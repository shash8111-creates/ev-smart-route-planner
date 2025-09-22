# app.py
import streamlit as st
import requests
import numpy as np
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestRegressor

st.set_page_config(layout="wide", page_title="EV Energy-Efficient Route Planner (AI)")

# ---------------------------
# Train simple energy model
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
# ORS routing
# ---------------------------
def fetch_route(start_coords, end_coords, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {"coordinates": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]}  # lon,lat order

    try:
        r = requests.post(url, headers=headers, json=body, timeout=15)
        data = r.json()

        if "features" not in data or len(data["features"]) == 0:
            st.error(f"Routing failed: {data.get('error', 'No route found')}")
            return None, None, None

        coords = data["features"][0]["geometry"]["coordinates"]
        distance_km = data["features"][0]["properties"]["segments"][0]["distance"] / 1000.0  # km
        duration_h = data["features"][0]["properties"]["segments"][0]["duration"] / 3600.0  # h

        return coords, distance_km, duration_h

    except Exception as e:
        st.error(f"Routing request failed: {e}")
        return None, None, None

# ---------------------------
# Elevation fetch (ORS API)
# ---------------------------
def fetch_elevation(coords, api_key):
    url = "https://api.openrouteservice.org/elevation/line"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {
        "format_in": "polyline",
        "format_out": "encodedpolyline",
        "geometry": coords
    }

    try:
        r = requests.post(url, headers=headers, json=body, timeout=15)
        data = r.json()

        if "geometry" not in data:
            st.error(f"Elevation fetch failed: {data}")
            return 0.0

        # ORS encodes (lon, lat, ele)
        decoded = data["geometry"]
        elevation_gain = 0.0
        last_ele = None
        for pt in decoded:
            if len(pt) == 3:
                ele = pt[2]
                if last_ele is not None and ele > last_ele:
                    elevation_gain += ele - last_ele
                last_ele = ele
        return elevation_gain
    except Exception as e:
        st.error(f"Elevation request failed: {e}")
        return 0.0

# ---------------------------
# UI
# ---------------------------
st.title("⚡ EV Energy-Efficient Route Planner — AI-powered")

with st.sidebar:
    api_key = st.text_input("Enter your ORS API Key", type="password")
    battery_kwh = st.number_input("Battery capacity (kWh)", value=40.0, min_value=10.0, step=1.0)
    soc_percent = st.slider("Starting State-of-Charge (%)", min_value=5, max_value=100, value=80)
    driving_style = st.selectbox("Driving style", ["eco", "normal", "sport"])

start = st.text_input("Start location", "Bangalore, India")
end = st.text_input("End location", "Mysore, India")

if st.button("Find Best Route"):
    if not api_key:
        st.error("Please enter your ORS API key in the sidebar.")
        st.stop()

    # ---------------------------
    # Geocode start & end
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

    with st.spinner("Fetching elevation data..."):
        elev_gain = fetch_elevation(coords, api_key)

    # ---------------------------
    # Predict energy
    # ---------------------------
    X = np.array([[distance, elev_gain]])
    pred_kwh = model.predict(X)[0]
    available_kwh = battery_kwh * (soc_percent/100.0)
    battery_used_pct = (pred_kwh / battery_kwh) * 100

    # ---------------------------
    # Map
    # ---------------------------
    m = folium.Map(location=[(s_lat+e_lat)/2, (s_lon+e_lon)/2], zoom_start=8)
    folium.Marker(location=[s_lat, s_lon], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(location=[e_lat, e_lon], tooltip="End", icon=folium.Icon(color="red")).add_to(m)
    coords_latlon = [(lat, lon) for lon, lat in coords]
    folium.PolyLine(coords_latlon, color="blue", weight=4).add_to(m)
    st_folium(m, width=900, height=600)

    # ---------------------------
    # Results
    # ---------------------------
    st.subheader("📊 Route Results")
    st.write(f"**Distance:** {distance:.2f} km")
    st.write(f"**Duration:** {duration:.2f} h")
    st.write(f"**Elevation gain:** {elev_gain:.1f} m")
    st.write(f"**Predicted Energy Use:** {pred_kwh:.2f} kWh")
    st.write(f"**Battery Available:** {available_kwh:.2f} kWh ({soc_percent}%)")
    st.write(f"🔋 **Battery % used:** {battery_used_pct:.1f}%")

    if pred_kwh > available_kwh:
        st.warning("⚠️ This trip requires a charging stop!")
    else:
        st.success("✅ You can complete this trip without charging.")
