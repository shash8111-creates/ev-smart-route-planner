# ev_route_rf.py
import streamlit as st
import pandas as pd
import numpy as np
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

# ------------------------
# Load or Train Model
# ------------------------
@st.cache_resource
def load_or_train_model():
    MODEL_FILE = "rf_ev_model.pkl"
    FEATURE_FILE = "rf_feature_order.pkl"

    if os.path.exists(MODEL_FILE) and os.path.exists(FEATURE_FILE):
        rf_model = joblib.load(MODEL_FILE)
        feature_order = joblib.load(FEATURE_FILE)
        return rf_model, feature_order

    st.warning("⚠️ No model found, training a new Random Forest model...")

    df = pd.read_csv("ev_energy_dataset_full.csv")
    X = df.drop(columns=['energy_consumed'])
    y = df['energy_consumed']

    X = pd.get_dummies(X, columns=['vehicle_type'])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    rf = RandomForestRegressor(n_estimators=200, random_state=42)
    rf.fit(X_train, y_train)

    joblib.dump(rf, MODEL_FILE)
    joblib.dump(list(X.columns), FEATURE_FILE)

    st.success("✅ Model trained and saved successfully!")
    return rf, list(X.columns)


rf_model, feature_order = load_or_train_model()

# ------------------------
# User Inputs
# ------------------------
st.header("🔢 Enter Trip Details")

col1, col2 = st.columns(2)

with col1:
    distance = st.number_input("Trip Distance (km)", min_value=1, value=120)
    avg_speed = st.number_input("Average Speed (km/h)", min_value=10, value=60)

with col2:
    temperature = st.number_input("Outside Temperature (°C)", min_value=-10, value=25)
    soc_start = st.number_input("Starting SOC (%)", min_value=1, max_value=100, value=80)

vehicle_type = st.selectbox("Vehicle Type", ["sedan", "suv", "hatchback"])

start_lat = st.number_input("Start Latitude", value=12.9716, format="%.6f")
start_lon = st.number_input("Start Longitude", value=77.5946, format="%.6f")
end_lat = st.number_input("End Latitude", value=12.2958, format="%.6f")
end_lon = st.number_input("End Longitude", value=76.6394, format="%.6f")

# ------------------------
# Prediction + Map
# ------------------------
if st.button("🚗 Plan Route"):
    # Prepare input
    input_data = pd.DataFrame([{
        "distance_km": distance,
        "avg_speed": avg_speed,
        "temperature": temperature,
        "soc_start": soc_start,
        "vehicle_type": vehicle_type
    }])

    input_data = pd.get_dummies(input_data, columns=['vehicle_type'])
    for col in feature_order:
        if col not in input_data.columns:
            input_data[col] = 0
    input_data = input_data[feature_order]

    energy_pred = rf_model.predict(input_data)[0]
    soc_end = soc_start - (energy_pred / 50 * 100)  # ⚠️ assumes 50 kWh battery

    # --- Show results ---
    st.subheader("📊 Prediction Results")
    st.write(f"🔋 Estimated Energy Consumption: **{energy_pred:.2f} kWh**")
    st.write(f"⚡ Remaining SOC: **{max(soc_end, 0):.1f}%**")

    # --- Create Map ---
    st.subheader("🗺️ Route Map with Charging Stations")

    route_map = folium.Map(location=[(start_lat + end_lat) / 2,
                                     (start_lon + end_lon) / 2], zoom_start=8)

    # Add start & end
    folium.Marker([start_lat, start_lon], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker([end_lat, end_lon], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

    # Draw route line (straight line as placeholder)
    folium.PolyLine([(start_lat, start_lon), (end_lat, end_lon)],
                    color="blue", weight=4, opacity=0.7).add_to(route_map)

    # Add charging stations (every 50 km approx.)
    num_stations = distance // 50
    lat_step = (end_lat - start_lat) / (num_stations + 1)
    lon_step = (end_lon - start_lon) / (num_stations + 1)

    for i in range(1, int(num_stations) + 1):
        station_lat = start_lat + i * lat_step
        station_lon = start_lon + i * lon_step
        folium.Marker([station_lat, station_lon],
                      popup=f"Charging Station {i}",
                      icon=folium.Icon(color="blue", icon="bolt", prefix="fa")).add_to(route_map)

    st_folium(route_map, width=700, height=500)
