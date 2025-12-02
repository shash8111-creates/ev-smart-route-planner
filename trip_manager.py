import sqlite3
from datetime import datetime
from typing import List, Dict

class TripManager:
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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trip_history WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (user_id, limit))
        
        trips = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trips
    
    def get_trip_statistics(self, user_id: int) -> Dict:
        """Calculate trip statistics for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trips,
                SUM(distance_km) as total_distance,
                SUM(energy_consumed_kwh) as total_energy,
                SUM(charging_cost) as total_cost,
                AVG(energy_consumed_kwh/distance_km) as avg_consumption
            FROM trip_history WHERE user_id = ?
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

#========================================
4. STREAMLIT UI - auth_ui.py


import streamlit as st
from auth_module import AuthManager
from trip_manager import TripManager

def render_login_page():
    """Render login page"""
    st.set_page_config(page_title="EV Route Planner", layout="centered")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("⚡ EV Smart Route Planner")
        st.subheader("User Login")
    
    auth = AuthManager()
    
    # Tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login to Your Account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("🔓 Login", use_container_width=True):
            if username and password:
                success, user_id, message = auth.login_user(username, password)
                if success:
                    st.success(message)
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter username and password")
    
    with tab2:
        st.subheader("Create New Account")
        new_username = st.text_input("Choose Username", key="reg_username")
        new_email = st.text_input("Email Address", key="reg_email")
        new_fullname = st.text_input("Full Name (optional)", key="reg_fullname")
        new_password = st.text_input("Password (min 6 chars)", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("✍️ Register", use_container_width=True):
            if not all([new_username, new_email, new_password]):
                st.warning("Please fill all required fields")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                success, message = auth.register_user(
                    new_username, new_email, new_password, new_fullname
                )
                if success:
                    st.success(message)
                    st.info("You can now login with your credentials")
                else:
                    st.error(message)

def render_main_app():
    """Render main application after login"""
    st.set_page_config(page_title="EV Route Planner", layout="wide")
    
    # Sidebar
    with st.sidebar:
        st.title("⚡ EV Route Planner")
        st.write(f"Welcome, **{st.session_state.username}**!")
        
        page = st.radio(
            "Navigation",
            ["Route Planner", "Trip History", "Statistics", "Preferences", "Logout"]
        )
        
        if page == "Logout":
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    
    # Main content
    if page == "Route Planner":
        st.header("Plan Your Route")
        # Your existing route planning code here
        
    elif page == "Trip History":
        st.header("Your Trip History")
        trip_manager = TripManager()
        trips = trip_manager.get_user_trips(st.session_state.user_id)
        
        if trips:
            for trip in trips:
                with st.expander(f"{trip['start_location']} → {trip['end_location']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Distance", f"{trip['distance_km']:.2f} km")
                    col2.metric("Energy Used", f"{trip['energy_consumed_kwh']:.2f} kWh")
                    col3.metric("Cost", f"₹{trip['charging_cost']:.2f}")
        else:
            st.info("No trips recorded yet")
    
    elif page == "Statistics":
        st.header("Your Statistics")
        trip_manager = TripManager()
        stats = trip_manager.get_trip_statistics(st.session_state.user_id)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Trips", int(stats['total_trips']))
        col2.metric("Total Distance", f"{stats['total_distance_km']:.2f} km")
        col3.metric("Total Energy", f"{stats['total_energy_kwh']:.2f} kWh")
        col4.metric("Avg Consumption", f"{stats['avg_consumption_kwh_per_km']:.3f} kWh/km")
    
    elif page == "Preferences":
        st.header("User Preferences")
        auth = AuthManager()
        profile = auth.get_user_profile(st.session_state.user_id)
        
        with st.form("preferences_form"):
            vehicle = st.selectbox(
                "Preferred Vehicle",
                ["Tata Nexon EV", "MG ZS EV", "Hyundai Kona EV", "Mahindra eVerito"],
                index=0
            )
            mode = st.selectbox(
                "Default Drive Mode",
                ["Eco", "Normal", "Sport"]
            )
            
            if st.form_submit_button("Save Preferences"):
                auth.update_user_preferences(st.session_state.user_id, vehicle, mode)
                st.success("Preferences updated!")
