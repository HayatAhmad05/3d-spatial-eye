# pi_scanner Package

This is the main Python package for the 3D Spatial Eye scanner.

## Module Structure

```
pi_scanner/
├── __init__.py         # Package initialization
├── config.py           # Configuration constants
├── main.py             # Entry point
├── hardware/           # Hardware interface modules
│   ├── tof_sensor.py   # VL53L1X TOF sensor
│   ├── servo.py        # Servo motor control
│   └── stepper.py      # Stepper motor driver
├── scanner/            # Scanning logic
│   ├── coordinator.py  # Scan orchestration
│   └── point_cloud.py  # Point cloud data
├── web/                # Web interface
│   ├── server.py       # Flask server
│   ├── templates/      # HTML templates
│   └── static/         # JS/CSS assets
└── export/             # File export
    ├── ply_writer.py   # PLY format
    └── pcd_writer.py   # PCD format
```

## Running

```bash
# From repository root
python -m pi_scanner.main --simulate
```

## Configuration

All configurable parameters are in `config.py`:
- GPIO pin assignments
- Scan parameters (angles, timing)
- Web server settings
- Export settings
