#!/usr/bin/env python3
"""
3D Spatial Eye - Main Entry Point

A 3D point cloud scanner for Raspberry Pi 5 using:
- VL53L1X TOF sensor for distance measurement
- Servo motor for vertical sweep (0-180 degrees)
- Stepper motor for horizontal rotation (360 degrees)
- Real-time web-based 3D visualization
- Export to PLY and PCD formats

Usage:
    python -m pi_scanner.main [options]

Options:
    --simulate      Run in simulation mode (no hardware required)
    --host HOST     Web server host (default: 0.0.0.0)
    --port PORT     Web server port (default: 5000)
    --debug         Enable debug mode
"""

import argparse
import logging
import signal
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pi_scanner.scanner.coordinator import ScanCoordinator
from pi_scanner.web.server import create_app, run_server
from pi_scanner.config import WEB_HOST, WEB_PORT, WEB_DEBUG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='3D Spatial Eye - Point Cloud Scanner for Raspberry Pi 5',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with real hardware
    python -m pi_scanner.main

    # Run in simulation mode (for testing without hardware)
    python -m pi_scanner.main --simulate

    # Run on custom port
    python -m pi_scanner.main --port 8080

    # Run with debug logging
    python -m pi_scanner.main --debug
        """
    )
    
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Run in simulation mode without real hardware'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=WEB_HOST,
        help=f'Web server host address (default: {WEB_HOST})'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=WEB_PORT,
        help=f'Web server port (default: {WEB_PORT})'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose logging'
    )
    
    return parser.parse_args()


def setup_signal_handlers(scanner: ScanCoordinator):
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        scanner.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def print_banner():
    """Print application banner."""
    banner = """
    ============================================================
    |                                                          |
    |           3D SPATIAL EYE - Point Cloud Scanner           |
    |                                                          |
    |    Raspberry Pi 5 | VL53L1X TOF | Real-time 3D View      |
    |                                                          |
    ============================================================
    """
    print(banner)


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Configure debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Print banner
    print_banner()
    
    # Log startup info
    mode = "SIMULATION" if args.simulate else "HARDWARE"
    logger.info(f"Starting 3D Spatial Eye in {mode} mode")
    logger.info(f"Web interface will be available at http://{args.host}:{args.port}")
    
    if args.simulate:
        logger.warning("Running in simulation mode - no real hardware will be used")
        logger.info("Simulated distance readings will be generated")
    
    # Create scanner
    scanner = ScanCoordinator(simulate=args.simulate)
    
    # Set up signal handlers
    setup_signal_handlers(scanner)
    
    try:
        # Initialize hardware
        logger.info("Initializing hardware...")
        if not scanner.initialize():
            logger.error("Failed to initialize scanner hardware")
            if not args.simulate:
                logger.info("Tip: Try running with --simulate flag for testing")
            return 1
        
        logger.info("Hardware initialized successfully")
        
        # Create web application
        logger.info("Creating web application...")
        app, socketio = create_app(scanner)
        
        # Print access instructions
        print("\n" + "=" * 60)
        print("Scanner Ready!")
        print("=" * 60)
        print(f"\nOpen your web browser and navigate to:")
        print(f"  http://localhost:{args.port}")
        print(f"\nOr from another device on the network:")
        print(f"  http://<raspberry-pi-ip>:{args.port}")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60 + "\n")
        
        # Run web server (blocking)
        run_server(app, socketio, host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        # Clean up
        logger.info("Shutting down...")
        scanner.close()
        logger.info("Goodbye!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
