"""
Thread-safe point cloud buffer with spherical to Cartesian conversion.
"""

import logging
import math
import threading
from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Point3D:
    """A single 3D point with optional metadata."""
    x: float
    y: float
    z: float
    # Original spherical coordinates
    theta: float = 0.0  # Servo angle (elevation)
    phi: float = 0.0    # Stepper angle (azimuth)
    distance: float = 0.0  # Original distance in mm
    
    def to_tuple(self) -> Tuple[float, float, float]:
        """Return point as (x, y, z) tuple."""
        return (self.x, self.y, self.z)
    
    def to_list(self) -> List[float]:
        """Return point as [x, y, z] list."""
        return [self.x, self.y, self.z]


class PointCloud:
    """
    Thread-safe point cloud buffer for collecting 3D scan data.
    
    Handles conversion from spherical coordinates (servo angle, stepper angle, distance)
    to Cartesian coordinates (x, y, z).
    """
    
    def __init__(self, max_points: int = 100000):
        """
        Initialize the point cloud buffer.
        
        Args:
            max_points: Maximum number of points to store (prevents memory issues)
        """
        self._points: List[Point3D] = []
        self._lock = threading.RLock()
        self._max_points = max_points
        self._on_point_added: List[Callable[[Point3D], None]] = []
        self._on_batch_added: List[Callable[[List[Point3D]], None]] = []
        
    @staticmethod
    def spherical_to_cartesian(theta_deg: float, phi_deg: float, 
                                distance_mm: float) -> Tuple[float, float, float]:
        """
        Convert spherical coordinates to Cartesian.
        
        Coordinate system:
        - theta (servo angle): 0° = pointing up (+Z), 180° = pointing down (-Z)
        - phi (stepper angle): 0° = +X axis, 90° = +Y axis
        - distance: radius in mm
        
        Args:
            theta_deg: Servo angle in degrees (0-180, elevation)
            phi_deg: Stepper angle in degrees (0-360, azimuth)
            distance_mm: Distance in millimeters
            
        Returns:
            Tuple of (x, y, z) in millimeters
        """
        # Convert to radians
        theta = math.radians(theta_deg)
        phi = math.radians(phi_deg)
        
        # Spherical to Cartesian conversion
        # Using physics convention: theta from +Z axis, phi from +X in XY plane
        x = distance_mm * math.sin(theta) * math.cos(phi)
        y = distance_mm * math.sin(theta) * math.sin(phi)
        z = distance_mm * math.cos(theta)
        
        return (x, y, z)
    
    def add_point_spherical(self, theta: float, phi: float, distance: float) -> Optional[Point3D]:
        """
        Add a point using spherical coordinates.
        
        Args:
            theta: Servo angle in degrees (0-180)
            phi: Stepper angle in degrees (0-360)
            distance: Distance in millimeters
            
        Returns:
            The created Point3D object, or None if distance is invalid
        """
        if distance is None or distance <= 0:
            logger.debug(f"Invalid distance: {distance}")
            return None
            
        # Convert to Cartesian
        x, y, z = self.spherical_to_cartesian(theta, phi, distance)
        
        # Create point
        point = Point3D(
            x=x, y=y, z=z,
            theta=theta, phi=phi, distance=distance
        )
        
        # Add to buffer (thread-safe)
        with self._lock:
            if len(self._points) >= self._max_points:
                # Remove oldest points if at capacity
                self._points = self._points[1000:]  # Remove first 1000 points
                logger.warning(f"Point cloud at capacity, removed oldest 1000 points")
            
            self._points.append(point)
        
        # Notify listeners
        for callback in self._on_point_added:
            try:
                callback(point)
            except Exception as e:
                logger.error(f"Error in point callback: {e}")
        
        return point
    
    def add_point_cartesian(self, x: float, y: float, z: float) -> Point3D:
        """
        Add a point using Cartesian coordinates directly.
        
        Args:
            x, y, z: Coordinates in millimeters
            
        Returns:
            The created Point3D object
        """
        point = Point3D(x=x, y=y, z=z)
        
        with self._lock:
            if len(self._points) >= self._max_points:
                self._points = self._points[1000:]
            self._points.append(point)
        
        for callback in self._on_point_added:
            try:
                callback(point)
            except Exception as e:
                logger.error(f"Error in point callback: {e}")
        
        return point
    
    def get_points(self) -> List[Point3D]:
        """
        Get a copy of all points.
        
        Returns:
            List of Point3D objects
        """
        with self._lock:
            return list(self._points)
    
    def get_points_as_numpy(self) -> np.ndarray:
        """
        Get points as numpy array (N x 3).
        
        Returns:
            Numpy array of shape (N, 3) with x, y, z columns
        """
        with self._lock:
            if not self._points:
                return np.array([]).reshape(0, 3)
            return np.array([[p.x, p.y, p.z] for p in self._points])
    
    def get_points_as_list(self) -> List[List[float]]:
        """
        Get points as list of [x, y, z] lists.
        
        Returns:
            List of [x, y, z] lists
        """
        with self._lock:
            return [p.to_list() for p in self._points]
    
    def get_latest_points(self, count: int) -> List[Point3D]:
        """
        Get the most recent N points.
        
        Args:
            count: Number of points to retrieve
            
        Returns:
            List of most recent Point3D objects
        """
        with self._lock:
            return list(self._points[-count:])
    
    def get_point_count(self) -> int:
        """
        Get the number of points in the cloud.
        
        Returns:
            Number of points
        """
        with self._lock:
            return len(self._points)
    
    def clear(self):
        """Clear all points from the buffer."""
        with self._lock:
            self._points.clear()
        logger.info("Point cloud cleared")
    
    def on_point_added(self, callback: Callable[[Point3D], None]):
        """
        Register a callback to be called when a point is added.
        
        Args:
            callback: Function that takes a Point3D argument
        """
        self._on_point_added.append(callback)
    
    def on_batch_added(self, callback: Callable[[List[Point3D]], None]):
        """
        Register a callback to be called when a batch of points is ready.
        
        Args:
            callback: Function that takes a list of Point3D objects
        """
        self._on_batch_added.append(callback)
    
    def notify_batch(self, points: List[Point3D]):
        """
        Notify listeners about a batch of points.
        
        Args:
            points: List of points to notify about
        """
        for callback in self._on_batch_added:
            try:
                callback(points)
            except Exception as e:
                logger.error(f"Error in batch callback: {e}")
    
    def get_bounds(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Get the bounding box of the point cloud.
        
        Returns:
            Tuple of (min_point, max_point) where each is (x, y, z)
        """
        with self._lock:
            if not self._points:
                return ((0, 0, 0), (0, 0, 0))
            
            points = np.array([[p.x, p.y, p.z] for p in self._points])
            min_pt = tuple(points.min(axis=0))
            max_pt = tuple(points.max(axis=0))
            return (min_pt, max_pt)
    
    def get_center(self) -> Tuple[float, float, float]:
        """
        Get the center point of the cloud.
        
        Returns:
            Center point as (x, y, z)
        """
        with self._lock:
            if not self._points:
                return (0.0, 0.0, 0.0)
            
            points = np.array([[p.x, p.y, p.z] for p in self._points])
            center = points.mean(axis=0)
            return tuple(center)
    
    def __len__(self) -> int:
        """Return number of points."""
        return self.get_point_count()
    
    def __iter__(self):
        """Iterate over points."""
        with self._lock:
            return iter(list(self._points))
