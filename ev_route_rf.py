import os
import pandas as pd
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib

st.set_page_config(page_title="EV Smart Route Planner", layout="wide")
st.title("⚡ EV Smart Route Planner")
st.write("Plan your EV journey with estimated energy, SOC, and charging stations along the route.")

# --- Vehicle presets ---
vehicles = {
    "Tata Nexon EV": {"mass": 1745, "usable_kwh": 30, "base_wh_per_km": 180},
    "MG ZS EV": {"mass": 1815, "usable_kwh": 44, "base_wh_per_km": 200},
    "Hyundai Kona EV": {"mass": 1680, "usable_kwh": 39, "base_wh_per_km": 190},
    "Mahindra eVerito": {"mass": 1490, "usable_kwh": 21, "base_wh_per_km": 170},
}

drive_factors = {"Eco": 0.9, "Normal": 1.0, "Sport": 1.1}

# --- Initialize session state ---
for key in ["route_data", "start_coords", "end_coords", "soc_remaining", "energy_kwh", "chargers"]:
    if key not in st.session_state:
        st.session_state[key] = None

# --- Inputs ---
start = st.text_input("Start location", "Bangalore, India")
end = st.text_input("Destination location", "Mysore, India")
vehicle_choice = st.selectbox("Select Vehicle", list(vehicles.keys()), index=0)
vehicle = vehicles[vehicle_choice]
drive_mode = st.radio("Drive Mode", ["Eco", "Normal", "Sport"], index=1)
current_charge_pct = st.number_input("Current Battery Charge (%)", min_value=0, max_value=100, value=100, step=1)
current_charge_kwh = vehicle["usable_kwh"] * (current_charge_pct / 100)

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

def get_elevation(coords, sample_every=20):
    sampled_coords = coords[::sample_every]
    locations = [{"latitude": lat, "longitude": lon} for lon, lat in sampled_coords]
    if not locations:
        return [0]
    url = "https://api.open-elevation.com/api/v1/lookup"
    r = requests.post(url, json={"locations": locations}, timeout=30)
    r.raise_for_status()
    results = r.json().get("results", [])
    elevations = [point.get("elevation", 0) for point in results]
    return elevations

def find_chargers_osm(lat, lon, distance_km=30):
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

def estimate_energy_kwh(distance_km, avg_speed_kmh, vehicle_mass_kg, base_wh_per_km, ascent_m):
    df_input = pd.DataFrame([{
        "distance": distance_km,
        "avg_speed": avg_speed_kmh,
        "vehicle_mass": vehicle_mass_kg,
        "base_wh_per_km": base_wh_per_km,
        "ascent_m": ascent_m
    }])
    return rf_model.predict(df_input)[0]

# --- Train RF model if missing ---
if not os.path.exists("rf_ev_model.pkl"):
    st.info("Training Random Forest model, please wait...")
    df = pd.read_csv("ev_energy_dataset_full.csv")
    X = df.drop(columns=['energy_consumed'])
    y = df['energy_consumed']
    X = pd.get_dummies(X, columns=['vehicle_type'])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    rf_model = RandomForestRegressor(n_estimators=200, random_state=42)
    rf_model.fit(X_train, y_train)
    joblib.dump(rf_model, "rf_ev_model.pkl")
    st.success("Random Forest model trained and saved.")
else:
    rf_model = joblib.load("rf_ev_model.pkl")

# --- Main route planning ---
if st.button("Plan Route") or st.session_state.route_data:
    try:
        if st.session_state.route_data is None:
            st.session_state.start_coords = geocode_nominatim(start)
            st.session_state.end_coords = geocode_nominatim(end)
            st.session_state.route_data = osrm_route(st.session_state.start_coords, st.session_state.end_coords)
            summary = st.session_state.route_data["routes"][0]
            distance_km = summary["distance"] / 1000
            duration_min = summary["duration"] / 60
            coords = summary["geometry"]["coordinates"]
            elevations = get_elevation(coords)
            ascent_m = max(0, max(elevations) - min(elevations))
            st.session_state.energy_kwh = estimate_energy_kwh(
                distance_km=distance_km,
                avg_speed_kmh=60 * drive_factors[drive_mode],
                vehicle_mass_kg=vehicle["mass"],
                base_wh_per_km=vehicle["base_wh_per_km"],
                ascent_m=ascent_m
            )
            soc_used = (st.session_state.energy_kwh / current_charge_kwh) * 100
            st.session_state.soc_remaining = max(0, 100 - soc_used)

            # Fetch chargers near midpoint if SOC is low
            st.session_state.chargers = []
            if st.session_state.soc_remaining < 20:
                mid_lat = (st.session_state.start_coords[1] + st.session_state.end_coords[1]) / 2
                mid_lon = (st.session_state.start_coords[0] + st.session_state.end_coords[0]) / 2
                st.session_state.chargers = find_chargers_osm(mid_lat, mid_lon)

        # --- Trip Summary ---
        st.subheader("📊 Trip Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Vehicle", vehicle_choice)
        col2.metric("Distance", f"{distance_km:.1f} km")
        col3.metric("Duration", f"{duration_min:.1f} min")
        col4.metric("Predicted Energy", f"{st.session_state.energy_kwh:.2f} kWh")
        col5.metric("Charging Stations", len(st.session_state.chargers))
        st.progress(min(1.0, st.session_state.soc_remaining / 100.0))

        # --- Map with chargers ---
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

        route_points = [(lat, lon) for lon, lat in st.session_state.route_data["routes"][0]["geometry"]["coordinates"]]
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
