import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd
import joblib

st.set_page_config(page_title="EV Smart Route Planner", layout="wide")
st.title("⚡ EV Smart Route Planner (Random Forest)")
st.write("Plan your EV journey with predicted energy and charging stations along the route.")

# --- Vehicle presets ---
vehicles = {
    "Tata Nexon EV": {"usable_kwh": 30},
    "MG ZS EV": {"usable_kwh": 44},
    "Hyundai Kona EV": {"usable_kwh": 39},
    "Mahindra eVerito": {"usable_kwh": 21},
}

vehicle_types = list(vehicles.keys())

# --- Drive mode efficiency factors ---
drive_factors = {"Eco": 0.9, "Normal": 1.0, "Sport": 1.1}

# --- Session state initialization ---
for key in ["route_data", "start_coords", "end_coords", "soc_remaining", "energy_kwh", "chargers"]:
    if key not in st.session_state:
        st.session_state[key] = None

# --- Inputs ---
start = st.text_input("Start location", "Bangalore, India")
end = st.text_input("Destination location", "Mysore, India")

vehicle_choice = st.selectbox("Select Vehicle", vehicle_types, index=0)
vehicle = vehicles[vehicle_choice]

drive_mode = st.radio("Drive Mode", ["Eco", "Normal", "Sport"], index=1)

current_charge_pct = st.number_input(
    "Current Battery Charge (%)", min_value=0, max_value=100, value=100, step=1
)
current_charge_kwh = vehicle["usable_kwh"] * (current_charge_pct / 100)

# --- Load Random Forest model and feature order ---
rf_model = joblib.load("rf_ev_model.pkl")
feature_order = joblib.load("rf_feature_order.pkl")  # ensures correct column order

# --- Helper functions ---
def geocode_nominatim(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json"}
    headers = {"User-Agent": "EV-Planner"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"Location not found: {place}")
    return [float(data[0]["lon"]), float(data[0]["lat"])]

def osrm_route(start_coords, end_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}"
    params = {"overview": "full", "geometries": "geojson"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def find_chargers_osm(lat, lon, distance_km=5):
    """Fetch EV chargers near a given point using Overpass API"""
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node
      ["amenity"="charging_station"]
      (around:{distance_km*1000},{lat},{lon});
    out;
    """
    r = requests.get(overpass_url, params={'data': query}, timeout=30)
    r.raise_for_status()
    data = r.json().get("elements", [])
    chargers = []
    for ch in data:
        chargers.append({
            "AddressInfo": {
                "Latitude": ch.get("lat"),
                "Longitude": ch.get("lon"),
                "Title": ch.get("tags", {}).get("name", "Charger")
            }
        })
    return chargers

def find_chargers_along_route(route_coords, distance_interval_km=10):
    """Find chargers along the route at intervals to improve coverage"""
    chargers = []
    # Sample route points every ~distance_interval_km
    num_points = max(2, len(route_coords) // distance_interval_km)
    sampled_points = route_coords[::max(1, len(route_coords)//num_points)]

    for lon, lat in sampled_points:
        try:
            chargers += find_chargers_osm(lat, lon, distance_km=5)
        except:
            pass

    # Remove duplicates
    unique_chargers = []
    seen = set()
    for ch in chargers:
        key = (ch['AddressInfo']['Latitude'], ch['AddressInfo']['Longitude'])
        if key not in seen:
            seen.add(key)
            unique_chargers.append(ch)
    return unique_chargers

# --- Main ---
if st.button("Plan Route") or st.session_state.route_data:
    try:
        if st.session_state.route_data is None:
            st.session_state.start_coords = geocode_nominatim(start)
            st.session_state.end_coords = geocode_nominatim(end)
            st.session_state.route_data = osrm_route(st.session_state.start_coords, st.session_state.end_coords)

        summary = st.session_state.route_data["routes"][0]
        coords = summary["geometry"]["coordinates"]
        distance_km = summary["distance"] / 1000
        duration_min = summary["duration"] / 60

        # --- Predict energy using Random Forest ---
        df_input = pd.DataFrame([{
            "distance": distance_km,
            "speed": 60 * drive_factors[drive_mode],
            "elevation_change": 0.0,
            "temperature": 25.0,
            "traffic_level": 1,
            "vehicle_type": vehicle_choice
        }])

        # One-hot encode vehicle_type
        df_encoded = pd.get_dummies(df_input, columns=['vehicle_type'])

        # Add missing columns and ensure correct order
        for col in feature_order:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
        df_encoded = df_encoded[feature_order]

        energy_pred = rf_model.predict(df_encoded)[0]
        st.session_state.energy_kwh = energy_pred

        soc_used = (energy_pred / current_charge_kwh) * 100
        st.session_state.soc_remaining = max(0, 100 - soc_used)

        # --- Find chargers along route if SOC is low ---
        st.session_state.chargers = []
        if st.session_state.soc_remaining < 20:
            route_points = [(lon, lat) for lon, lat in coords]
            st.session_state.chargers = find_chargers_along_route(route_points, distance_interval_km=10)

        # --- Trip Summary ---
        st.subheader("📊 Trip Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Vehicle", vehicle_choice)
        col2.metric("Distance", f"{distance_km:.1f} km")
        col3.metric("Duration", f"{duration_min:.1f} min")
        col4.metric("Predicted Energy", f"{energy_pred:.2f} kWh")
        col5.metric("Charging Stations", len(st.session_state.chargers))
        st.progress(min(1.0, st.session_state.soc_remaining / 100.0))

        # --- Map ---
        st.subheader("🗺️ Route & Charging Stations")
        m = folium.Map(
            location=[(st.session_state.start_coords[1] + st.session_state.end_coords[1]) / 2,
                      (st.session_state.start_coords[0] + st.session_state.end_coords[0]) / 2],
            zoom_start=8
        )

        folium.Marker([st.session_state.start_coords[1], st.session_state.start_coords[0]],
                      popup="Start", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker([st.session_state.end_coords[1], st.session_state.end_coords[0]],
                      popup="End", icon=folium.Icon(color="red")).add_to(m)

        route_points = [(lat, lon) for lon, lat in coords]
        folium.PolyLine(route_points, color="blue", weight=4, opacity=0.8).add_to(m)

        for ch in st.session_state.chargers:
            info = ch.get("AddressInfo", {})
            folium.Marker([info.get("Latitude"), info.get("Longitude")],
                          popup=info.get("Title", "Charger"),
                          icon=folium.Icon(color="blue", icon="bolt")).add_to(m)

        st_folium(m, width=800, height=600)

        if st.session_state.soc_remaining <= 0:
            st.error("⚠️ Trip not possible with current battery charge!")
        elif st.session_state.soc_remaining < 20 and st.session_state.chargers:
            st.warning(f"⚠️ Low SOC (~{st.session_state.soc_remaining:.1f}%). Charging stations displayed on map.")
        else:
            st.success(f"✅ You’ll arrive with ~{st.session_state.soc_remaining:.1f}% SOC remaining.")

    except Exception as e:
        st.error(f"Error: {e}")
