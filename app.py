# app.py
import streamlit as st
import requests
import numpy as np
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestRegressor

st.set_page_config(layout="wide", page_title="EV Energy-Efficient Route Planner")

# ---------------------------
# Load AI energy model
# ---------------------------
@st.cache_resource
def load_model():
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    # Dummy training (replace with real EV dataset later)
    X = np.array([[10, 50], [20, 100], [30, 200], [40, 300]])
    y = np.array([2, 4, 7, 10])  # kWh usage
    model.fit(X, y)
    return model

model = load_model()

# ---------------------------
# ORS Routing
# ---------------------------
def fetch_route(start_coords, end_coords, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {"coordinates": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        if r.status_code != 200:
            st.error(f"ORS routing failed: {r.status_code} {r.text}")
            return None, None, None
        data = r.json()
        coords = data["features"][0]["geometry"]["coordinates"]
        distance = data["features"][0]["properties"]["segments"][0]["distance"] / 1000
        duration = data["features"][0]["properties"]["segments"][0]["duration"] / 3600
        return coords, distance, duration
    except Exception as e:
        st.error(f"Routing error: {e}")
        return None, None, None

# ---------------------------
# Elevation along route
# ---------------------------
def fetch_elevation(coords):
    step = max(1, len(coords)//40)
    pts = coords[::step]
    locations = "|".join([f"{lat},{lon}" for lon, lat in pts])
    try:
        r = requests.get(f"https://api.open-elevation.com/api/v1/lookup?locations={locations}", timeout=15)
        data = r.json()
        elevations = [p["elevation"] for p in data["results"]]
        gain = 0.0
        for i in range(1, len(elevations)):
            diff = elevations[i] - elevations[i-1]
            if diff > 0:
                gain += diff
        return gain
    except Exception:
        return 0.0

# ---------------------------
# Geocoding
# ---------------------------
def geocode(place):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": place, "format": "json", "limit": 1},
                         headers={"User-Agent": "ev-route-planner"}, timeout=10)
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None

# ---------------------------
# UI
# ---------------------------
st.title("⚡ EV Energy-Efficient Route Planner — AI-powered")

# ORS API key from secrets
api_key = st.secrets.get("ORS_API_KEY", "")
battery_kwh = st.sidebar.number_input("Battery capacity (kWh)", value=40.0, min_value=10.0)
soc_percent = st.sidebar.slider("Starting State-of-Charge (%)", 5, 100, 80)
driving_style = st.sidebar.selectbox("Driving style", ["eco", "normal", "sport"])

start = st.text_input("Start location", "Bangalore, India")
end = st.text_input("End location", "Mysore, India")

if st.button("Find Best Route"):
    if not api_key:
        st.error("Please add your ORS API key in Streamlit secrets!")
        st.stop()

    with st.spinner("Geocoding..."):
        s = geocode(start)
        e = geocode(end)
        if s is None or e is None:
            st.error("Failed to geocode start or end.")
            st.stop()
        s_lat, s_lon = s
        e_lat, e_lon = e

    with st.spinner("Fetching route..."):
        coords, distance, duration = fetch_route((s_lat, s_lon), (e_lat, e_lon), api_key)
        if coords is None:
            st.stop()

    with st.spinner("Fetching elevation..."):
        elev_gain = fetch_elevation(coords)

    # Predict energy
    X = np.array([[distance, elev_gain]])
    pred_kwh = model.predict(X)[0]
    available_kwh = battery_kwh * (soc_percent/100)
    battery_used_pct = (pred_kwh / battery_kwh) * 100

    # Map
    m = folium.Map(location=[(s_lat+e_lat)/2, (s_lon+e_lon)/2], zoom_start=8)
    folium.Marker([s_lat, s_lon], "Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([e_lat, e_lon], "End", icon=folium.Icon(color="red")).add_to(m)
    coords_latlon = [(lat, lon) for lon, lat in coords]
    folium.PolyLine(coords_latlon, color="blue", weight=4).add_to(m)
    st_folium(m, width=900, height=600)

    # Results
    st.subheader("📊 Route Results")
    st.write(f"**Distance:** {distance:.2f} km")
    st.write(f"**Elevation gain:** {elev_gain:.1f} m")
    st.write(f"**Predicted Energy Use:** {pred_kwh:.2f} kWh")
    st.write(f"**Battery Available:** {available_kwh:.2f} kWh ({soc_percent}%)")
    st.write(f"🔋 **Battery % used:** {battery_used_pct:.1f}%")

    if pred_kwh > available_kwh:
        st.warning("⚠️ This trip requires a charging stop!")
    else:
        st.success("✅ You can complete this trip without charging.")
