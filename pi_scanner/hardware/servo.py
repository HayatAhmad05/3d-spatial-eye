"""
Servo motor control for Raspberry Pi using gpiozero/pigpio.
"""

import logging
import time
from typing import Optional

try:
    from gpiozero import Servo
    from gpiozero.pins.pigpio import PiGPIOFactory
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False

from ..config import (
    SERVO_PIN,
    SERVO_MIN_ANGLE,
    SERVO_MAX_ANGLE,
    SERVO_MIN_PULSE_WIDTH,
    SERVO_MAX_PULSE_WIDTH,
    SERVO_STEP_DELAY,
    SERVO_SETTLE_TIME
)

logger = logging.getLogger(__name__)


class ServoController:
    """
    Controller for servo motor with smooth movement and angle tracking.
    
    Uses gpiozero with pigpio backend for hardware PWM on Raspberry Pi.
    """
    
    def __init__(self, pin: int = SERVO_PIN, simulate: bool = False):
        """
        Initialize the servo controller.
        
        Args:
            pin: GPIO pin number (BCM)
            simulate: If True, run in simulation mode without real hardware
        """
        self.pin = pin
        self.simulate = simulate
        self._servo = None
        self._current_angle = 0
        self._initialized = False
        self._factory = None
        
    def initialize(self) -> bool:
        """
        Initialize the servo motor.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.simulate:
            logger.info("Servo controller running in simulation mode")
            self._initialized = True
            self._current_angle = SERVO_MIN_ANGLE
            return True
            
        if not HAS_GPIOZERO:
            logger.error("gpiozero library not installed. Install with: pip install gpiozero pigpio")
            return False
            
        try:
            # Try to use pigpio factory for hardware PWM (smoother)
            try:
                self._factory = PiGPIOFactory()
                logger.info("Using pigpio factory for hardware PWM")
            except Exception:
                self._factory = None
                logger.warning("pigpio not available, using software PWM")
            
            # Create servo with custom pulse widths
            self._servo = Servo(
                self.pin,
                min_pulse_width=SERVO_MIN_PULSE_WIDTH,
                max_pulse_width=SERVO_MAX_PULSE_WIDTH,
                pin_factory=self._factory
            )
            
            # Move to starting position
            self._set_angle(SERVO_MIN_ANGLE)
            self._current_angle = SERVO_MIN_ANGLE
            
            logger.info(f"Servo initialized on GPIO {self.pin}")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize servo: {e}")
            return False
    
    def _angle_to_value(self, angle: float) -> float:
        """
        Convert angle (0-180) to gpiozero servo value (-1 to 1).
        
        Args:
            angle: Angle in degrees (0-180)
            
        Returns:
            Servo value (-1 to 1)
        """
        # Clamp angle to valid range
        angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, angle))
        # Convert: 0 degrees = -1, 180 degrees = 1
        return (angle / 90.0) - 1.0
    
    def _set_angle(self, angle: float):
        """
        Set servo to specific angle (internal method).
        
        Args:
            angle: Target angle in degrees
        """
        if self._servo is not None:
            value = self._angle_to_value(angle)
            self._servo.value = value
    
    def move_to(self, angle: float, smooth: bool = True) -> float:
        """
        Move servo to specified angle.
        
        Args:
            angle: Target angle in degrees (0-180)
            smooth: If True, move gradually; if False, move immediately
            
        Returns:
            Actual angle moved to
        """
        if not self._initialized:
            logger.warning("Servo not initialized")
            return self._current_angle
            
        # Clamp angle to valid range
        target_angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, angle))
        
        if self.simulate:
            if smooth:
                # Simulate smooth movement delay
                steps = abs(target_angle - self._current_angle)
                time.sleep(steps * SERVO_STEP_DELAY * 0.1)  # Faster in simulation
            self._current_angle = target_angle
            return target_angle
        
        if smooth and abs(target_angle - self._current_angle) > 1:
            # Move gradually for smoother motion
            self._smooth_move(target_angle)
        else:
            # Direct movement
            self._set_angle(target_angle)
            
        self._current_angle = target_angle
        return target_angle
    
    def _smooth_move(self, target_angle: float):
        """
        Gradually move servo to target angle.
        
        Args:
            target_angle: Target angle in degrees
        """
        step = 1 if target_angle > self._current_angle else -1
        current = self._current_angle
        
        while (step > 0 and current < target_angle) or (step < 0 and current > target_angle):
            current += step
            self._set_angle(current)
            time.sleep(SERVO_STEP_DELAY)
        
        # Ensure we reach exact target
        self._set_angle(target_angle)
    
    def sweep(self, start: float, end: float, step: int = 1, callback=None):
        """
        Sweep servo from start to end angle, calling callback at each position.
        
        Args:
            start: Starting angle in degrees
            end: Ending angle in degrees
            step: Step size in degrees
            callback: Function to call at each position (receives angle as argument)
            
        Yields:
            Current angle at each step
        """
        if not self._initialized:
            logger.warning("Servo not initialized")
            return
            
        # Determine direction
        if start < end:
            angles = range(int(start), int(end) + 1, step)
        else:
            angles = range(int(start), int(end) - 1, -step)
        
        for angle in angles:
            self.move_to(angle, smooth=False)
            time.sleep(SERVO_SETTLE_TIME)  # Let servo settle
            
            if callback:
                callback(angle)
            
            yield angle
    
    def get_angle(self) -> float:
        """
        Get current servo angle.
        
        Returns:
            Current angle in degrees
        """
        return self._current_angle
    
    def detach(self):
        """
        Detach servo (stop PWM signal) to save power and reduce jitter.
        """
        if self._servo is not None:
            try:
                self._servo.detach()
                logger.debug("Servo detached")
            except Exception as e:
                logger.error(f"Error detaching servo: {e}")
    
    def close(self):
        """
        Close the servo and release resources.
        """
        if self._servo is not None:
            try:
                self._servo.close()
                logger.info("Servo closed")
            except Exception as e:
                logger.error(f"Error closing servo: {e}")
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if servo is initialized."""
        return self._initialized
    
    @property
    def current_angle(self) -> float:
        """Get current angle."""
        return self._current_angle
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
