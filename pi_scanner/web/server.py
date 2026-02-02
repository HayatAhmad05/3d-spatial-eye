"""
Flask web server with WebSocket support for real-time point cloud visualization.
"""

import logging
import os
from typing import Optional
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit

from ..scanner.coordinator import ScanCoordinator, ScanState
from ..scanner.point_cloud import Point3D
from ..export import PLYWriter, PCDWriter
from ..config import WEB_HOST, WEB_PORT, WEB_DEBUG, EXPORT_DIRECTORY

logger = logging.getLogger(__name__)

# Global scanner instance (set by create_app)
scanner: Optional[ScanCoordinator] = None
socketio: Optional[SocketIO] = None


def create_app(scanner_instance: ScanCoordinator) -> tuple:
    """
    Create and configure the Flask application.
    
    Args:
        scanner_instance: The ScanCoordinator instance to use
        
    Returns:
        Tuple of (Flask app, SocketIO instance)
    """
    global scanner, socketio
    scanner = scanner_instance
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    app.config['SECRET_KEY'] = 'pi-scanner-secret-key'
    
    # Create SocketIO instance
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register routes
    register_routes(app)
    
    # Register WebSocket handlers
    register_socketio_handlers(socketio)
    
    # Register scanner callbacks for real-time updates
    register_scanner_callbacks()
    
    return app, socketio


def register_routes(app: Flask):
    """Register HTTP routes."""
    
    @app.route('/')
    def index():
        """Serve the main viewer page."""
        return render_template('index.html')
    
    @app.route('/api/status')
    def get_status():
        """Get current scanner status."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        progress = scanner.get_progress()
        return jsonify(progress.to_dict())
    
    @app.route('/api/points')
    def get_points():
        """Get all points in the current scan."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        points = scanner.point_cloud.get_points_as_list()
        return jsonify({
            'count': len(points),
            'points': points
        })
    
    @app.route('/api/points/latest/<int:count>')
    def get_latest_points(count: int):
        """Get the latest N points."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        points = scanner.point_cloud.get_latest_points(count)
        return jsonify({
            'count': len(points),
            'points': [[p.x, p.y, p.z] for p in points]
        })
    
    @app.route('/api/scan/start', methods=['POST'])
    def start_scan():
        """Start a new scan."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        success = scanner.start_scan()
        return jsonify({'success': success, 'state': scanner.get_state().value})
    
    @app.route('/api/scan/stop', methods=['POST'])
    def stop_scan():
        """Stop the current scan."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        scanner.stop_scan()
        return jsonify({'success': True, 'state': scanner.get_state().value})
    
    @app.route('/api/scan/pause', methods=['POST'])
    def pause_scan():
        """Pause the current scan."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        scanner.pause_scan()
        return jsonify({'success': True, 'state': scanner.get_state().value})
    
    @app.route('/api/scan/resume', methods=['POST'])
    def resume_scan():
        """Resume a paused scan."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        scanner.resume_scan()
        return jsonify({'success': True, 'state': scanner.get_state().value})
    
    @app.route('/api/scan/reset', methods=['POST'])
    def reset_scan():
        """Reset the scanner."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        scanner.reset()
        return jsonify({'success': True, 'state': scanner.get_state().value})
    
    @app.route('/api/export/ply', methods=['GET'])
    def export_ply():
        """Export point cloud to PLY format."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        # Create export directory if needed
        os.makedirs(EXPORT_DIRECTORY, exist_ok=True)
        
        # Generate filename
        from datetime import datetime
        from ..config import EXPORT_TIMESTAMP_FORMAT
        timestamp = datetime.now().strftime(EXPORT_TIMESTAMP_FORMAT)
        filename = f"scan_{timestamp}.ply"
        filepath = os.path.join(EXPORT_DIRECTORY, filename)
        
        # Export
        writer = PLYWriter()
        writer.write(scanner.point_cloud, filepath)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    @app.route('/api/export/pcd', methods=['GET'])
    def export_pcd():
        """Export point cloud to PCD format."""
        if scanner is None:
            return jsonify({'error': 'Scanner not initialized'}), 500
        
        # Create export directory if needed
        os.makedirs(EXPORT_DIRECTORY, exist_ok=True)
        
        # Generate filename
        from datetime import datetime
        from ..config import EXPORT_TIMESTAMP_FORMAT
        timestamp = datetime.now().strftime(EXPORT_TIMESTAMP_FORMAT)
        filename = f"scan_{timestamp}.pcd"
        filepath = os.path.join(EXPORT_DIRECTORY, filename)
        
        # Export
        writer = PCDWriter()
        writer.write(scanner.point_cloud, filepath)
        
        return send_file(filepath, as_attachment=True, download_name=filename)


def register_socketio_handlers(sio: SocketIO):
    """Register WebSocket event handlers."""
    
    @sio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info("Client connected")
        
        # Send current state
        if scanner is not None:
            progress = scanner.get_progress()
            emit('status', progress.to_dict())
            
            # Send existing points if any
            points = scanner.point_cloud.get_points_as_list()
            if points:
                emit('points_batch', {'points': points})
    
    @sio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info("Client disconnected")
    
    @sio.on('request_points')
    def handle_request_points():
        """Handle request for all points."""
        if scanner is not None:
            points = scanner.point_cloud.get_points_as_list()
            emit('points_batch', {'points': points})
    
    @sio.on('request_status')
    def handle_request_status():
        """Handle request for current status."""
        if scanner is not None:
            progress = scanner.get_progress()
            emit('status', progress.to_dict())


def register_scanner_callbacks():
    """Register callbacks for scanner events to broadcast via WebSocket."""
    if scanner is None or socketio is None:
        return
    
    def on_points(points: list):
        """Broadcast new points to all clients."""
        point_list = [[p.x, p.y, p.z] for p in points]
        socketio.emit('points', {'points': point_list})
    
    def on_progress(progress):
        """Broadcast progress updates."""
        socketio.emit('progress', progress.to_dict())
    
    def on_state_change(state: ScanState):
        """Broadcast state changes."""
        socketio.emit('state', {'state': state.value})
    
    scanner.on_points(on_points)
    scanner.on_progress(on_progress)
    scanner.on_state_change(on_state_change)


def run_server(app: Flask, sio: SocketIO, host: str = WEB_HOST, port: int = WEB_PORT):
    """
    Run the web server.
    
    Args:
        app: Flask application
        sio: SocketIO instance
        host: Host to bind to
        port: Port to listen on
    """
    logger.info(f"Starting web server on http://{host}:{port}")
    sio.run(app, host=host, port=port, debug=WEB_DEBUG, use_reloader=False)
