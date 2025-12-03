# ev_route_rf.py            

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

try:
    from auth_ui import render_login_page, render_main_app
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False

vehicles_info = {
    "Tata Nexon EV": {"usable_kwh": 30},
    "MG ZS EV": {"usable_kwh": 44},
    "Hyundai Kona EV": {"usable_kwh": 39},
    "Mahindra eVerito": {"usable_kwh": 21},
}
drive_modes = ["Eco", "Normal", "Sport"]

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None

if 'route_data' not in st.session_state:
    st.session_state.route_data = None
    st.session_state.start_coords = None
    st.session_state.end_coords = None
    st.session_state.chargers = []
    st.session_state.energy_pred = 0
    st.session_state.soc = 100

    # Authentication check
if HAS_AUTH and not st.session_state.logged_in:
    render_login_page()
    st.stop()

def geocode(place):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": place, "format": "json"}
        r = requests.get(url, params=params, headers={"User-Agent": "EV-Planner"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            st.error(f"❌ Location not found: {place}")
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        st.error(f"❌ Geocoding error: {str(e)}")
        return None

def osrm_route(start_coords, end_coords):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        params = {"overview": "full", "geometries": "geojson"}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Route error: {str(e)}")
        return None

def find_chargers_osm(lat, lon, distance_km=30):
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        node["amenity"="charging_station"](around:{distance_km*1000},{lat},{lon});
        out;
        """
        r = requests.get(overpass_url, params={'data': query}, timeout=15)
        r.raise_for_status()
        data = r.json().get("elements", [])
        chargers = []
        for ch in data:
            chargers.append((ch.get("lat"), ch.get("lon"), ch.get("tags", {}).get("name", "Charging Station")))
        return chargers
    except Exception as e:
        st.warning(f"⚠️ Could not fetch chargers: {str(e)}")
        return []

def predict_energy(distance_km, vehicle, drive_mode, rf_model, feature_order):
    try:
        df_input = pd.DataFrame([{
            "distance_km": distance_km,
            "vehicle_type": vehicle,
            "drive_mode": drive_mode
        }])
        df_input = pd.get_dummies(df_input, columns=['vehicle_type', 'drive_mode'])
        for col in feature_order:
            if col not in df_input.columns:
                df_input[col] = 0
        df_input = df_input[feature_order]
        return float(rf_model.predict(df_input)[0])
    except Exception as e:
        st.error(f"❌ Energy prediction error: {str(e)}")
        return 0

@st.cache_resource
def load_or_train_model():
    MODEL_FILE = "rf_ev_model.pkl"
    FEATURE_FILE = "rf_feature_order.pkl"
    
    try:
        if os.path.exists(MODEL_FILE) and os.path.exists(FEATURE_FILE):
            rf_model = joblib.load(MODEL_FILE)
            feature_order = joblib.load(FEATURE_FILE)
            return rf_model, feature_order
    except Exception as e:
        st.warning(f"Could not load cached model: {e}")

    try:
        with st.spinner("🔄 Training Random Forest model..."):
            df = pd.read_csv("ev_energy_dataset_full_updated.csv")
            X = df.drop(columns=['energy_consumed'])
            y = df['energy_consumed']
            X = pd.get_dummies(X, columns=['vehicle_type', 'drive_mode'])
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            rf = RandomForestRegressor(n_estimators=200, random_state=42)
            rf.fit(X_train, y_train)
            joblib.dump(rf, MODEL_FILE)
            joblib.dump(list(X.columns), FEATURE_FILE)
        return rf, list(X.columns)
    except FileNotFoundError:
        st.error("❌ Dataset file 'ev_energy_dataset_full_updated.csv' not found!")
        return None, None
    except Exception as e:
        st.error(f"❌ Error training model: {str(e)}")
        return None, None

st.title("⚡ EV Smart Route Planner")
st.write("Plan your EV journey with estimated energy, SOC, and charging stations.")

rf_model, feature_order = load_or_train_model()
if rf_model is None:
    st.stop()

st.header("🔢 Enter Trip Details")
col1, col2 = st.columns(2)
with col1:
    start = st.text_input("Start Location", "Bangalore, India")
with col2:
    end = st.text_input("Destination Location", "Mysore, India")

col3, col4, col5 = st.columns(3)
with col3:
    vehicle_choice = st.selectbox("Select Vehicle", list(vehicles_info.keys()))
with col4:
    drive_mode_choice = st.selectbox("Drive Mode", drive_modes)
with col5:
    current_charge_pct = st.slider("Current Battery Charge (%)", 0, 100, 100)

if st.button("🗺️ Plan Route", use_container_width=True):
    if not start or not end:
        st.error("❌ Please enter both start and end locations")
    else:
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        with status_placeholder.container():
            st.info("🌍 Geocoding start location...")
        start_coords = geocode(start)
        if not start_coords:
            st.stop()
        
        with status_placeholder.container():
            st.info("🌍 Geocoding end location...")
        end_coords = geocode(end)
        if not end_coords:
            st.stop()
        
        with status_placeholder.container():
            st.info("🗺️ Calculating route...")
        route_data = osrm_route(start_coords, end_coords)
        if not route_data:
            st.stop()
        
        with status_placeholder.container():
            st.info("🔌 Predicting energy consumption...")
        route_distance = route_data["routes"][0]["distance"] / 1000
        energy_pred = predict_energy(route_distance, vehicle_choice, drive_mode_choice, rf_model, feature_order)
        
        with status_placeholder.container():
            st.info("⚡ Finding charging stations...")
        chargers = find_chargers_osm(
            (start_coords[0] + end_coords[0]) / 2,
            (start_coords[1] + end_coords[1]) / 2
        )
        
        with status_placeholder.container():
            st.info("🏁 Computing state of charge...")
        soc = max(0, current_charge_pct - (energy_pred / vehicles_info[vehicle_choice]["usable_kwh"] * 100))
        
        st.session_state.route_data = route_data
        st.session_state.start_coords = start_coords
        st.session_state.end_coords = end_coords
        st.session_state.chargers = chargers
        st.session_state.energy_pred = energy_pred
        st.session_state.soc = soc
        
        with status_placeholder.container():
            st.success("✅ Route planned successfully!")

if st.session_state.route_data is not None:
    st.divider()
    route_distance = st.session_state.route_data["routes"][0]["distance"] / 1000
    
    st.subheader("📊 Trip Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Distance", f"{route_distance:.1f} km")
    with col2:
        st.metric("Energy Used", f"{st.session_state.energy_pred:.2f} kWh")
    with col3:
        st.metric("Remaining SOC", f"{st.session_state.soc:.1f}%")
    
    st.progress(max(0, min(st.session_state.soc / 100, 1.0)))
    
    st.subheader("🗺️ Route & Charging Stations")
    m = folium.Map(
        location=[
            (st.session_state.start_coords[0] + st.session_state.end_coords[0]) / 2,
            (st.session_state.start_coords[1] + st.session_state.end_coords[1]) / 2
        ],
        zoom_start=8
    )
    
    folium.Marker(
        st.session_state.start_coords,
        popup="Start",
        icon=folium.Icon(color="green")
    ).add_to(m)
    
    folium.Marker(
        st.session_state.end_coords,
        popup="End",
        icon=folium.Icon(color="red")
    ).add_to(m)
    
    route_points = [
        (lat, lon) for lon, lat in st.session_state.route_data["routes"][0]["geometry"]["coordinates"]
    ]
    folium.PolyLine(route_points, color="blue", weight=4, opacity=0.8).add_to(m)
    
    for lat, lon, name in st.session_state.chargers:
        folium.Marker(
            [lat, lon],
            popup=name,
            icon=folium.Icon(color="blue", icon="bolt", prefix="fa")
        ).add_to(m)
    
    st_folium(m, width=800, height=500)
    
    st.divider()
    if st.button("🔄 Plan Another Route", use_container_width=True):
        st.session_state.route_data = None
        st.session_state.start_coords = None
        st.session_state.end_coords = None
        st.session_state.chargers = []
        st.session_state.energy_pred = 0
        st.session_state.soc = 100

