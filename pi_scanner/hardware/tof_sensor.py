"""
VL53L1X Time-of-Flight sensor interface for Raspberry Pi.
"""

import logging
from typing import Optional

try:
    import vl53l1x
    HAS_VL53L1X = True
except ImportError:
    HAS_VL53L1X = False

from ..config import (
    I2C_BUS,
    TOF_I2C_ADDRESS,
    TOF_TIMING_BUDGET,
    TOF_MAX_RANGE,
    TOF_MIN_RANGE
)

logger = logging.getLogger(__name__)


class TOFSensor:
    """
    Interface for the VL53L1X Time-of-Flight distance sensor.
    
    Provides distance measurements in millimeters using I2C communication.
    """
    
    def __init__(self, i2c_bus: int = I2C_BUS, simulate: bool = False):
        """
        Initialize the TOF sensor.
        
        Args:
            i2c_bus: I2C bus number (default: 1 for /dev/i2c-1)
            simulate: If True, run in simulation mode without real hardware
        """
        self.i2c_bus = i2c_bus
        self.simulate = simulate
        self._sensor = None
        self._initialized = False
        self._simulation_distance = 500  # Default simulation distance
        
    def initialize(self) -> bool:
        """
        Initialize and configure the TOF sensor.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.simulate:
            logger.info("TOF sensor running in simulation mode")
            self._initialized = True
            return True
            
        if not HAS_VL53L1X:
            logger.error("vl53l1x library not installed. Install with: pip install vl53l1x")
            return False
            
        try:
            self._sensor = vl53l1x.VL53L1X(i2c_bus=self.i2c_bus, i2c_address=TOF_I2C_ADDRESS)
            self._sensor.open()
            
            # Configure timing budget for accuracy vs speed tradeoff
            # 1 = Short range (fast), 2 = Medium, 3 = Long range (slow but accurate)
            self._sensor.start_ranging(2)  # Medium range mode
            
            logger.info(f"VL53L1X TOF sensor initialized on I2C bus {self.i2c_bus}")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TOF sensor: {e}")
            return False
    
    def read_distance(self) -> Optional[int]:
        """
        Read current distance from the sensor.
        
        Returns:
            Distance in millimeters, or None if reading failed
        """
        if not self._initialized:
            logger.warning("TOF sensor not initialized")
            return None
            
        if self.simulate:
            return self._get_simulation_distance()
            
        try:
            distance = self._sensor.get_distance()
            
            # Validate reading
            if distance < TOF_MIN_RANGE or distance > TOF_MAX_RANGE:
                logger.debug(f"TOF reading out of range: {distance}mm")
                return None
                
            return distance
            
        except Exception as e:
            logger.error(f"Failed to read TOF sensor: {e}")
            return None
    
    def _get_simulation_distance(self) -> int:
        """
        Generate simulated distance reading for testing.
        
        Returns:
            Simulated distance in millimeters
        """
        import random
        # Add some noise to simulation
        noise = random.randint(-20, 20)
        return max(TOF_MIN_RANGE, min(TOF_MAX_RANGE, self._simulation_distance + noise))
    
    def set_simulation_distance(self, distance: int):
        """
        Set the base distance for simulation mode.
        
        Args:
            distance: Base distance in millimeters
        """
        self._simulation_distance = distance
    
    def close(self):
        """
        Close the sensor and release resources.
        """
        if self._sensor is not None:
            try:
                self._sensor.stop_ranging()
                self._sensor.close()
                logger.info("TOF sensor closed")
            except Exception as e:
                logger.error(f"Error closing TOF sensor: {e}")
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if sensor is initialized."""
        return self._initialized
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
