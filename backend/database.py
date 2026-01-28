import sqlite3
import json
import os
import time
from typing import List, Dict

DB_PATH = "system.db"
CONFIG_PATH = "config.json"

def init_db():
    """Initialize SQLite database for historical logs"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Detections History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            class_name TEXT,
            confidence REAL,
            bbox TEXT,
            frame_id INTEGER
        )
    ''')
    
    # GSM Contacts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gsm_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT, -- 'sms' or 'call'
            number TEXT,
            name TEXT,
            message TEXT,
            category TEXT DEFAULT 'general'
        )
    ''')

    # Migration: Add category column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE gsm_contacts ADD COLUMN category TEXT DEFAULT 'general'")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Cluster Workers (Classification)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cluster_workers (
            device_id TEXT PRIMARY KEY,
            classification TEXT, -- 'GPU Computing', 'Tracker', 'Logic'
            capabilities TEXT
        )
    ''')

    # Alert History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            state TEXT,
            reason TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def log_detection(class_name: str, confidence: float, bbox: List[float], frame_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO detections (class_name, confidence, bbox, frame_id) VALUES (?, ?, ?, ?)",
            (class_name, confidence, json.dumps(bbox), frame_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Detection log error: {e}")

def log_alert(state: str, reason: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alerts (state, reason) VALUES (?, ?)",
            (state, reason)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Alert log error: {e}")

def get_history(limit: int = 100):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "class": row["class_name"],
                "confidence": row["confidence"],
                "bbox": json.loads(row["bbox"]),
                "frame_id": row["frame_id"]
            })
        conn.close()
        return history
    except Exception as e:
        print(f"[DB] Fetch error: {e}")
        return []

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "confidence_threshold": 0.4,
        "alert_mode": "Visual",
        "analysis_interval_ms": 1000,
        "hazard_classes": ["Fire", "Smoke", "Flood", "Falling Debris", "Landslide", "Explosion", "Collapsed Structure", "Industrial Accident"]
    }

def save_config(config: Dict):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except:
        return False

def add_gsm_number(mode: str, number: str, name: str, message: str = "", category: str = "general"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO gsm_contacts (mode, number, name, message, category) VALUES (?, ?, ?, ?, ?)",
            (mode, number, name, message, category)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] GSM contact add error: {e}")

def delete_gsm_number(number: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gsm_contacts WHERE number = ?", (number,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] GSM contact delete error: {e}")

def get_gsm_contacts():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gsm_contacts")
        rows = cursor.fetchall()
        contacts = {"sms": [], "call": []}
        for row in rows:
            contacts[row["mode"]].append({
                "number": row["number"],
                "name": row["name"],
                "message": row["message"],
                "category": row["category"] if "category" in row.keys() else "general"
            })
        conn.close()
        return contacts
    except:
        return {"sms": [], "call": []}

def set_worker_classification(device_id: str, classification: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cluster_workers (device_id, classification) VALUES (?, ?)",
            (device_id, classification)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Cluster classification error: {e}")
