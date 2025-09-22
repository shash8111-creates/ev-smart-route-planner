# app.py
import streamlit as st
import requests
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from shapely.geometry import LineString
from urllib.parse import urlencode
from math import radians, cos, sin, asin, sqrt
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

st.set_page_config(layout="wide", page_title="EV Route Planner (AI)")

# ---------------------------
# Utility functions
# ---------------------------
def haversine(lat1, lon1, lat2, lon2):
    # returns km
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

def get_osrm_routes(lat1, lon1, lat2, lon2, alternatives=True):
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}
    if alternatives:
        params["alternatives"] = "true"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?{urlencode(params)}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        st.error("OSRM routing failed. Try again later.")
        return []
    data = r.json()
    routes = []
    for route in data.get("routes", []):
        geom = route["geometry"]["coordinates"]  # [lon, lat]
        distance_km = route["distance"] / 1000.0
        duration_h = route["duration"] / 3600.0
        routes.append({"geometry": geom, "distance_km": distance_km, "duration_h": duration_h})
    return routes

def geocode(place):
    try:
        geolocator = Nominatim(user_agent="ev-route-planner")
        location = geolocator.geocode(place)
        if location:
            return location.latitude, location.longitude
    except Exception:
        return None
    return None

# ---------------------------
# Train & cache AI model
# ---------------------------
@st.cache_resource
def load_model():
    # Dummy dataset (replace with real EV dataset if available)
    X = np.array([[10, 50], [20, 100], [30, 200], [40, 300]])
    y = np.array([2, 4, 7, 10])  # kWh
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model

model = load_model()

# ---------------------------
# UI
# ---------------------------
st.title("AI-Powered EV Route Planner")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Trip Inputs")
    start = st.text_input("Start location", "Bangalore, India")
    end = st.text_input("End location", "Mysore, India")
    distance = st.number_input("Approx Distance (km)", min_value=1.0, value=20.0)
    elevation = st.number_input("Approx Elevation gain (m)", min_value=0.0, value=100.0)
    vehicle = st.selectbox("Vehicle type", ["Tesla Model 3", "Tata Nexon EV", "MG ZS EV"])
    weather = st.selectbox("Weather", ["Normal", "Cold", "Hot"])
    driving_style = st.selectbox("Driving Style", ["Eco", "Normal", "Sport"])
    run_btn = st.button("Find Best Route")

with col2:
    st.subheader("Map & Results")
    map_placeholder = st.empty()
    details_placeholder = st.empty()

# ---------------------------
# Main Flow
# ---------------------------
if run_btn:
    s = geocode(start)
    e = geocode(end)
    if not s or not e:
        st.error("Failed to geocode start or end location.")
        st.stop()

    s_lat, s_lon = s
    e_lat, e_lon = e

    routes = get_osrm_routes(s_lat, s_lon, e_lat, e_lon)
    if not routes:
        st.error("No routes found.")
        st.stop()

    # Predict energy usage
    base_pred = float(model.predict([[distance, elevation]])[0])

    # Adjust for weather
    if weather == "Cold":
        base_pred *= 1.15
    elif weather == "Hot":
        base_pred *= 1.05

    # Adjust for driving style
    if driving_style == "Eco":
        base_pred *= 0.9
    elif driving_style == "Sport":
        base_pred *= 1.2

    # Battery % estimation
    battery_kwh = 40.0
    used_percent = (base_pred / battery_kwh) * 100

    # Map
    m = folium.Map(location=[(s_lat + e_lat) / 2, (s_lon + e_lon) / 2], zoom_start=8)
    folium.Marker([s_lat, s_lon], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([e_lat, e_lon], tooltip="End", icon=folium.Icon(color="red")).add_to(m)

    for idx, r in enumerate(routes):
        coords = [(pt[1], pt[0]) for pt in r["geometry"]]
        folium.PolyLine(coords, color="blue", weight=4, opacity=0.7,
                        tooltip=f"Route {idx+1}: {r['distance_km']:.1f} km").add_to(m)

    st_folium(m, width=900, height=600)

    details_placeholder.markdown(f"""
    ### Results
    - Vehicle: **{vehicle}**
    - Weather: **{weather}**
    - Driving Style: **{driving_style}**
    - Distance: **{distance:.1f} km**
    - Elevation Gain: **{elevation:.1f} m**
    - Predicted Energy: **{base_pred:.2f} kWh**
    - Battery % Used: **{used_percent:.1f}%**
    """)

    if used_percent > 80:
        st.warning("Trip may require charging stop(s).")
    else:
        st.success("Trip can be completed without charging.")
