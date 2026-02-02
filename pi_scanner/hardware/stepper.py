"""
28BYJ-48 Stepper motor driver with ULN2003 for Raspberry Pi.
Uses half-step sequence for smoother operation.
"""

import logging
import time
from typing import List

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

from ..config import (
    STEPPER_PINS,
    STEPPER_STEPS_PER_REVOLUTION,
    STEPPER_STEP_DELAY,
    STEPPER_DEGREES_PER_INCREMENT
)

logger = logging.getLogger(__name__)

# Half-step sequence for 28BYJ-48 stepper motor
# This provides smoother operation than full-step
HALF_STEP_SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]


class StepperMotor:
    """
    Controller for 28BYJ-48 stepper motor with ULN2003 driver board.
    
    Uses half-step sequence for 4096 steps per revolution (360 degrees).
    """
    
    def __init__(self, pins: dict = None, simulate: bool = False):
        """
        Initialize the stepper motor controller.
        
        Args:
            pins: Dictionary with IN1, IN2, IN3, IN4 pin numbers (BCM)
            simulate: If True, run in simulation mode without real hardware
        """
        self.pins = pins or STEPPER_PINS
        self.simulate = simulate
        self._pin_list: List[int] = [
            self.pins['IN1'],
            self.pins['IN2'],
            self.pins['IN3'],
            self.pins['IN4']
        ]
        self._current_step = 0
        self._current_angle = 0.0
        self._initialized = False
        self._steps_per_degree = STEPPER_STEPS_PER_REVOLUTION / 360.0
        
    def initialize(self) -> bool:
        """
        Initialize GPIO pins for stepper motor.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.simulate:
            logger.info("Stepper motor running in simulation mode")
            self._initialized = True
            return True
            
        if not HAS_GPIO:
            logger.error("RPi.GPIO library not installed. Install with: pip install RPi.GPIO")
            return False
            
        try:
            # Set up GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Configure pins as outputs
            for pin in self._pin_list:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            logger.info(f"Stepper motor initialized on pins {self._pin_list}")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize stepper motor: {e}")
            return False
    
    def _set_step(self, step_index: int):
        """
        Set GPIO outputs for a specific step in the sequence.
        
        Args:
            step_index: Index into half-step sequence (0-7)
        """
        if self.simulate:
            return
            
        sequence = HALF_STEP_SEQUENCE[step_index % 8]
        for i, pin in enumerate(self._pin_list):
            GPIO.output(pin, GPIO.HIGH if sequence[i] else GPIO.LOW)
    
    def _step_motor(self, steps: int, clockwise: bool = True):
        """
        Move stepper motor by specified number of steps.
        
        Args:
            steps: Number of steps to move
            clockwise: Direction of rotation
        """
        direction = 1 if clockwise else -1
        
        for _ in range(abs(steps)):
            self._current_step = (self._current_step + direction) % 8
            self._set_step(self._current_step)
            time.sleep(STEPPER_STEP_DELAY)
        
        # Turn off coils to save power and reduce heat
        self._release()
    
    def _release(self):
        """Turn off all coils to save power."""
        if self.simulate:
            return
            
        for pin in self._pin_list:
            GPIO.output(pin, GPIO.LOW)
    
    def move_degrees(self, degrees: float, clockwise: bool = True) -> float:
        """
        Move stepper motor by specified degrees.
        
        Args:
            degrees: Degrees to rotate
            clockwise: Direction of rotation
            
        Returns:
            New absolute angle position
        """
        if not self._initialized:
            logger.warning("Stepper motor not initialized")
            return self._current_angle
            
        steps = int(abs(degrees) * self._steps_per_degree)
        
        if self.simulate:
            # Simulate movement delay
            time.sleep(steps * STEPPER_STEP_DELAY * 0.1)
        else:
            self._step_motor(steps, clockwise)
        
        # Update angle tracking
        if clockwise:
            self._current_angle += degrees
        else:
            self._current_angle -= degrees
            
        # Normalize to 0-360
        self._current_angle = self._current_angle % 360
        
        return self._current_angle
    
    def move_to_angle(self, target_angle: float) -> float:
        """
        Move to an absolute angle position (0-360).
        
        Args:
            target_angle: Target angle in degrees (0-360)
            
        Returns:
            Actual angle position
        """
        if not self._initialized:
            logger.warning("Stepper motor not initialized")
            return self._current_angle
            
        # Normalize target angle
        target_angle = target_angle % 360
        
        # Calculate shortest path
        diff = target_angle - self._current_angle
        
        # Determine direction for shortest path
        if abs(diff) <= 180:
            clockwise = diff > 0
            degrees_to_move = abs(diff)
        else:
            clockwise = diff < 0
            degrees_to_move = 360 - abs(diff)
        
        return self.move_degrees(degrees_to_move, clockwise)
    
    def increment(self, degrees: float = STEPPER_DEGREES_PER_INCREMENT) -> float:
        """
        Increment stepper position by configured amount.
        
        Args:
            degrees: Degrees to increment (default from config)
            
        Returns:
            New absolute angle position
        """
        return self.move_degrees(degrees, clockwise=True)
    
    def reset_position(self):
        """
        Reset the angle tracking to zero (does not physically move motor).
        
        Call this when motor is at known zero position.
        """
        self._current_angle = 0.0
        logger.info("Stepper position reset to 0 degrees")
    
    def get_angle(self) -> float:
        """
        Get current stepper angle.
        
        Returns:
            Current angle in degrees (0-360)
        """
        return self._current_angle
    
    def close(self):
        """
        Close the stepper motor and release GPIO resources.
        """
        if self._initialized and not self.simulate:
            try:
                self._release()
                # Note: We don't call GPIO.cleanup() here to avoid
                # affecting other GPIO users. Let main program handle cleanup.
                logger.info("Stepper motor released")
            except Exception as e:
                logger.error(f"Error closing stepper motor: {e}")
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if stepper motor is initialized."""
        return self._initialized
    
    @property
    def current_angle(self) -> float:
        """Get current angle."""
        return self._current_angle
    
    @property
    def steps_per_degree(self) -> float:
        """Get steps per degree."""
        return self._steps_per_degree
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
