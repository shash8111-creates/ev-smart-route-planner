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

@st.cache_resource
def load_or_train_model():
    MODEL_FILE = "rf_ev_model.pkl"
    FEATURE_FILE = "rf_feature_order.pkl"

    if os.path.exists(MODEL_FILE) and os.path.exists(FEATURE_FILE):
        # ✅ Load saved model if already trained
        rf_model = joblib.load(MODEL_FILE)
        feature_order = joblib.load(FEATURE_FILE)
        return rf_model, feature_order

    # ⚡ Train new model if .pkl not found
    st.warning("⚠️ No model found, training a new Random Forest model...")

    # Load dataset from repo
    df = pd.read_csv("ev_energy_dataset_full.csv")

    X = df.drop(columns=['energy_consumed'])
    y = df['energy_consumed']

    # One-hot encode categorical features
    X = pd.get_dummies(X, columns=['vehicle_type'])

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train Random Forest
    rf = RandomForestRegressor(n_estimators=200, random_state=42)
    rf.fit(X_train, y_train)

    # Save model + feature order
    joblib.dump(rf, MODEL_FILE)
    joblib.dump(list(X.columns), FEATURE_FILE)

    st.success("✅ Model trained and saved successfully!")
    return rf, list(X.columns)

# ------------------------
# Load or train model
# ------------------------
rf_model, feature_order = load_or_train_model()
