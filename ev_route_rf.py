# ev_route_rf.py
import streamlit as st
from auth_ui import render_login_page, render_main_app
from trip_manager import TripManager

# ============= SESSION STATE INITIALIZATION =============
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.route_data = {}
    st.session_state.chargers = []
    st.session_state.energy_pred = 0
    st.session_state.soc = 100

# ============= MAIN APP ENTRY POINT =============
if st.session_state.logged_in:
    # User is authenticated - render main app
    render_main_app()
else:
    # User not authenticated - render login page
    render_login_page()
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

st.set_page_config(page_title="⚡ EV Smart Route Planner", layout="wide")
st.title("⚡ EV Smart Route Planner")
st.write("Plan your EV journey with estimated energy, SOC, and charging stations along the route.")

# ----------------------------
# Vehicle presets (for SOC calculation)
# ----------------------------
vehicles_info = {
    "Tata Nexon EV": {"usable_kwh": 30},
    "MG ZS EV": {"usable_kwh": 44},
    "Hyundai Kona EV": {"usable_kwh": 39},
    "Mahindra eVerito": {"usable_kwh": 21},
}
drive_modes = ["Eco", "Normal", "Sport"]

# ----------------------------
# Session State Initialization
# ----------------------------
for key in ["route_data", "energy_pred", "start_coords", "end_coords", "chargers", "soc"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ----------------------------
# User Inputs
# ----------------------------
st.header("🔢 Enter Trip Details")
start = st.text_input("Start Location", "Bangalore, India")
end = st.text_input("Destination Location", "Mysore, India")
vehicle_choice = st.selectbox("Select Vehicle", list(vehicles_info.keys()))
drive_mode_choice = st.selectbox("Drive Mode", drive_modes)
current_charge_pct = st.slider("Current Battery Charge (%)", 0, 100, 100)

# ----------------------------
# Clear session state if inputs change
# ----------------------------
if ("prev_start" in st.session_state and st.session_state.prev_start != start) or \
   ("prev_end" in st.session_state and st.session_state.prev_end != end) or \
   ("prev_vehicle" in st.session_state and st.session_state.prev_vehicle != vehicle_choice) or \
   ("prev_drive" in st.session_state and st.session_state.prev_drive != drive_mode_choice):
    for key in ["route_data", "energy_pred", "start_coords", "end_coords", "chargers", "soc"]:
        st.session_state[key] = None

# Store current inputs to compare next time
st.session_state.prev_start = start
st.session_state.prev_end = end
st.session_state.prev_vehicle = vehicle_choice
st.session_state.prev_drive = drive_mode_choice

# ----------------------------
# Train or Load Random Forest
# ----------------------------
@st.cache_resource
def load_or_train_model():
    MODEL_FILE = "rf_ev_model.pkl"
    FEATURE_FILE = "rf_feature_order.pkl"

    if os.path.exists(MODEL_FILE) and os.path.exists(FEATURE_FILE):
        rf_model = joblib.load(MODEL_FILE)
        feature_order = joblib.load(FEATURE_FILE)
        return rf_model, feature_order

    st.warning("⚠️ Training new Random Forest model...")

    df = pd.read_csv("ev_energy_dataset_full_updated.csv")  # dataset with drive_mode
    X = df.drop(columns=['energy_consumed'])
    y = df['energy_consumed']
    X = pd.get_dummies(X, columns=['vehicle_type','drive_mode'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    rf = RandomForestRegressor(n_estimators=200, random_state=42)
    rf.fit(X_train, y_train)

    joblib.dump(rf, MODEL_FILE)
    joblib.dump(list(X.columns), FEATURE_FILE)
    st.success("✅ Model trained and saved!")
    return rf, list(X.columns)

rf_model, feature_order = load_or_train_model()

# ----------------------------
# Helper Functions
# ----------------------------
def geocode(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json"}
    r = requests.get(url, params=params, headers={"User-Agent":"EV-Planner"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        st.error(f"Location not found: {place}")
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])

def osrm_route(start_coords, end_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
    params = {"overview": "full", "geometries": "geojson"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def find_chargers_osm(lat, lon, distance_km=30):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node["amenity"="charging_station"](around:{distance_km*1000},{lat},{lon});
    out;
    """
    r = requests.get(overpass_url, params={'data': query}, timeout=30)
    r.raise_for_status()
    data = r.json().get("elements", [])
    chargers = []
    for ch in data:
        chargers.append((ch.get("lat"), ch.get("lon"), ch.get("tags", {}).get("name","Charger")))
    return chargers

def predict_energy(distance_km, vehicle, drive_mode):
    df_input = pd.DataFrame([{
        "distance_km": distance_km,
        "vehicle_type": vehicle,
        "drive_mode": drive_mode
    }])
    df_input = pd.get_dummies(df_input, columns=['vehicle_type','drive_mode'])
    for col in feature_order:
        if col not in df_input.columns:
            df_input[col] = 0
    df_input = df_input[feature_order]
    return rf_model.predict(df_input)[0]

# ----------------------------
# Main Route Planning
# ----------------------------
if st.button("Plan Route") or st.session_state.route_data:
    if st.session_state.route_data is None:
        start_coords = geocode(start)
        end_coords = geocode(end)
        if start_coords and end_coords:
            route_data = osrm_route(start_coords, end_coords)
            route_distance = route_data["routes"][0]["distance"] / 1000
            energy_pred = predict_energy(route_distance, vehicle_choice, drive_mode_choice)

            # Save in session state
            st.session_state.route_data = route_data
            st.session_state.energy_pred = energy_pred
            st.session_state.start_coords = start_coords
            st.session_state.end_coords = end_coords
            st.session_state.chargers = find_chargers_osm(
                (start_coords[0]+end_coords[0])/2, (start_coords[1]+end_coords[1])/2
            )
            st.session_state.soc = max(0, current_charge_pct - (energy_pred/vehicles_info[vehicle_choice]["usable_kwh"]*100))

    # Display results
    route_distance = st.session_state.route_data["routes"][0]["distance"] / 1000
    st.subheader("📊 Trip Summary")
    st.write(f"Distance: **{route_distance:.1f} km**")
    st.write(f"Predicted Energy: **{st.session_state.energy_pred:.2f} kWh**")
    st.write(f"Estimated SOC Remaining: **{st.session_state.soc:.1f}%**")
    st.progress(st.session_state.soc/100)

    # Map
    m = folium.Map(location=[(st.session_state.start_coords[0]+st.session_state.end_coords[0])/2,
                             (st.session_state.start_coords[1]+st.session_state.end_coords[1])/2], zoom_start=8)
    folium.Marker(st.session_state.start_coords, popup="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(st.session_state.end_coords, popup="End", icon=folium.Icon(color="red")).add_to(m)
    route_points = [(lat, lon) for lon, lat in st.session_state.route_data["routes"][0]["geometry"]["coordinates"]]
    folium.PolyLine(route_points, color="blue", weight=4, opacity=0.8).add_to(m)

    for lat, lon, name in st.session_state.chargers:
        folium.Marker([lat, lon], popup=name, icon=folium.Icon(color="blue", icon="bolt")).add_to(m)

    st.subheader("🗺️ Route & Charging Stations")
    st_folium(m, width=800, height=500)


