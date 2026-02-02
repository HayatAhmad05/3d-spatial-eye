/**
 * 3D Spatial Eye - Three.js Point Cloud Viewer
 * Real-time 3D visualization with WebSocket updates
 */

class PointCloudViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.pointCloud = null;
        this.points = [];
        this.pointSize = 3;
        this.axesHelper = null;
        this.gridHelper = null;
        
        this.init();
        this.animate();
    }
    
    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a0a);
        
        // Camera
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, aspect, 1, 100000);
        this.camera.position.set(2000, 2000, 2000);
        this.camera.lookAt(0, 0, 0);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
        
        // Orbit Controls (simple implementation)
        this.setupControls();
        
        // Axes Helper
        this.axesHelper = new THREE.AxesHelper(1000);
        this.scene.add(this.axesHelper);
        
        // Grid Helper
        this.gridHelper = new THREE.GridHelper(4000, 40, 0x444444, 0x222222);
        this.scene.add(this.gridHelper);
        
        // Point Cloud
        this.initPointCloud();
        
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        
        // Handle resize
        window.addEventListener('resize', () => this.onWindowResize());
    }
    
    setupControls() {
        // Simple orbit controls implementation
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        let spherical = { radius: 3500, theta: Math.PI / 4, phi: Math.PI / 4 };
        
        const updateCamera = () => {
            this.camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
            this.camera.position.y = spherical.radius * Math.cos(spherical.phi);
            this.camera.position.z = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
            this.camera.lookAt(0, 0, 0);
        };
        
        this.container.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        this.container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;
            
            spherical.theta -= deltaX * 0.01;
            spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + deltaY * 0.01));
            
            updateCamera();
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        this.container.addEventListener('mouseup', () => {
            isDragging = false;
        });
        
        this.container.addEventListener('mouseleave', () => {
            isDragging = false;
        });
        
        this.container.addEventListener('wheel', (e) => {
            e.preventDefault();
            spherical.radius = Math.max(500, Math.min(20000, spherical.radius + e.deltaY * 2));
            updateCamera();
        });
        
        // Touch support
        let touchStart = null;
        let initialRadius = spherical.radius;
        
        this.container.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            } else if (e.touches.length === 2) {
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                initialRadius = spherical.radius;
                touchStart = { distance: Math.sqrt(dx * dx + dy * dy) };
            }
        });
        
        this.container.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (e.touches.length === 1 && touchStart && !touchStart.distance) {
                const deltaX = e.touches[0].clientX - touchStart.x;
                const deltaY = e.touches[0].clientY - touchStart.y;
                
                spherical.theta -= deltaX * 0.01;
                spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + deltaY * 0.01));
                
                updateCamera();
                touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            } else if (e.touches.length === 2 && touchStart && touchStart.distance) {
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                const distance = Math.sqrt(dx * dx + dy * dy);
                const scale = touchStart.distance / distance;
                spherical.radius = Math.max(500, Math.min(20000, initialRadius * scale));
                updateCamera();
            }
        });
        
        this.container.addEventListener('touchend', () => {
            touchStart = null;
        });
        
        // Store controls reference for reset
        this.spherical = spherical;
        this.updateCamera = updateCamera;
        
        updateCamera();
    }
    
    initPointCloud() {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(300000 * 3); // Pre-allocate for 100k points
        const colors = new Float32Array(300000 * 3);
        
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setDrawRange(0, 0);
        
        const material = new THREE.PointsMaterial({
            size: this.pointSize,
            vertexColors: true,
            sizeAttenuation: true
        });
        
        this.pointCloud = new THREE.Points(geometry, material);
        this.scene.add(this.pointCloud);
    }
    
    addPoints(newPoints) {
        if (!newPoints || newPoints.length === 0) return;
        
        const geometry = this.pointCloud.geometry;
        const positions = geometry.attributes.position.array;
        const colors = geometry.attributes.color.array;
        
        const startIdx = this.points.length;
        
        for (let i = 0; i < newPoints.length; i++) {
            const point = newPoints[i];
            const idx = (startIdx + i) * 3;
            
            if (idx + 2 >= positions.length) {
                console.warn('Point cloud buffer full');
                break;
            }
            
            // Position
            positions[idx] = point[0];
            positions[idx + 1] = point[2]; // Swap Y and Z for Three.js coordinate system
            positions[idx + 2] = point[1];
            
            // Color based on height (Z value)
            const height = point[2];
            const normalizedHeight = (height + 2000) / 4000; // Normalize to 0-1
            const color = this.heightToColor(normalizedHeight);
            colors[idx] = color.r;
            colors[idx + 1] = color.g;
            colors[idx + 2] = color.b;
            
            this.points.push(point);
        }
        
        geometry.attributes.position.needsUpdate = true;
        geometry.attributes.color.needsUpdate = true;
        geometry.setDrawRange(0, this.points.length);
    }
    
    heightToColor(t) {
        // Color gradient from blue (low) to cyan to green to yellow to red (high)
        t = Math.max(0, Math.min(1, t));
        
        let r, g, b;
        if (t < 0.25) {
            // Blue to Cyan
            r = 0;
            g = t * 4;
            b = 1;
        } else if (t < 0.5) {
            // Cyan to Green
            r = 0;
            g = 1;
            b = 1 - (t - 0.25) * 4;
        } else if (t < 0.75) {
            // Green to Yellow
            r = (t - 0.5) * 4;
            g = 1;
            b = 0;
        } else {
            // Yellow to Red
            r = 1;
            g = 1 - (t - 0.75) * 4;
            b = 0;
        }
        
        return { r, g, b };
    }
    
    clearPoints() {
        this.points = [];
        const geometry = this.pointCloud.geometry;
        geometry.setDrawRange(0, 0);
    }
    
    setPointSize(size) {
        this.pointSize = size;
        this.pointCloud.material.size = size;
    }
    
    setAxesVisible(visible) {
        this.axesHelper.visible = visible;
    }
    
    setGridVisible(visible) {
        this.gridHelper.visible = visible;
    }
    
    resetView() {
        this.spherical.radius = 3500;
        this.spherical.theta = Math.PI / 4;
        this.spherical.phi = Math.PI / 4;
        this.updateCamera();
    }
    
    fitToPoints() {
        if (this.points.length === 0) return;
        
        // Calculate bounding box
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;
        
        for (const point of this.points) {
            minX = Math.min(minX, point[0]);
            maxX = Math.max(maxX, point[0]);
            minY = Math.min(minY, point[1]);
            maxY = Math.max(maxY, point[1]);
            minZ = Math.min(minZ, point[2]);
            maxZ = Math.max(maxZ, point[2]);
        }
        
        const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
        this.spherical.radius = size * 2;
        this.updateCamera();
    }
    
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        this.renderer.render(this.scene, this.camera);
    }
}

// Scanner Controller
class ScannerController {
    constructor(viewer) {
        this.viewer = viewer;
        this.socket = null;
        this.state = 'idle';
        
        this.initSocket();
        this.initUI();
    }
    
    initSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
            this.socket.emit('request_status');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('points', (data) => {
            this.viewer.addPoints(data.points);
            this.updatePointCount(this.viewer.points.length);
        });
        
        this.socket.on('points_batch', (data) => {
            this.viewer.addPoints(data.points);
            this.updatePointCount(this.viewer.points.length);
        });
        
        this.socket.on('progress', (data) => {
            this.updateProgress(data);
        });
        
        this.socket.on('status', (data) => {
            this.updateProgress(data);
            this.updateState(data.state);
        });
        
        this.socket.on('state', (data) => {
            this.updateState(data.state);
        });
    }
    
    initUI() {
        // Scan controls
        document.getElementById('btn-start').addEventListener('click', () => this.startScan());
        document.getElementById('btn-stop').addEventListener('click', () => this.stopScan());
        document.getElementById('btn-pause').addEventListener('click', () => this.pauseScan());
        document.getElementById('btn-resume').addEventListener('click', () => this.resumeScan());
        document.getElementById('btn-reset').addEventListener('click', () => this.resetScan());
        
        // View controls
        document.getElementById('point-size').addEventListener('input', (e) => {
            this.viewer.setPointSize(parseInt(e.target.value));
        });
        
        document.getElementById('btn-reset-view').addEventListener('click', () => {
            this.viewer.resetView();
        });
        
        document.getElementById('btn-fit-view').addEventListener('click', () => {
            this.viewer.fitToPoints();
        });
        
        document.getElementById('show-axes').addEventListener('change', (e) => {
            this.viewer.setAxesVisible(e.target.checked);
        });
        
        document.getElementById('show-grid').addEventListener('change', (e) => {
            this.viewer.setGridVisible(e.target.checked);
        });
        
        // Export controls
        document.getElementById('btn-export-ply').addEventListener('click', () => {
            window.location.href = '/api/export/ply';
        });
        
        document.getElementById('btn-export-pcd').addEventListener('click', () => {
            window.location.href = '/api/export/pcd';
        });
    }
    
    async startScan() {
        try {
            const response = await fetch('/api/scan/start', { method: 'POST' });
            const data = await response.json();
            console.log('Start scan response:', data);
        } catch (error) {
            console.error('Error starting scan:', error);
        }
    }
    
    async stopScan() {
        try {
            const response = await fetch('/api/scan/stop', { method: 'POST' });
            const data = await response.json();
            console.log('Stop scan response:', data);
        } catch (error) {
            console.error('Error stopping scan:', error);
        }
    }
    
    async pauseScan() {
        try {
            const response = await fetch('/api/scan/pause', { method: 'POST' });
            const data = await response.json();
            console.log('Pause scan response:', data);
        } catch (error) {
            console.error('Error pausing scan:', error);
        }
    }
    
    async resumeScan() {
        try {
            const response = await fetch('/api/scan/resume', { method: 'POST' });
            const data = await response.json();
            console.log('Resume scan response:', data);
        } catch (error) {
            console.error('Error resuming scan:', error);
        }
    }
    
    async resetScan() {
        try {
            const response = await fetch('/api/scan/reset', { method: 'POST' });
            const data = await response.json();
            this.viewer.clearPoints();
            this.updatePointCount(0);
            console.log('Reset scan response:', data);
        } catch (error) {
            console.error('Error resetting scan:', error);
        }
    }
    
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        const connectionStatus = document.getElementById('connection-status');
        
        if (connected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
            connectionStatus.textContent = 'Connected to scanner';
        } else {
            statusDot.classList.remove('connected', 'scanning');
            statusText.textContent = 'Disconnected';
            connectionStatus.textContent = 'Disconnected from scanner';
        }
    }
    
    updateState(state) {
        this.state = state;
        
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        const btnStart = document.getElementById('btn-start');
        const btnStop = document.getElementById('btn-stop');
        const btnPause = document.getElementById('btn-pause');
        const btnResume = document.getElementById('btn-resume');
        
        // Reset classes
        statusDot.classList.remove('scanning', 'error');
        
        switch (state) {
            case 'idle':
                statusText.textContent = 'Idle';
                btnStart.disabled = false;
                btnStop.disabled = true;
                btnPause.disabled = true;
                btnResume.disabled = true;
                break;
            case 'scanning':
                statusText.textContent = 'Scanning...';
                statusDot.classList.add('scanning');
                btnStart.disabled = true;
                btnStop.disabled = false;
                btnPause.disabled = false;
                btnResume.disabled = true;
                break;
            case 'paused':
                statusText.textContent = 'Paused';
                btnStart.disabled = true;
                btnStop.disabled = false;
                btnPause.disabled = true;
                btnResume.disabled = false;
                break;
            case 'stopping':
                statusText.textContent = 'Stopping...';
                btnStart.disabled = true;
                btnStop.disabled = true;
                btnPause.disabled = true;
                btnResume.disabled = true;
                break;
            case 'error':
                statusText.textContent = 'Error';
                statusDot.classList.add('error');
                btnStart.disabled = true;
                btnStop.disabled = true;
                btnPause.disabled = true;
                btnResume.disabled = true;
                break;
        }
    }
    
    updateProgress(data) {
        document.getElementById('servo-angle').textContent = `${Math.round(data.servo_angle)}°`;
        document.getElementById('stepper-angle').textContent = `${Math.round(data.stepper_angle)}°`;
        document.getElementById('point-count').textContent = data.points_collected.toLocaleString();
        
        const progress = data.progress_percent || 0;
        document.getElementById('progress').textContent = `${Math.round(progress)}%`;
        document.getElementById('progress-bar').style.width = `${progress}%`;
        
        let progressText = 'Ready to scan';
        if (data.state === 'scanning') {
            progressText = `Scanning: Cycle ${data.current_cycle} of ${data.total_cycles}`;
        } else if (data.state === 'paused') {
            progressText = 'Scan paused';
        } else if (progress >= 100) {
            progressText = 'Scan complete!';
        }
        document.getElementById('progress-text').textContent = progressText;
    }
    
    updatePointCount(count) {
        document.getElementById('point-count').textContent = count.toLocaleString();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const viewer = new PointCloudViewer('viewer');
    const controller = new ScannerController(viewer);
    
    // Make available globally for debugging
    window.viewer = viewer;
    window.controller = controller;
});
