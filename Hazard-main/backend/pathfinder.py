"""
MOD-EVAC-MS - A* Pathfinding for Evacuation Routes

This module calculates optimal evacuation paths through the diorama,
avoiding hazard zones and guiding people to the nearest safe exit.

Key features:
- A* algorithm with hazard-aware cost function
- Dynamic re-routing when new hazards are detected
- Multi-path support (primary and alternate routes)
- LED command generation for the ESP32 controller
"""

import heapq
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

from . import diorama_model
from .diorama_model import LEDZone, DioramaModel


@dataclass
class PathResult:
    """Result of pathfinding calculation."""
    # Ordered list of zone IDs forming the path
    path: List[int]
    # Total cost of the path
    cost: float
    # Destination exit zone
    destination: int
    # Zones to mark as hazardous (red LEDs)
    hazard_zones: List[int]
    # Is this path valid (reaches an exit)?
    valid: bool


class DioramaPathfinder:
    """
    A* pathfinder for evacuation routes.
    
    Uses the zone connection graph from the diorama model to find
    the safest path from any zone to the nearest exit.
    """
    
    # Cost weights
    NORMAL_COST = 1.0
    HAZARD_ADJACENT_COST = 5.0  # Cost to pass near a hazard
    BLOCKED_COST = float('inf')  # Impassable
    
    def __init__(self, model: Optional[DioramaModel] = None):
        """
        Initialize pathfinder with a diorama model.
        
        Args:
            model: DioramaModel to use (defaults to global model)
        """
        self.model = model or diorama_model.get_model()
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build the navigation graph from zone connections."""
        self.graph: Dict[int, List[int]] = {}
        self.zones: Dict[int, LEDZone] = {}
        self.exits: Set[int] = set()
        
        # Index all zones
        for zone in self.model.get_all_zones():
            self.zones[zone.id] = zone
            if zone.is_exit:
                self.exits.add(zone.id)
        
        # Build adjacency from model
        self.graph = dict(self.model.zone_connections)
        
        # Ensure bidirectional connections
        for zone_id, neighbors in list(self.graph.items()):
            for neighbor in neighbors:
                if neighbor not in self.graph:
                    self.graph[neighbor] = []
                if zone_id not in self.graph[neighbor]:
                    self.graph[neighbor].append(zone_id)
    
    def _heuristic(self, zone_id: int, goal_id: int) -> float:
        """
        Heuristic function for A* (Euclidean distance).
        """
        if zone_id not in self.zones or goal_id not in self.zones:
            return 0.0
        
        zone = self.zones[zone_id]
        goal = self.zones[goal_id]
        
        dx = zone.position[0] - goal.position[0]
        dy = zone.position[1] - goal.position[1]
        dz = zone.position[2] - goal.position[2]
        
        return (dx**2 + dy**2 + dz**2) ** 0.5
    
    def _get_edge_cost(self, from_id: int, to_id: int, 
                       hazard_zones: Set[int], hazard_type: str) -> float:
        """
        Get the cost of moving from one zone to another.
        
        Args:
            from_id: Starting zone
            to_id: Destination zone
            hazard_zones: Set of zone IDs currently hazardous
            hazard_type: Type of hazard (fire, flood, seismic)
        
        Returns:
            Movement cost (inf if blocked)
        """
        to_zone = self.zones.get(to_id)
        if not to_zone:
            return self.BLOCKED_COST
        
        # Check if destination is directly hazardous
        if to_id in hazard_zones:
            # Check zone's hazard sensitivity
            if hazard_type == 'fire' and to_zone.danger_on_fire:
                return self.BLOCKED_COST
            elif hazard_type == 'flood' and to_zone.danger_on_flood:
                return self.BLOCKED_COST
            elif hazard_type == 'seismic' and to_zone.danger_on_seismic:
                return self.HAZARD_ADJACENT_COST  # Seismic doesn't fully block
        
        # Check if adjacent to hazard (increased cost but passable)
        neighbors = self.graph.get(to_id, [])
        for neighbor in neighbors:
            if neighbor in hazard_zones:
                return self.HAZARD_ADJACENT_COST
        
        return self.NORMAL_COST
    
    def find_path_to_exit(self, start_zone: int, hazard_zones: List[int],
                          hazard_type: str = 'fire') -> PathResult:
        """
        Find the safest path from a starting zone to the nearest exit.
        
        Args:
            start_zone: Zone ID where evacuation starts
            hazard_zones: List of zone IDs with active hazards
            hazard_type: Type of hazard (fire, flood, seismic)
        
        Returns:
            PathResult with the optimal evacuation route
        """
        if start_zone in self.exits:
            # Already at an exit
            return PathResult(
                path=[start_zone],
                cost=0.0,
                destination=start_zone,
                hazard_zones=hazard_zones,
                valid=True
            )
        
        hazard_set = set(hazard_zones)
        
        # A* search to find nearest exit
        # Priority queue: (f_cost, g_cost, zone_id, path)
        open_set = [(0.0, 0.0, start_zone, [start_zone])]
        closed_set: Set[int] = set()
        
        # Find minimum heuristic to any exit for the start
        min_h = min(self._heuristic(start_zone, exit_id) for exit_id in self.exits)
        open_set[0] = (min_h, 0.0, start_zone, [start_zone])
        
        while open_set:
            f_cost, g_cost, current, path = heapq.heappop(open_set)
            
            if current in self.exits:
                # Found exit!
                return PathResult(
                    path=path,
                    cost=g_cost,
                    destination=current,
                    hazard_zones=hazard_zones,
                    valid=True
                )
            
            if current in closed_set:
                continue
            closed_set.add(current)
            
            # Explore neighbors
            for neighbor in self.graph.get(current, []):
                if neighbor in closed_set:
                    continue
                
                edge_cost = self._get_edge_cost(current, neighbor, hazard_set, hazard_type)
                if edge_cost == float('inf'):
                    continue  # Blocked
                
                new_g = g_cost + edge_cost
                
                # Heuristic: minimum distance to any exit
                h = min(self._heuristic(neighbor, exit_id) for exit_id in self.exits)
                new_f = new_g + h
                
                new_path = path + [neighbor]
                heapq.heappush(open_set, (new_f, new_g, neighbor, new_path))
        
        # No path found
        return PathResult(
            path=[],
            cost=float('inf'),
            destination=-1,
            hazard_zones=hazard_zones,
            valid=False
        )
    
    def find_all_evacuation_routes(self, hazard_zones: List[int],
                                   hazard_type: str = 'fire') -> Dict[int, PathResult]:
        """
        Calculate evacuation routes from all non-exit zones.
        
        Args:
            hazard_zones: List of zone IDs with active hazards
            hazard_type: Type of hazard
        
        Returns:
            Dict mapping zone_id to PathResult
        """
        routes = {}
        
        for zone_id in self.zones:
            if zone_id not in self.exits:
                routes[zone_id] = self.find_path_to_exit(zone_id, hazard_zones, hazard_type)
        
        return routes
    
    def get_led_commands(self, hazard_zones: List[int], 
                         hazard_type: str = 'fire') -> dict:
        """
        Generate LED commands for the ESP32 based on current hazards.
        
        This calculates the safest paths from all zones and returns
        a command that lights safe paths green and hazards red.
        
        Args:
            hazard_zones: List of zone IDs with active hazards
            hazard_type: Type of hazard
        
        Returns:
            JSON command dict for ESP32
        """
        # Get all safe zones (exits + zones on safe paths)
        safe_zones: Set[int] = set(self.exits)
        
        # Calculate routes from all zones
        routes = self.find_all_evacuation_routes(hazard_zones, hazard_type)
        
        for zone_id, result in routes.items():
            if result.valid:
                safe_zones.update(result.path)
        
        # Remove hazard zones from safe set
        safe_zones -= set(hazard_zones)
        
        return {
            "cmd": "set_path",
            "path": list(safe_zones),
            "hazards": hazard_zones
        }
    
    def get_detailed_led_commands(self, hazard_zones: List[int],
                                  hazard_type: str = 'fire') -> dict:
        """
        Generate per-LED commands with RGB values.
        
        More granular control for complex visualizations.
        """
        leds = []
        hazard_set = set(hazard_zones)
        
        for zone_id, zone in self.zones.items():
            if zone_id in hazard_set:
                # Red for hazard zones
                for led_idx in zone.led_indices:
                    leds.append({"i": led_idx, "r": 255, "g": 0, "b": 0})
            elif zone.is_exit:
                # Bright green for exits
                for led_idx in zone.led_indices:
                    leds.append({"i": led_idx, "r": 0, "g": 255, "b": 0})
            else:
                # Check if on a safe path
                route = self.find_path_to_exit(zone_id, hazard_zones, hazard_type)
                if route.valid:
                    # Dim green for safe zones
                    for led_idx in zone.led_indices:
                        leds.append({"i": led_idx, "r": 0, "g": 150, "b": 0})
                else:
                    # Orange for uncertain zones
                    for led_idx in zone.led_indices:
                        leds.append({"i": led_idx, "r": 255, "g": 100, "b": 0})
        
        return {
            "cmd": "set_leds",
            "leds": leds
        }


# Singleton instance
_pathfinder: Optional[DioramaPathfinder] = None


def get_pathfinder() -> DioramaPathfinder:
    """Get or create the pathfinder singleton."""
    global _pathfinder
    if _pathfinder is None:
        _pathfinder = DioramaPathfinder()
    return _pathfinder


def refresh_pathfinder() -> DioramaPathfinder:
    """Refresh the pathfinder (call after model changes)."""
    global _pathfinder
    _pathfinder = DioramaPathfinder()
    return _pathfinder
