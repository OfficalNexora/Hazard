"""
MOD-EVAC-MS - Diorama/Building 3D Model Configuration

This module defines the spatial layout of the monitored environment in a
scale-agnostic way. All coordinates use METERS as the base unit, making
it work for both dioramas (0.3m) and real buildings (30m).

The coordinate system:
- Origin (0,0,0) is at the southwest corner, ground level
- X-axis: West to East
- Y-axis: South to North  
- Z-axis: Ground to Sky (floor height)

I use normalized zone IDs that map to physical LED positions, so the same
configuration works regardless of actual LED count or placement.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json
import math


@dataclass
class LEDZone:
    """A physical zone mapped to LEDs."""
    id: int
    name: str
    floor: int
    # Center position in meters
    position: Tuple[float, float, float]
    # Bounding radius in meters (for proximity detection)
    radius: float
    # LED indices this zone controls
    led_indices: List[int]
    # Hazard proximity flags (which hazards make this zone RED)
    danger_on_fire: bool = True
    danger_on_flood: bool = True
    danger_on_seismic: bool = True
    # Is this an exit/evacuation point?
    is_exit: bool = False


@dataclass
class Building:
    """A building structure with multiple floors and zones."""
    id: str
    name: str
    floors: int
    # Bounding box in meters: (min_x, min_y, min_z, max_x, max_y, max_z)
    bounds: Tuple[float, float, float, float, float, float]
    zones: List[LEDZone] = field(default_factory=list)
    
    def floor_height(self) -> float:
        """Height per floor in meters."""
        _, _, min_z, _, _, max_z = self.bounds
        return (max_z - min_z) / self.floors


@dataclass
class CameraConfig:
    """ESP32-CAM position and calibration."""
    # Camera position in meters
    position: Tuple[float, float, float]
    # Viewing direction (unit vector)
    direction: Tuple[float, float, float]
    # Field of view in degrees
    fov_horizontal: float
    fov_vertical: float
    # Image resolution
    resolution: Tuple[int, int]
    # 4-point calibration: list of (pixel_x, pixel_y, world_x, world_y, world_z)
    calibration_points: List[Tuple[int, int, float, float, float]] = field(default_factory=list)


@dataclass
class DioramaModel:
    """
    Complete spatial model of the monitored environment.
    
    Scale-agnostic: Use meters for all measurements.
    - Diorama example: 0.3m x 0.2m footprint
    - Real building example: 30m x 20m footprint
    """
    name: str
    # Total environment bounds (meters)
    bounds: Tuple[float, float, float, float, float, float]
    buildings: List[Building] = field(default_factory=list)
    exits: List[LEDZone] = field(default_factory=list)
    cameras: List[CameraConfig] = field(default_factory=list)
    
    # Adjacency graph for pathfinding (zone_id -> list of connected zone_ids)
    zone_connections: Dict[int, List[int]] = field(default_factory=dict)
    
    def get_all_zones(self) -> List[LEDZone]:
        """Get all zones including building zones and exits."""
        zones = []
        for building in self.buildings:
            zones.extend(building.zones)
        zones.extend(self.exits)
        return zones
    
    def get_zone_by_id(self, zone_id: int) -> Optional[LEDZone]:
        """Find a zone by its ID."""
        for zone in self.get_all_zones():
            if zone.id == zone_id:
                return zone
        return None
    
    def find_nearest_zone(self, position: Tuple[float, float, float]) -> Optional[LEDZone]:
        """Find the zone closest to a 3D position."""
        x, y, z = position
        nearest = None
        min_dist = float('inf')
        
        for zone in self.get_all_zones():
            zx, zy, zz = zone.position
            dist = math.sqrt((x - zx)**2 + (y - zy)**2 + (z - zz)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = zone
        
        return nearest
    
    def find_zones_in_radius(self, position: Tuple[float, float, float], radius: float) -> List[LEDZone]:
        """Find all zones within a radius of a position."""
        x, y, z = position
        nearby = []
        
        for zone in self.get_all_zones():
            zx, zy, zz = zone.position
            dist = math.sqrt((x - zx)**2 + (y - zy)**2 + (z - zz)**2)
            if dist <= radius:
                nearby.append(zone)
        
        return nearby
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "name": self.name,
            "bounds": self.bounds,
            "buildings": [
                {
                    "id": b.id,
                    "name": b.name,
                    "floors": b.floors,
                    "bounds": b.bounds,
                    "zones": [
                        {
                            "id": z.id,
                            "name": z.name,
                            "floor": z.floor,
                            "position": z.position,
                            "radius": z.radius,
                            "led_indices": z.led_indices,
                            "danger_on_fire": z.danger_on_fire,
                            "danger_on_flood": z.danger_on_flood,
                            "danger_on_seismic": z.danger_on_seismic,
                            "is_exit": z.is_exit
                        }
                        for z in b.zones
                    ]
                }
                for b in self.buildings
            ],
            "exits": [
                {
                    "id": e.id,
                    "name": e.name,
                    "position": e.position,
                    "led_indices": e.led_indices,
                    "is_exit": True
                }
                for e in self.exits
            ],
            "cameras": [
                {
                    "position": c.position,
                    "direction": c.direction,
                    "fov_horizontal": c.fov_horizontal,
                    "fov_vertical": c.fov_vertical,
                    "resolution": c.resolution
                }
                for c in self.cameras
            ],
            "zone_connections": self.zone_connections
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# ============================================================
# DEFAULT CONFIGURATION (2-Story Diorama Example)
# ============================================================
# This is a template - modify for your actual layout
# All measurements in METERS (scale down for diorama)

def create_default_diorama(scale: float = 0.01) -> DioramaModel:
    """
    Create a default diorama model.
    
    Args:
        scale: Conversion factor. 0.01 means 1 unit = 1cm (diorama).
               Use 1.0 for real-world meters.
    
    Returns:
        Configured DioramaModel
    """
    # Total footprint: 30cm x 20cm diorama (or 30m x 20m real)
    total_width = 30 * scale   # X-axis
    total_depth = 20 * scale   # Y-axis
    floor_height = 3 * scale   # Each floor is 3 units tall
    
    # Building A: 2-story, positioned on the left
    building_a = Building(
        id="A",
        name="Building A",
        floors=2,
        bounds=(0, 0, 0, 12 * scale, 15 * scale, 6 * scale),
        zones=[
            LEDZone(
                id=1,
                name="A-Floor1",
                floor=1,
                position=(6 * scale, 7.5 * scale, 1.5 * scale),
                radius=5 * scale,
                led_indices=[3, 4, 5, 6],
                danger_on_seismic=True
            ),
            LEDZone(
                id=2,
                name="A-Floor2",
                floor=2,
                position=(6 * scale, 7.5 * scale, 4.5 * scale),
                radius=5 * scale,
                led_indices=[7, 8, 9, 10],
                danger_on_seismic=True
            ),
        ]
    )
    
    # Building B: 2-story, positioned on the right
    building_b = Building(
        id="B",
        name="Building B",
        floors=2,
        bounds=(18 * scale, 0, 0, 30 * scale, 15 * scale, 6 * scale),
        zones=[
            LEDZone(
                id=4,
                name="B-Floor1",
                floor=1,
                position=(24 * scale, 7.5 * scale, 1.5 * scale),
                radius=5 * scale,
                led_indices=[13, 14, 15, 16],
                danger_on_fire=True,
                danger_on_seismic=True
            ),
            LEDZone(
                id=5,
                name="B-Floor2",
                floor=2,
                position=(24 * scale, 7.5 * scale, 4.5 * scale),
                radius=5 * scale,
                led_indices=[17, 18, 19, 20],
                danger_on_seismic=True
            ),
        ]
    )
    
    # Exits
    exit_1 = LEDZone(
        id=0,
        name="Main Exit",
        floor=0,
        position=(0, 10 * scale, 0),
        radius=3 * scale,
        led_indices=[0, 1, 2],
        is_exit=True,
        danger_on_fire=False,
        danger_on_flood=True,
        danger_on_seismic=False
    )
    
    exit_2 = LEDZone(
        id=3,
        name="Secondary Exit",
        floor=0,
        position=(15 * scale, 0, 0),
        radius=3 * scale,
        led_indices=[11, 12],
        is_exit=True,
        danger_on_fire=True,
        danger_on_flood=True,
        danger_on_seismic=False
    )
    
    # Camera (mounted above, looking down)
    camera = CameraConfig(
        position=(15 * scale, 10 * scale, 20 * scale),
        direction=(0, 0, -1),  # Looking straight down
        fov_horizontal=90,
        fov_vertical=66,
        resolution=(640, 480)
    )
    
    # Zone connections for pathfinding (which zones connect to which)
    connections = {
        0: [1],        # Exit 1 connects to A-Floor1
        1: [0, 2, 3],  # A-Floor1 connects to Exit1, A-Floor2, Exit2
        2: [1],        # A-Floor2 connects to A-Floor1 (stairs)
        3: [1, 4],     # Exit 2 connects to A-Floor1, B-Floor1
        4: [3, 5],     # B-Floor1 connects to Exit2, B-Floor2
        5: [4],        # B-Floor2 connects to B-Floor1 (stairs)
    }
    
    return DioramaModel(
        name="Default Diorama",
        bounds=(0, 0, 0, total_width, total_depth, 6 * scale),
        buildings=[building_a, building_b],
        exits=[exit_1, exit_2],
        cameras=[camera],
        zone_connections=connections
    )


# Singleton instance - loaded on import
_current_model: Optional[DioramaModel] = None


def get_model() -> DioramaModel:
    """Get the current diorama model (loads from config.json if exists, else default)."""
    global _current_model
    if _current_model is None:
        # Try to load from JSON config first
        import os
        config_paths = [
            os.path.join(os.path.dirname(__file__), "diorama_config.json"),
            "diorama_config.json",
            "backend/diorama_config.json"
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    _current_model = load_model_from_json(config_path)
                    print(f"[DioramaModel] Loaded config from {config_path}")
                    return _current_model
                except Exception as e:
                    print(f"[DioramaModel] Failed to load {config_path}: {e}")
        
        # Fall back to default
        _current_model = create_default_diorama()
        print("[DioramaModel] Using default configuration")
    return _current_model


def set_model(model: DioramaModel) -> None:
    """Set a custom diorama model."""
    global _current_model
    _current_model = model


def load_model_from_json(json_path: str) -> DioramaModel:
    """Load a diorama model from a JSON file."""
    # Implementation for loading custom configurations
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Parse buildings
    buildings = []
    for b_data in data.get("buildings", []):
        zones = [
            LEDZone(
                id=z["id"],
                name=z["name"],
                floor=z["floor"],
                position=tuple(z["position"]),
                radius=z["radius"],
                led_indices=z["led_indices"],
                danger_on_fire=z.get("danger_on_fire", True),
                danger_on_flood=z.get("danger_on_flood", True),
                danger_on_seismic=z.get("danger_on_seismic", True),
                is_exit=z.get("is_exit", False)
            )
            for z in b_data.get("zones", [])
        ]
        buildings.append(Building(
            id=b_data["id"],
            name=b_data["name"],
            floors=b_data["floors"],
            bounds=tuple(b_data["bounds"]),
            zones=zones
        ))
    
    # Parse exits
    exits = [
        LEDZone(
            id=e["id"],
            name=e["name"],
            floor=0,
            position=tuple(e["position"]),
            radius=e.get("radius", 1.0),
            led_indices=e["led_indices"],
            is_exit=True
        )
        for e in data.get("exits", [])
    ]
    
    # Parse cameras
    cameras = [
        CameraConfig(
            position=tuple(c["position"]),
            direction=tuple(c.get("direction", (0, 0, -1))),
            fov_horizontal=c.get("fov_horizontal", 90),
            fov_vertical=c.get("fov_vertical", 66),
            resolution=tuple(c.get("resolution", (640, 480)))
        )
        for c in data.get("cameras", [])
    ]
    
    model = DioramaModel(
        name=data.get("name", "Custom Model"),
        bounds=tuple(data["bounds"]),
        buildings=buildings,
        exits=exits,
        cameras=cameras,
        zone_connections=data.get("zone_connections", {})
    )
    
    set_model(model)
    return model
