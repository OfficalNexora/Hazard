"""
MOD-EVAC-MS - Camera to 3D World Coordinate Mapper

This module handles the transformation from camera pixel coordinates to
3D world coordinates. It uses perspective projection math to map detected
hazards from the camera image to their physical location in the diorama.

The key insight: I use a homography matrix computed from calibration points
to map any pixel (u, v) to world coordinates (x, y). The Z-coordinate is
estimated based on the detection size or assumed to be ground level.

This is scale-agnostic - works for dioramas and real buildings.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass

# Import the diorama model
from . import diorama_model


@dataclass
class DetectionResult:
    """A detection mapped to 3D space."""
    class_name: str
    confidence: float
    # Original pixel bounding box
    pixel_bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    # Center in 3D world coordinates
    world_position: Tuple[float, float, float]
    # Nearest LED zone
    zone_id: Optional[int]
    zone_name: Optional[str]


class CameraMapper:
    """
    Maps camera pixel coordinates to 3D world coordinates.
    
    Uses homography (perspective transform) for ground-plane mapping,
    with height estimation based on detection characteristics.
    """
    
    def __init__(self, camera_index: int = 0):
        """
        Initialize the mapper for a specific camera.
        
        Args:
            camera_index: Index of the camera in the diorama model
        """
        self.model = diorama_model.get_model()
        self.camera_index = camera_index
        self.camera = self.model.cameras[camera_index] if self.model.cameras else None
        
        # Homography matrix (computed from calibration)
        self._homography: Optional[np.ndarray] = None
        self._inverse_homography: Optional[np.ndarray] = None
        
        # If we have calibration points, compute homography
        if self.camera and len(self.camera.calibration_points) >= 4:
            self._compute_homography()
    
    def _compute_homography(self) -> None:
        """
        Compute the homography matrix from calibration points.
        
        Requires at least 4 calibration points mapping pixel coords to world coords.
        """
        if not self.camera or len(self.camera.calibration_points) < 4:
            return
        
        # Extract pixel points and world points (ground plane, z=0)
        pixel_points = []
        world_points = []
        
        for px, py, wx, wy, wz in self.camera.calibration_points:
            pixel_points.append([px, py])
            world_points.append([wx, wy])  # We project to ground plane
        
        pixel_points = np.float32(pixel_points)
        world_points = np.float32(world_points)
        
        # Compute homography using OpenCV-style DLT
        # H maps pixel -> world: world = H @ pixel
        self._homography = self._compute_perspective_transform(pixel_points, world_points)
        
        # Inverse for world -> pixel
        if self._homography is not None:
            self._inverse_homography = np.linalg.inv(self._homography)
    
    def _compute_perspective_transform(self, src: np.ndarray, dst: np.ndarray) -> np.ndarray:
        """
        Compute perspective transform matrix using Direct Linear Transform.
        
        This is a simplified implementation. For production, use cv2.getPerspectiveTransform.
        """
        # Build the system of equations
        n = len(src)
        A = []
        
        for i in range(n):
            x, y = src[i]
            u, v = dst[i]
            A.append([-x, -y, -1, 0, 0, 0, x*u, y*u, u])
            A.append([0, 0, 0, -x, -y, -1, x*v, y*v, v])
        
        A = np.array(A)
        
        # Solve using SVD
        _, _, Vt = np.linalg.svd(A)
        H = Vt[-1].reshape(3, 3)
        
        # Normalize
        H = H / H[2, 2]
        
        return H
    
    def pixel_to_world(self, pixel_x: int, pixel_y: int, assumed_z: float = 0.0) -> Tuple[float, float, float]:
        """
        Convert pixel coordinates to world coordinates.
        
        Args:
            pixel_x: X coordinate in image
            pixel_y: Y coordinate in image
            assumed_z: Assumed height (default ground level)
        
        Returns:
            (world_x, world_y, world_z) in meters
        """
        if self._homography is None:
            # Fallback: simple linear mapping if no calibration
            return self._simple_mapping(pixel_x, pixel_y, assumed_z)
        
        # Apply homography
        pixel = np.array([pixel_x, pixel_y, 1.0])
        world_h = self._homography @ pixel
        
        # Normalize homogeneous coordinates
        world_x = world_h[0] / world_h[2]
        world_y = world_h[1] / world_h[2]
        
        return (float(world_x), float(world_y), float(assumed_z))
    
    def _simple_mapping(self, pixel_x: int, pixel_y: int, assumed_z: float) -> Tuple[float, float, float]:
        """
        Simple linear mapping when no calibration is available.
        
        Assumes camera is looking straight down at the center of the diorama.
        """
        if not self.camera:
            # No camera config - return normalized coords
            return (pixel_x / 640.0, pixel_y / 480.0, assumed_z)
        
        # Get bounds
        min_x, min_y, _, max_x, max_y, _ = self.model.bounds
        res_x, res_y = self.camera.resolution
        
        # Linear interpolation
        world_x = min_x + (pixel_x / res_x) * (max_x - min_x)
        world_y = min_y + (pixel_y / res_y) * (max_y - min_y)
        
        return (world_x, world_y, assumed_z)
    
    def world_to_pixel(self, world_x: float, world_y: float, world_z: float = 0.0) -> Tuple[int, int]:
        """
        Convert world coordinates to pixel coordinates.
        
        Useful for overlaying zone boundaries on camera feed.
        """
        if self._inverse_homography is None:
            # Fallback: simple linear mapping
            if not self.camera:
                return (int(world_x * 640), int(world_y * 480))
            
            min_x, min_y, _, max_x, max_y, _ = self.model.bounds
            res_x, res_y = self.camera.resolution
            
            pixel_x = int((world_x - min_x) / (max_x - min_x) * res_x)
            pixel_y = int((world_y - min_y) / (max_y - min_y) * res_y)
            
            return (pixel_x, pixel_y)
        
        # Apply inverse homography
        world = np.array([world_x, world_y, 1.0])
        pixel_h = self._inverse_homography @ world
        
        pixel_x = int(pixel_h[0] / pixel_h[2])
        pixel_y = int(pixel_h[1] / pixel_h[2])
        
        return (pixel_x, pixel_y)
    
    def estimate_height(self, bbox: Tuple[int, int, int, int], class_name: str) -> float:
        """
        Estimate the Z-coordinate based on detection characteristics.
        
        For fires and smoke, assume they're at floor level or above.
        For people, estimate based on bounding box size.
        """
        x1, y1, x2, y2 = bbox
        height_pixels = y2 - y1
        
        # Get average floor height from model
        floor_height = 0.0
        if self.model.buildings:
            floor_height = self.model.buildings[0].floor_height()
        
        # Heuristics based on detection type
        if class_name in ['fire', 'flame', 'smoke']:
            # Fire/smoke could be at any height, assume mid-floor
            return floor_height * 0.5
        elif class_name in ['person', 'people']:
            # People are at ground level
            return 0.0
        elif class_name in ['flood', 'water']:
            # Water is at ground level
            return 0.0
        else:
            # Default to ground
            return 0.0
    
    def map_detection(self, class_name: str, confidence: float, 
                      bbox: Tuple[int, int, int, int]) -> DetectionResult:
        """
        Map a detection from pixel space to world space.
        
        Args:
            class_name: Detected class (fire, smoke, flood, person, etc.)
            confidence: Detection confidence
            bbox: Bounding box (x1, y1, x2, y2)
        
        Returns:
            DetectionResult with world coordinates and nearest zone
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        # Estimate height
        z = self.estimate_height(bbox, class_name)
        
        # Map to world coordinates
        world_x, world_y, _ = self.pixel_to_world(center_x, center_y, z)
        world_position = (world_x, world_y, z)
        
        # Find nearest zone
        zone = self.model.find_nearest_zone(world_position)
        
        return DetectionResult(
            class_name=class_name,
            confidence=confidence,
            pixel_bbox=bbox,
            world_position=world_position,
            zone_id=zone.id if zone else None,
            zone_name=zone.name if zone else None
        )
    
    def calibrate(self, calibration_points: List[Tuple[int, int, float, float, float]]) -> None:
        """
        Set calibration points and recompute homography.
        
        Args:
            calibration_points: List of (pixel_x, pixel_y, world_x, world_y, world_z)
        """
        if self.camera:
            self.camera.calibration_points = calibration_points
            self._compute_homography()
    
    def get_zone_pixel_bounds(self, zone_id: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the approximate pixel bounding box for a zone.
        
        Useful for drawing zone overlays on camera feed.
        """
        zone = self.model.get_zone_by_id(zone_id)
        if not zone:
            return None
        
        # Get zone center and radius in world coords
        wx, wy, wz = zone.position
        r = zone.radius
        
        # Project corners to pixel space
        corners = [
            (wx - r, wy - r),
            (wx + r, wy - r),
            (wx + r, wy + r),
            (wx - r, wy + r),
        ]
        
        pixel_corners = [self.world_to_pixel(x, y, wz) for x, y in corners]
        
        # Get bounding box
        xs = [p[0] for p in pixel_corners]
        ys = [p[1] for p in pixel_corners]
        
        return (min(xs), min(ys), max(xs), max(ys))


# Singleton instance
_mapper: Optional[CameraMapper] = None


def get_mapper(camera_index: int = 0) -> CameraMapper:
    """Get or create the camera mapper singleton."""
    global _mapper
    if _mapper is None or _mapper.camera_index != camera_index:
        _mapper = CameraMapper(camera_index)
    return _mapper
