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
