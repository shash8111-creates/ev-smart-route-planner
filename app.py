# app.py
import streamlit as st
import requests
import numpy as np
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestRegressor

st.set_page_config(layout="wide", page_title="EV Energy-Efficient Route Planner (AI)")

# ---------------------------
# Train simple AI model
# ---------------------------
@st.cache_resource
def load_model():
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    # Dummy data (replace with real EV dataset later)
    X = np.array([[10, 50], [20, 100], [30, 200], [40, 300]])
    y = np.array([2, 4, 7, 10])  # kWh usage
    model.fit(X, y)
    return model

model = load_model()

# ---------------------------
# ORS Route Fetch
# ---------------------------
def fetch_route(start_coords, end_coords, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {"coordinates": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]}

    try:
        r = requests.post(url, headers=headers, json=body, timeout=15)

        if r.status_code != 200:
            st.error(f"ORS routing failed: {r.status_code} — {r.text}")
            return None

        data = r.json()
        coords = data["features"][0]["geometry"]["coordinates"]
        distance = data["features"][0]["properties"]["segments"][0]["distance"] / 1000.0
        duration = data["features"][0]["properties"]["segments"][0]["duration"] / 3600.0

        return {"geometry": coords, "distance_km": distance, "duration_h": duration}

    except Exception as e:
        st.error(f"Routing request failed: {e}")
        return None

# ---------------------------
# Elevation API (open-elevation)
# ---------------------------
def fetch_elevation_along(coords):
    step = max(1, len(coords) // 40)
    pts = coords[::step]
    locations = "|".join([f"{lat},{lon}" for lon, lat in pts])

    try:
        r = requests.get(f"https://api.open-elevation.com/api/v1/lookup?locations={locations}", timeout=15)
        data = r.json()
        elevations = [p["elevation"] for p in data["results"]]
        gain = 0.0
        for i in range(1, len(elevations)):
            diff = elevations[i] - elevations[i - 1]
            if diff > 0:
                gain += diff
        return gain
    except Exception:
        return 0.0

# ---------------------------
# Geocoding (Nominatim OSM)
# ---------------------------
def geocode(place):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "ev-route-planner"},
            timeout=10,
        )
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

with st.sidebar:
    # API Key comes from Streamlit Secrets
    api_key = st.secrets["ORS_API_KEY"]

    battery_kwh = st.number_input("Battery capacity (kWh)", value=40.0, min_value=10.0, step=1.0)
    soc_percent = st.slider("Starting State-of-Charge (%)", min_value=5, max_value=100, value=80)
    driving_style = st.selectbox("Driving style", ["eco", "normal", "sport"])

start = st.text_input("Start location", "Bangalore, India")
end = st.text_input("End location", "Mysore, India")

if st.button("Find Best Route"):
    with st.spinner("Geocoding locations..."):
        s = geocode(start)
        e = geocode(end)
        if s is None or e is None:
            st.error("❌ Failed to geocode start or end.")
            st.stop()
        s_lat, s_lon = s
        e_lat, e_lon = e

    with st.spinner("Fetching best route..."):
        route = fetch_route((s_lat, s_lon), (e_lat, e_lon), api_key)
        if route is None:
            st.stop()

    with st.spinner("Fetching elevation data..."):
        elev_gain = fetch_elevation_along(route["geometry"])

    # Predict energy
    distance = route["distance_km"]
    X = np.array([[distance, elev_gain]])
    pred_kwh = model.predict(X)[0]
    available_kwh = battery_kwh * (soc_percent / 100.0)
    battery_used_pct = (pred_kwh / battery_kwh) * 100

    # Map
    m = folium.Map(location=[(s_lat + e_lat) / 2, (s_lon + e_lon) / 2], zoom_start=8)
    folium.Marker(location=[s_lat, s_lon], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(location=[e_lat, e_lon], tooltip="End", icon=folium.Icon(color="red")).add_to(m)
    coords_latlon = [(lat, lon) for lon, lat in route["geometry"]]
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
