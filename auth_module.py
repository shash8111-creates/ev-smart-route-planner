import sqlite3
import bcrypt
import hashlib
from datetime import datetime
from typing import Optional, Dict, Tuple
import streamlit as st

DB_FILE = "ev_route_planner.db"

class AuthManager:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                vehicle_type TEXT DEFAULT 'Tata Nexon EV',
                drive_mode TEXT DEFAULT 'Normal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Trip history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trip_history (
                trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_location TEXT,
                end_location TEXT,
                distance_km FLOAT,
                energy_consumed_kwh FLOAT,
                charging_cost FLOAT,
                duration_minutes INTEGER,
                drive_mode TEXT,
                soc_start FLOAT,
                soc_end FLOAT,
                route_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Charging history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS charging_history (
                charge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                station_name TEXT,
                location TEXT,
                kwh_charged FLOAT,
                charging_cost FLOAT,
                charging_time_minutes INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    @staticmethod
    def verify_password(password: str, hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode(), hash.encode())
    
    def register_user(self, username: str, email: str, password: str, full_name: str = "") -> Tuple[bool, str]:
        """Register new user"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            hashed_pwd = self.hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?)
            """, (username, email, hashed_pwd, full_name))
            
            conn.commit()
            conn.close()
            return True, "Registration successful!"
        
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Username already exists"
            elif "email" in str(e):
                return False, "Email already registered"
            return False, str(e)
    
    def login_user(self, username: str, password: str) -> Tuple[bool, Optional[int], str]:
        """Authenticate user and return user_id"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, password_hash, full_name FROM users WHERE username = ?
            """, (username,))
            
            result = cursor.fetchone()
            
            if result is None:
                return False, None, "Invalid username or password"
            
            user_id, pwd_hash, full_name = result
            
            if not self.verify_password(password, pwd_hash):
                return False, None, "Invalid username or password"
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            conn.close()
            
            return True, user_id, f"Welcome back, {full_name or username}!"
        
        except Exception as e:
            return False, None, f"Login error: {str(e)}"
    
    def get_user_profile(self, user_id: int) -> Dict:
        """Get user profile information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, email, full_name, vehicle_type, drive_mode, created_at, last_login
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'username': result[0],
                'email': result[1],
                'full_name': result[2],
                'vehicle_type': result[3],
                'drive_mode': result[4],
                'created_at': result[5],
                'last_login': result[6]
            }
        return {}
    
    def update_user_preferences(self, user_id: int, vehicle_type: str, drive_mode: str) -> bool:
        """Update user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET vehicle_type = ?, drive_mode = ? WHERE user_id = ?
        """, (vehicle_type, drive_mode, user_id))
        
        conn.commit()
        conn.close()
        return True
