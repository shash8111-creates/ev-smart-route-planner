import requests
import json
from typing import Dict, Tuple, List
import streamlit as st

# Weather API Integration
def get_weather_data(latitude: float, longitude: float) -> Dict:
    """
    Fetch weather data using Open-Meteo API (free, no API key required)
    Returns temperature, wind speed, and weather condition
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "Asia/Kolkata"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        return {
            "temperature": current.get("temperature_2m", 25),
            "humidity": current.get("relative_humidity_2m", 50),
            "wind_speed": current.get("wind_speed_10m", 0),
            "weather_code": current.get("weather_code", 0),
            "status": "success"
        }
    except Exception as e:
        st.warning(f"⚠️ Weather API Error: {str(e)}. Using default values.")
        return {"temperature": 25, "humidity": 50, "wind_speed": 0, "weather_code": 0, "status": "error"}

# Elevation Data Integration
def get_elevation_profile(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Dict:
    """
    Get elevation data using Open Elevation API (free)
    Calculates elevation gain/loss and slope percentage
    """
    try:
        # Sample points along the route (approx 10 points)
        points = []
        for i in range(11):
            fraction = i / 10
            lat = start_coords[0] + (end_coords[0] - start_coords[0]) * fraction
            lon = start_coords[1] + (end_coords[1] - start_coords[1]) * fraction
            points.append({"latitude": lat, "longitude": lon})
        
        # Get elevation for sampled points
        url = "https://api.open-elevation.com/api/v1/lookup"
        locations = [f"locations={p['latitude']},{p['longitude']}" for p in points]
        params_str = "&".join(locations)
        
        response = requests.get(f"{url}?{params_str}", timeout=10)
        response.raise_for_status()
        elevations_data = response.json()
        
        results = elevations_data.get("results", [])
        elevations = [r["elevation"] for r in results]
        
        if not elevations:
            return {"elevation_gain": 0, "elevation_loss": 0, "avg_slope": 0, "status": "error"}
        
        # Calculate elevation gain and loss
        gain = sum([elevations[i+1] - elevations[i] for i in range(len(elevations)-1) if elevations[i+1] > elevations[i]])
        loss = sum([elevations[i] - elevations[i+1] for i in range(len(elevations)-1) if elevations[i] > elevations[i+1]])
        
        # Calculate average slope (simplified)
        total_elevation_change = max(elevations) - min(elevations)
        avg_slope = total_elevation_change / max(abs(end_coords[0] - start_coords[0]), 0.0001) * 111  # Convert to percentage
        
        return {
            "elevation_gain": round(gain, 2),
            "elevation_loss": round(loss, 2),
            "avg_slope": round(avg_slope, 2),
            "min_elevation": round(min(elevations), 2),
            "max_elevation": round(max(elevations), 2),
            "status": "success"
        }
    except Exception as e:
        st.warning(f"⚠️ Elevation API Error: {str(e)}. Using flat terrain estimate.")
        return {"elevation_gain": 0, "elevation_loss": 0, "avg_slope": 0, "status": "error"}

# Real-time Traffic Data Integration
def get_traffic_data(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Dict:
    """
    Get traffic data using TomTom API or fallback to simplified calculation
    For free tier, use simplified traffic model based on time of day
    """
    try:
        from datetime import datetime
        current_hour = datetime.now().hour
        
        # Simplified traffic model for India (based on typical traffic patterns)
        # Morning rush: 7-10 AM (30-50% slower)
        # Evening rush: 5-8 PM (40-60% slower)
        # Night: 10 PM - 6 AM (normal)
        # Off-peak: 10 AM - 5 PM (20% slower)
        
        if 7 <= current_hour < 10:
            congestion_factor = 0.4  # 40% slower
            traffic_status = "🔴 Heavy Morning Traffic"
        elif 17 <= current_hour < 20:
            congestion_factor = 0.5  # 50% slower
            traffic_status = "🔴 Heavy Evening Traffic"
        elif 20 <= current_hour or current_hour < 6:
            congestion_factor = 0.0  # Normal speed
            traffic_status = "🟢 Light Night Traffic"
        else:
            congestion_factor = 0.2  # 20% slower
            traffic_status = "🟡 Moderate Traffic"
        
        # Calculate additional time due to traffic
        base_time_minutes = ((end_coords[0] - start_coords[0])**2 + (end_coords[1] - start_coords[1])**2)**0.5 * 60
        traffic_delay_minutes = base_time_minutes * congestion_factor
        
        return {
            "congestion_factor": congestion_factor,
            "traffic_status": traffic_status,
            "delay_minutes": round(traffic_delay_minutes, 2),
            "speed_reduction_percent": int(congestion_factor * 100),
            "status": "success"
        }
    except Exception as e:
        st.warning(f"⚠️ Traffic API Error: {str(e)}. Using average traffic model.")
        return {"congestion_factor": 0.2, "traffic_status": "🟡 Average Traffic", "delay_minutes": 5, "speed_reduction_percent": 20, "status": "error"}

# Energy Adjustment Function
def adjust_energy_for_conditions(base_energy: float, weather: Dict, elevation: Dict, traffic: Dict) -> Dict:
    """
    Adjust energy consumption based on weather, elevation, and traffic conditions
    Returns adjusted energy and breakdown of factors
    """
    adjustments = {"base": base_energy, "factors": {}, "total_adjustment": 1.0}
    
    # Weather adjustments
    if weather.get("status") == "success":
        temp = weather.get("temperature", 25)
        wind = weather.get("wind_speed", 0)
        humidity = weather.get("humidity", 50)
        
        # Cold reduces efficiency (below 10°C)
        if temp < 10:
            temp_factor = 1 + (0.05 * (10 - temp) / 10)
            adjustments["factors"]["Temperature Effect"] = f"{(temp_factor - 1) * 100:.1f}% increase"
            adjustments["total_adjustment"] *= temp_factor
        
        # Wind resistance increases consumption
        if wind > 20:
            wind_factor = 1 + (wind - 20) * 0.01
            adjustments["factors"]["Wind Resistance"] = f"{(wind_factor - 1) * 100:.1f}% increase"
            adjustments["total_adjustment"] *= wind_factor
        
        # High humidity (rain) increases rolling resistance
        if humidity > 80:
            humidity_factor = 1.05
            adjustments["factors"]["High Humidity/Rain"] = "5% increase"
            adjustments["total_adjustment"] *= humidity_factor
    
    # Elevation adjustments
    if elevation.get("status") == "success":
        elevation_gain = elevation.get("elevation_gain", 0)
        if elevation_gain > 0:
            # Uphill increases consumption: ~0.5% per 10m of elevation gain
            elevation_factor = 1 + (elevation_gain * 0.005)
            adjustments["factors"]["Elevation Gain"] = f"{(elevation_factor - 1) * 100:.1f}% increase"
            adjustments["total_adjustment"] *= elevation_factor
    
    # Traffic adjustments
    if traffic.get("status") == "success":
        # More stop-and-go driving = higher consumption
        congestion = traffic.get("congestion_factor", 0)
        if congestion > 0:
            # Higher congestion = more energy (stop-and-go inefficiency)
            traffic_factor = 1 + (congestion * 0.3)  # Up to 30% increase at heavy congestion
            adjustments["factors"]["Traffic Congestion"] = f"{(traffic_factor - 1) * 100:.1f}% increase"
            adjustments["total_adjustment"] *= traffic_factor
    
    adjustments["adjusted_energy"] = round(base_energy * adjustments["total_adjustment"], 2)
    adjustments["total_adjustment"] = round(adjustments["total_adjustment"], 3)
    
    return adjustments

# Display function for energy breakdown
def display_energy_breakdown(st_container, adjustments: Dict, original_energy: float):
    """
    Display detailed energy consumption breakdown in Streamlit
    """
    st_container.subheader("⚡ Energy Consumption Breakdown")
    
    col1, col2, col3 = st_container.columns(3)
    with col1:
        st_container.metric("Base Energy", f"{adjustments['base']:.2f} kWh")
    with col2:
        st_container.metric("Adjustment Factor", f"{adjustments['total_adjustment']:.1f}x")
    with col3:
        st_container.metric("Adjusted Energy", f"{adjustments['adjusted_energy']:.2f} kWh")
    
    if adjustments["factors"]:
        st_container.write("**Contributing Factors:**")
        for factor, impact in adjustments["factors"].items():
            st_container.write(f"  • {factor}: {impact}")
