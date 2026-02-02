"""
Configuration for the Raspberry Pi 5 3D Scanner.
GPIO pin mappings and scan parameters.
"""

# =============================================================================
# GPIO Pin Configuration (BCM numbering)
# =============================================================================

# Servo motor (PWM)
SERVO_PIN = 17  # Hardware PWM preferred for smooth control

# Stepper motor (28BYJ-48 with ULN2003 driver)
STEPPER_PINS = {
    'IN1': 5,
    'IN2': 6,
    'IN3': 13,
    'IN4': 19
}

# I2C for TOF sensor (VL53L1X)
# Uses default I2C bus (GPIO 2 = SDA, GPIO 3 = SCL)
I2C_BUS = 1  # /dev/i2c-1 on Raspberry Pi

# =============================================================================
# Servo Parameters
# =============================================================================

SERVO_MIN_ANGLE = 0      # Minimum angle in degrees
SERVO_MAX_ANGLE = 180    # Maximum angle in degrees
SERVO_STEP_DELAY = 0.05  # Delay between servo steps (seconds)
SERVO_SETTLE_TIME = 0.03 # Time to let servo settle before TOF reading

# Servo PWM parameters (for gpiozero)
SERVO_MIN_PULSE_WIDTH = 0.0005  # 0.5ms
SERVO_MAX_PULSE_WIDTH = 0.0025  # 2.5ms

# =============================================================================
# Stepper Motor Parameters (28BYJ-48)
# =============================================================================

STEPPER_STEPS_PER_REVOLUTION = 4096  # Full steps for 360 degrees
STEPPER_STEP_DELAY = 0.002           # Delay between steps (seconds)
STEPPER_DEGREES_PER_INCREMENT = 1    # Degrees to move per scan cycle

# =============================================================================
# TOF Sensor Parameters (VL53L1X)
# =============================================================================

TOF_I2C_ADDRESS = 0x29      # Default I2C address
TOF_TIMING_BUDGET = 50000   # Timing budget in microseconds (50ms)
TOF_MAX_RANGE = 4000        # Maximum valid range in mm
TOF_MIN_RANGE = 10          # Minimum valid range in mm

# =============================================================================
# Scan Parameters
# =============================================================================

# Scan pattern
SCAN_SERVO_START = 0    # Starting servo angle
SCAN_SERVO_END = 180    # Ending servo angle
SCAN_STEPPER_TOTAL = 360  # Total stepper rotation

# Timing
SCAN_DELAY_AT_ENDS = 0.5  # Pause at 0 and 180 degrees (seconds)

# =============================================================================
# Web Server Configuration
# =============================================================================

WEB_HOST = '0.0.0.0'  # Listen on all interfaces
WEB_PORT = 5000       # Default port
WEB_DEBUG = False     # Debug mode (disable in production)

# WebSocket settings
WEBSOCKET_BATCH_SIZE = 10  # Send points in batches for efficiency
WEBSOCKET_BATCH_INTERVAL = 0.1  # Max time between batches (seconds)

# =============================================================================
# Export Configuration
# =============================================================================

EXPORT_DIRECTORY = 'scans'  # Directory for exported files
EXPORT_TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'  # Timestamp format for filenames
