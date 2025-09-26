import streamlit as st
import requests
from energy import estimate_energy_kwh

st.set_page_config(page_title="EV Smart Route Planner", layout="wide")
st.title("⚡ EV Smart Route Planner with Charging Stops")

st.write("Plan your EV journey with estimated energy, SOC, and charging stations along the route.")

# --- Inputs ---
start = st.text_input("Start location", "Bangalore, India")
end = st.text_input("Destination location", "Mysore, India")

# Read ORS API key from Streamlit secrets
ors_api_key = st.secrets["ORS_API_KEY"]

usable_kwh = st.number_input("Battery usable capacity (kWh)", min_value=20.0, value=60.0, step=1.0)
vehicle_mass = st.slider("Vehicle mass (kg)", 1000, 3000, 1800, step=50)
base_wh_per_km = st.slider("Base efficiency (Wh/km)", 100, 250, 180, step=5)
avg_speed_kmh = st.number_input("Assumed Avg Speed (km/h)", min_value=10.0, value=80.0, step=1.0)
hvac_on = st.checkbox("HVAC On", value=True)
reserve_frac = st.slider("Reserve buffer (%)", 0, 30, 10, step=1) / 100.0

# --- Helper functions ---

def geocode(place, api_key):
    url = "https://api.openrouteservice.org/geocode/search"
    params = {"api_key": api_key, "text": place}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    coords = r.json()["features"][0]["geometry"]["coordinates"]  # [lon, lat]
    return coords

def route(start_coords, end_coords, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    body = {"coordinates": [start_coords, end_coords], "elevation": True}
    r = requests.post(url, json=body, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def find_chargers(lat, lon, distance_km=30, max_results=10):
    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json",
        "latitude": lat,
        "longitude": lon,
        "distance": distance_km,
        "distanceunit": "KM",
        "maxresults": max_results,
    }
    headers = {"X-API-Key": ""}  # Optional
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

# --- Main ---
if st.button("Plan Route"):
    try:
        start_coords = geocode(start, ors_api_key)
        end_coords = geocode(end, ors_api_key)

        # Show start and end on map
        map_data = [
            {"lat": start_coords[1], "lon": start_coords[0], "name": "Start"},
            {"lat": end_coords[1], "lon": end_coords[0], "name": "End"}
        ]

        route_data = route(start_coords, end_coords, ors_api_key)
        props = route_data["features"][0]["properties"]
        summary = props["summary"]

        distance_km = summary["distance"] / 1000
        duration_min = summary["duration"] / 60
        ascent = props.get("ascent", 0.0)

        energy_kwh = estimate_energy_kwh(
            distance_km,
            avg_speed_kmh,
            ascent,
            vehicle_mass,
            base_wh_per_km,
            hvac_on,
            reserve_frac
        )

        soc_used = (energy_kwh / usable_kwh) * 100
        soc_remaining = 100 - soc_used

        # --- Display Results ---
        st.subheader("📊 Trip Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Distance", f"{distance_km:.1f} km")
        col2.metric("Duration", f"{duration_min:.1f} min")
        col3.metric("Ascent", f"{ascent:.1f} m")
        col4.metric("Predicted Energy", f"{energy_kwh:.2f} kWh")
        st.progress(min(1.0, soc_remaining / 100.0))

        if soc_remaining < 0:
            st.error("⚠️ Trip not possible without charging!")
        elif soc_remaining < 20:
            st.warning(f"⚠️ Low SOC (~{soc_remaining:.1f}%). Searching for charging stations...")
            mid_lat = (start_coords[1] + end_coords[1]) / 2
            mid_lon = (start_coords[0] + end_coords[0]) / 2
            chargers = find_chargers(mid_lat, mid_lon)

            if chargers:
                st.subheader("🔋 Charging Stations Nearby")
                for ch in chargers:
                    title = ch.get("AddressInfo", {}).get("Title", "Unknown")
                    addr = ch.get("AddressInfo", {}).get("AddressLine1", "")
                    lat = ch.get("AddressInfo", {}).get("Latitude")
                    lon = ch.get("AddressInfo", {}).get("Longitude")
                    map_data.append({"lat": lat, "lon": lon, "name": title})
                    st.write(f"✅ {title} - {addr}")
            else:
                st.error("❌ No charging stations found nearby!")

        else:
            st.success(f"✅ You’ll arrive with ~{soc_remaining:.1f}% SOC remaining.")

        # --- Show map with chargers ---
        st.subheader("🗺️ Route & Charging Stations")
        st.map([{"lat": d["lat"], "lon": d["lon"]} for d in map_data])

    except Exception as e:
        st.error(f"Error: {e}")
