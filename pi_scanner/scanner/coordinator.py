"""
Scan coordinator that orchestrates hardware components and collects point cloud data.
"""

import logging
import threading
import time
from enum import Enum
from typing import Optional, Callable, List
from dataclasses import dataclass

from ..hardware import TOFSensor, ServoController, StepperMotor
from .point_cloud import PointCloud, Point3D
from ..config import (
    SCAN_SERVO_START,
    SCAN_SERVO_END,
    SCAN_STEPPER_TOTAL,
    SCAN_DELAY_AT_ENDS,
    SERVO_SETTLE_TIME,
    STEPPER_DEGREES_PER_INCREMENT,
    WEBSOCKET_BATCH_SIZE,
    WEBSOCKET_BATCH_INTERVAL
)

logger = logging.getLogger(__name__)


class ScanState(Enum):
    """Scanner state enumeration."""
    IDLE = "idle"
    SCANNING = "scanning"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ScanProgress:
    """Current scan progress information."""
    state: ScanState
    servo_angle: float
    stepper_angle: float
    points_collected: int
    current_cycle: int
    total_cycles: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'state': self.state.value,
            'servo_angle': self.servo_angle,
            'stepper_angle': self.stepper_angle,
            'points_collected': self.points_collected,
            'current_cycle': self.current_cycle,
            'total_cycles': self.total_cycles,
            'progress_percent': (self.current_cycle / self.total_cycles * 100) if self.total_cycles > 0 else 0
        }


class ScanCoordinator:
    """
    Coordinates the scanning process across all hardware components.
    
    Scan pattern:
    1. Servo sweeps from 0° to 180° (taking TOF readings at each degree)
    2. Servo sweeps back from 180° to 0°
    3. Stepper rotates 1° (or configured increment)
    4. Repeat until stepper completes 360°
    """
    
    def __init__(self, simulate: bool = False):
        """
        Initialize the scan coordinator.
        
        Args:
            simulate: If True, run in simulation mode without real hardware
        """
        self.simulate = simulate
        
        # Hardware components
        self.tof = TOFSensor(simulate=simulate)
        self.servo = ServoController(simulate=simulate)
        self.stepper = StepperMotor(simulate=simulate)
        
        # Point cloud buffer
        self.point_cloud = PointCloud()
        
        # State
        self._state = ScanState.IDLE
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_requested = threading.Event()
        self._pause_requested = threading.Event()
        
        # Progress tracking
        self._current_servo_angle = 0.0
        self._current_stepper_angle = 0.0
        self._current_cycle = 0
        self._total_cycles = int(SCAN_STEPPER_TOTAL / STEPPER_DEGREES_PER_INCREMENT)
        
        # Callbacks for real-time updates
        self._on_progress: List[Callable[[ScanProgress], None]] = []
        self._on_points: List[Callable[[List[Point3D]], None]] = []
        self._on_state_change: List[Callable[[ScanState], None]] = []
        
        # Point batching for efficient WebSocket transmission
        self._point_batch: List[Point3D] = []
        self._last_batch_time = time.time()
    
    def initialize(self) -> bool:
        """
        Initialize all hardware components.
        
        Returns:
            True if all components initialized successfully
        """
        logger.info("Initializing scanner hardware...")
        
        # Initialize each component
        if not self.tof.initialize():
            logger.error("Failed to initialize TOF sensor")
            self._set_state(ScanState.ERROR)
            return False
            
        if not self.servo.initialize():
            logger.error("Failed to initialize servo")
            self._set_state(ScanState.ERROR)
            return False
            
        if not self.stepper.initialize():
            logger.error("Failed to initialize stepper motor")
            self._set_state(ScanState.ERROR)
            return False
        
        logger.info("All hardware initialized successfully")
        self._set_state(ScanState.IDLE)
        return True
    
    def start_scan(self) -> bool:
        """
        Start the scanning process in a background thread.
        
        Returns:
            True if scan started successfully
        """
        if self._state == ScanState.SCANNING:
            logger.warning("Scan already in progress")
            return False
            
        if self._state == ScanState.ERROR:
            logger.error("Scanner in error state, cannot start")
            return False
        
        # Reset stop flag
        self._stop_requested.clear()
        self._pause_requested.clear()
        
        # Start scan thread
        self._scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._scan_thread.start()
        
        logger.info("Scan started")
        return True
    
    def stop_scan(self):
        """Request the scan to stop."""
        if self._state in (ScanState.SCANNING, ScanState.PAUSED):
            logger.info("Stop requested")
            self._set_state(ScanState.STOPPING)
            self._stop_requested.set()
            self._pause_requested.set()  # Release from pause if paused
    
    def pause_scan(self):
        """Pause the current scan."""
        if self._state == ScanState.SCANNING:
            logger.info("Pause requested")
            self._pause_requested.set()
            self._set_state(ScanState.PAUSED)
    
    def resume_scan(self):
        """Resume a paused scan."""
        if self._state == ScanState.PAUSED:
            logger.info("Resume requested")
            self._pause_requested.clear()
            self._set_state(ScanState.SCANNING)
    
    def reset(self):
        """Reset the scanner to initial state."""
        self.stop_scan()
        
        # Wait for thread to finish
        if self._scan_thread is not None:
            self._scan_thread.join(timeout=5.0)
        
        # Clear point cloud
        self.point_cloud.clear()
        
        # Reset positions
        self._current_servo_angle = 0.0
        self._current_stepper_angle = 0.0
        self._current_cycle = 0
        
        # Move servo to start position
        if self.servo.is_initialized:
            self.servo.move_to(SCAN_SERVO_START)
        
        # Reset stepper position tracking
        if self.stepper.is_initialized:
            self.stepper.reset_position()
        
        self._set_state(ScanState.IDLE)
        logger.info("Scanner reset")
    
    def _scan_loop(self):
        """Main scan loop running in background thread."""
        self._set_state(ScanState.SCANNING)
        self._current_cycle = 0
        self._current_stepper_angle = 0.0
        
        try:
            while not self._stop_requested.is_set():
                # Check for pause
                while self._pause_requested.is_set() and not self._stop_requested.is_set():
                    time.sleep(0.1)
                
                if self._stop_requested.is_set():
                    break
                
                # Perform one complete servo sweep cycle
                self._perform_servo_sweep()
                
                # Check stop flag again
                if self._stop_requested.is_set():
                    break
                
                # Increment stepper
                self._current_stepper_angle = self.stepper.increment()
                self._current_cycle += 1
                
                # Notify progress
                self._notify_progress()
                
                # Check if full rotation complete
                if self._current_stepper_angle >= SCAN_STEPPER_TOTAL or \
                   self._current_cycle >= self._total_cycles:
                    logger.info("Full 360° scan complete!")
                    break
            
        except Exception as e:
            logger.error(f"Error in scan loop: {e}")
            self._set_state(ScanState.ERROR)
        finally:
            # Flush any remaining points
            self._flush_point_batch()
            
            if self._state != ScanState.ERROR:
                self._set_state(ScanState.IDLE)
            
            logger.info(f"Scan finished. Total points: {self.point_cloud.get_point_count()}")
    
    def _perform_servo_sweep(self):
        """Perform one complete servo sweep (0→180→0) with TOF readings."""
        # Forward sweep: 0 → 180
        for angle in range(SCAN_SERVO_START, SCAN_SERVO_END + 1):
            if self._stop_requested.is_set():
                return
            
            # Check pause
            while self._pause_requested.is_set() and not self._stop_requested.is_set():
                time.sleep(0.1)
            
            self._scan_at_angle(angle)
        
        # Pause at end
        time.sleep(SCAN_DELAY_AT_ENDS)
        
        # Reverse sweep: 180 → 0
        for angle in range(SCAN_SERVO_END, SCAN_SERVO_START - 1, -1):
            if self._stop_requested.is_set():
                return
            
            # Check pause
            while self._pause_requested.is_set() and not self._stop_requested.is_set():
                time.sleep(0.1)
            
            self._scan_at_angle(angle)
        
        # Pause at start
        time.sleep(SCAN_DELAY_AT_ENDS)
    
    def _scan_at_angle(self, servo_angle: int):
        """
        Take a TOF reading at the specified servo angle.
        
        Args:
            servo_angle: Servo angle in degrees
        """
        # Move servo
        self.servo.move_to(servo_angle, smooth=False)
        self._current_servo_angle = servo_angle
        
        # Wait for servo to settle
        time.sleep(SERVO_SETTLE_TIME)
        
        # Read TOF sensor
        distance = self.tof.read_distance()
        
        if distance is not None and distance > 0:
            # Add point to cloud
            point = self.point_cloud.add_point_spherical(
                theta=servo_angle,
                phi=self._current_stepper_angle,
                distance=distance
            )
            
            if point:
                self._add_to_batch(point)
        
        # Notify progress periodically
        if servo_angle % 10 == 0:
            self._notify_progress()
    
    def _add_to_batch(self, point: Point3D):
        """Add point to batch and send if batch is ready."""
        self._point_batch.append(point)
        
        current_time = time.time()
        batch_ready = (
            len(self._point_batch) >= WEBSOCKET_BATCH_SIZE or
            current_time - self._last_batch_time >= WEBSOCKET_BATCH_INTERVAL
        )
        
        if batch_ready and self._point_batch:
            self._flush_point_batch()
    
    def _flush_point_batch(self):
        """Send the current batch of points to listeners."""
        if not self._point_batch:
            return
            
        batch = self._point_batch.copy()
        self._point_batch.clear()
        self._last_batch_time = time.time()
        
        for callback in self._on_points:
            try:
                callback(batch)
            except Exception as e:
                logger.error(f"Error in points callback: {e}")
    
    def _set_state(self, state: ScanState):
        """Set scanner state and notify listeners."""
        old_state = self._state
        self._state = state
        
        if old_state != state:
            logger.info(f"Scanner state: {old_state.value} → {state.value}")
            for callback in self._on_state_change:
                try:
                    callback(state)
                except Exception as e:
                    logger.error(f"Error in state callback: {e}")
    
    def _notify_progress(self):
        """Notify listeners of current progress."""
        progress = self.get_progress()
        for callback in self._on_progress:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def get_progress(self) -> ScanProgress:
        """Get current scan progress."""
        return ScanProgress(
            state=self._state,
            servo_angle=self._current_servo_angle,
            stepper_angle=self._current_stepper_angle,
            points_collected=self.point_cloud.get_point_count(),
            current_cycle=self._current_cycle,
            total_cycles=self._total_cycles
        )
    
    def get_state(self) -> ScanState:
        """Get current scanner state."""
        return self._state
    
    def on_progress(self, callback: Callable[[ScanProgress], None]):
        """Register callback for progress updates."""
        self._on_progress.append(callback)
    
    def on_points(self, callback: Callable[[List[Point3D]], None]):
        """Register callback for new points."""
        self._on_points.append(callback)
    
    def on_state_change(self, callback: Callable[[ScanState], None]):
        """Register callback for state changes."""
        self._on_state_change.append(callback)
    
    def close(self):
        """Close all hardware resources."""
        self.stop_scan()
        
        # Wait for thread
        if self._scan_thread is not None:
            self._scan_thread.join(timeout=5.0)
        
        # Close hardware
        self.tof.close()
        self.servo.close()
        self.stepper.close()
        
        logger.info("Scanner coordinator closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
