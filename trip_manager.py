import sqlite3
from datetime import datetime
from typing import List, Dict


class TripManager:
    """Manages trip data storage and retrieval"""

    def __init__(self, db_path: str = "ev_route_planner.db"):
        self.db_path = db_path

    def save_trip(self, user_id: int, trip_data: Dict) -> bool:
        """Save trip to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO trip_history (
                    user_id, start_location, end_location, distance_km,
                    energy_consumed_kwh, charging_cost, duration_minutes,
                    drive_mode, soc_start, soc_end, route_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                trip_data.get('start_location'),
                trip_data.get('end_location'),
                trip_data.get('distance_km'),
                trip_data.get('energy_consumed_kwh'),
                trip_data.get('charging_cost'),
                trip_data.get('duration_minutes'),
                trip_data.get('drive_mode'),
                trip_data.get('soc_start'),
                trip_data.get('soc_end'),
                trip_data.get('route_type')
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving trip: {e}")
            return False

    def get_user_trips(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's trip history"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM trip_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            trips = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return trips
        except Exception as e:
            print(f"Error retrieving trips: {e}")
            return []

    def get_trip_statistics(self, user_id: int) -> Dict:
        """Calculate trip statistics for user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_trips,
                    SUM(distance_km) as total_distance,
                    SUM(energy_consumed_kwh) as total_energy,
                    SUM(charging_cost) as total_cost,
                    AVG(energy_consumed_kwh/distance_km) as avg_consumption
                FROM trip_history
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            conn.close()

            return {
                'total_trips': result[0] or 0,
                'total_distance_km': result[1] or 0,
                'total_energy_kwh': result[2] or 0,
                'total_cost': result[3] or 0,
                'avg_consumption_kwh_per_km': result[4] or 0
            }
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {
                'total_trips': 0,
                'total_distance_km': 0,
                'total_energy_kwh': 0,
                'total_cost': 0,
                'avg_consumption_kwh_per_km': 0
            }
