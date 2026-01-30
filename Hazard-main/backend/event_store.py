"""
MOD-EVAC-MS - Event Storage and Replay System

This module handles logging of all hazard events with timestamps and
3D positions, enabling historical analysis and event replay.

Events are stored in SQLite for persistence and can be queried by
time range for replay in the 3D viewer.
"""

import sqlite3
import json
import time
import threading
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from . import diorama_model


@dataclass
class HazardEvent:
    """A recorded hazard or detection event."""
    id: Optional[int]
    timestamp: float  # Unix timestamp
    event_type: str   # fire, flood, seismic, person, etc.
    # 3D position in world coordinates
    position_x: float
    position_y: float
    position_z: float
    # Associated zone
    zone_id: Optional[int]
    zone_name: Optional[str]
    # Detection metadata
    confidence: float
    # Additional data (JSON)
    metadata: Dict
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "position": {
                "x": self.position_x,
                "y": self.position_y,
                "z": self.position_z
            },
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class EventStore:
    """
    SQLite-backed event storage for hazard detection history.
    
    Thread-safe for concurrent access from multiple workers.
    """
    
    def __init__(self, db_path: str = "system.db"):
        """
        Initialize the event store.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hazard_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    position_x REAL NOT NULL,
                    position_y REAL NOT NULL,
                    position_z REAL NOT NULL,
                    zone_id INTEGER,
                    zone_name TEXT,
                    confidence REAL,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Index for time-range queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON hazard_events(timestamp)
            """)
            
            # Index for event type queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON hazard_events(event_type)
            """)
            
            conn.commit()
            conn.close()
    
    def log_event(self, event_type: str, position: Tuple[float, float, float],
                  zone_id: Optional[int] = None, zone_name: Optional[str] = None,
                  confidence: float = 1.0, metadata: Optional[Dict] = None) -> int:
        """
        Log a new hazard event.
        
        Args:
            event_type: Type of event (fire, flood, seismic, person, etc.)
            position: (x, y, z) world coordinates
            zone_id: Associated zone ID (optional)
            zone_name: Associated zone name (optional)
            confidence: Detection confidence (0-1)
            metadata: Additional data dict
        
        Returns:
            Event ID
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO hazard_events 
                (timestamp, event_type, position_x, position_y, position_z,
                 zone_id, zone_name, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                time.time(),
                event_type,
                position[0],
                position[1],
                position[2],
                zone_id,
                zone_name,
                confidence,
                json.dumps(metadata or {})
            ))
            
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return event_id
    
    def get_events(self, start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   event_type: Optional[str] = None,
                   limit: int = 1000) -> List[HazardEvent]:
        """
        Query events by time range and/or type.
        
        Args:
            start_time: Start of time range (Unix timestamp)
            end_time: End of time range (Unix timestamp)
            event_type: Filter by event type
            limit: Maximum number of events to return
        
        Returns:
            List of HazardEvent objects
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            query = "SELECT * FROM hazard_events WHERE 1=1"
            params = []
            
            if start_time is not None:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time is not None:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            if event_type is not None:
                query += " AND event_type = ?"
                params.append(event_type)
            
            query += " ORDER BY timestamp ASC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                events.append(HazardEvent(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    event_type=row['event_type'],
                    position_x=row['position_x'],
                    position_y=row['position_y'],
                    position_z=row['position_z'],
                    zone_id=row['zone_id'],
                    zone_name=row['zone_name'],
                    confidence=row['confidence'],
                    metadata=json.loads(row['metadata'] or '{}')
                ))
            
            return events
    
    def get_latest_events(self, event_type: Optional[str] = None,
                          count: int = 10) -> List[HazardEvent]:
        """Get the most recent events."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            if event_type:
                cursor.execute("""
                    SELECT * FROM hazard_events 
                    WHERE event_type = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (event_type, count))
            else:
                cursor.execute("""
                    SELECT * FROM hazard_events 
                    ORDER BY timestamp DESC LIMIT ?
                """, (count,))
            
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                events.append(HazardEvent(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    event_type=row['event_type'],
                    position_x=row['position_x'],
                    position_y=row['position_y'],
                    position_z=row['position_z'],
                    zone_id=row['zone_id'],
                    zone_name=row['zone_name'],
                    confidence=row['confidence'],
                    metadata=json.loads(row['metadata'] or '{}')
                ))
            
            # Reverse to chronological order
            return list(reversed(events))
    
    def get_active_hazards(self, window_seconds: float = 30.0) -> List[HazardEvent]:
        """
        Get currently active hazards (detected within time window).
        
        Args:
            window_seconds: How far back to look for active hazards
        
        Returns:
            List of recent hazard events
        """
        start_time = time.time() - window_seconds
        return self.get_events(
            start_time=start_time,
            event_type=None,  # All types
            limit=100
        )
    
    def get_timeline_summary(self, start_time: float, end_time: float,
                             bucket_seconds: float = 60.0) -> List[Dict]:
        """
        Get a summary of events grouped by time buckets.
        
        Useful for timeline visualization in the frontend.
        
        Args:
            start_time: Start of range
            end_time: End of range
            bucket_seconds: Size of each time bucket
        
        Returns:
            List of dicts with bucket start time and event counts
        """
        events = self.get_events(start_time, end_time, limit=10000)
        
        buckets = []
        current_bucket_start = start_time
        
        while current_bucket_start < end_time:
            bucket_end = current_bucket_start + bucket_seconds
            
            # Count events in this bucket
            bucket_events = [e for e in events 
                           if current_bucket_start <= e.timestamp < bucket_end]
            
            if bucket_events:
                # Group by type
                type_counts = {}
                for event in bucket_events:
                    type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
                
                buckets.append({
                    "start": current_bucket_start,
                    "end": bucket_end,
                    "total": len(bucket_events),
                    "by_type": type_counts
                })
            
            current_bucket_start = bucket_end
        
        return buckets
    
    def clear_old_events(self, max_age_seconds: float = 86400 * 7) -> int:
        """
        Delete events older than max_age.
        
        Args:
            max_age_seconds: Maximum age in seconds (default 7 days)
        
        Returns:
            Number of deleted events
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cutoff = time.time() - max_age_seconds
            cursor.execute("""
                DELETE FROM hazard_events WHERE timestamp < ?
            """, (cutoff,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted


# Singleton instance
_event_store: Optional[EventStore] = None


def get_event_store(db_path: str = "system.db") -> EventStore:
    """Get or create the event store singleton."""
    global _event_store
    if _event_store is None:
        _event_store = EventStore(db_path)
    return _event_store
