#app.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from geopy.geocoders import Nominatim
import requests

# -------------------------------
# Train & cache AI model
# -------------------------------
@st.cache_resource
def load_model():
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    # Dummy training data (replace with real EV dataset later)
    X = np.array([[10, 50], [20, 100], [30, 200], [40, 300]])
    y = np.array([2, 4, 7, 10])  # kWh usage
    model.fit(X, y)
    return model

model = load_model()

# -------------------------------
# Geocoding helper
# -------------------------------
def geocode_location(place_name):
    geolocator = Nominatim(user_agent="ev_route_planner")
    location = geolocator.geocode(place_name)
    if location:
        return (location.latitude, location.longitude)
    else:
        return None

# -------------------------------
# ORS Routing helper
# -------------------------------
def fetch_route(start_coords, end_coords, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {
        "coordinates": [
            [start_coords[1], start_coords[0]],  # ORS needs [lon, lat]
            [end_coords[1], end_coords[0]]
        ]
    }
    response = requests.post(url, json=body, headers=headers)
    if response.status_code == 200:
        data = response.json()
        coords = data["features"][0]["geometry"]["coordinates"]
        # Convert [lon, lat] → (lat, lon) for folium
        return [(lat, lon) for lon, lat in coords]
    else:
        return None

# -------------------------------
# Streamlit App
# -------------------------------
st.title("⚡ AI-Powered EV Route Planner")

if "results" not in st.session_state:
    st.session_state.results = None

start = st.text_input("Enter start location")
end = st.text_input("Enter destination")
distance = st.number_input("Distance (km)", min_value=1.0, value=20.0)
elevation = st.number_input("Elevation gain (m)", min_value=0.0, value=100.0)
api_key = st.text_input("Enter your OpenRouteService API Key", type="password")

if st.button("Find Best Route"):
    start_coords = geocode_location(start)
    end_coords = geocode_location(end)

    if not start_coords or not end_coords:
        st.error("❌ Failed to geocode start or end location. Please check spelling.")
    elif not api_key:
        st.error("❌ Please enter your OpenRouteService API key.")
    else:
        # Fetch real driving route
        route = fetch_route(start_coords, end_coords, api_key)

        if not route:
            st.error("❌ Failed to fetch route from ORS API.")
        else:
            # Predict energy
            energy_used = model.predict([[distance, elevation]])[0]

            # Store results
            st.session_state.results = {
                "start": start,
                "end": end,
                "distance": distance,
                "elevation": elevation,
                "energy": energy_used,
                "start_coords": start_coords,
                "end_coords": end_coords,
                "route": route,
            }

# -------------------------------
# Show results if available
# -------------------------------
if st.session_state.results:
    res = st.session_state.results

    st.subheader("📊 Route Results")
    st.write(f"**Start:** {res['start']}")
    st.write(f"**End:** {res['end']}")
    st.write(f"**Distance (input):** {res['distance']} km")
    st.write(f"**Elevation gain (input):** {res['elevation']} m")
    st.write(f"🔋 **Predicted Energy Use:** {res['energy']:.2f} kWh")

    # Center map on route midpoint
    mid_lat = (res["start_coords"][0] + res["end_coords"][0]) / 2
    mid_lon = (res["start_coords"][1] + res["end_coords"][1]) / 2
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=7)

    # Add start/end markers
    folium.Marker(res["start_coords"], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(res["end_coords"], tooltip="End", icon=folium.Icon(color="red")).add_to(m)

    # Draw route if available
    if "route" in res and res["route"]:
        folium.PolyLine(res["route"], color="blue", weight=4).add_to(m)

    st_folium(m, width=700, height=500)
