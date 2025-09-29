import pandas as pd
import numpy as np

np.random.seed(42)
num_samples = 1000

# Vehicle types and base efficiency
vehicle_types = ['Tata Nexon EV', 'MG ZS EV', 'Hyundai Kona EV', 'Mahindra eVerito']
vehicle_efficiency = {'Tata Nexon EV': 0.2, 'MG ZS EV': 0.18, 'Hyundai Kona EV': 0.19, 'Mahindra eVerito': 0.17}

# Generate features
distance = np.random.uniform(0.5, 50, num_samples)        # km
speed = np.random.uniform(20, 120, num_samples)           # km/h
elevation = np.random.uniform(-50, 100, num_samples)      # meters
temperature = np.random.uniform(0, 40, num_samples)       # °C
traffic = np.random.randint(0, 3, num_samples)            # 0=Low,1=Medium,2=High
vehicle = np.random.choice(vehicle_types, num_samples)

# Energy consumption (synthetic)
energy = []
for i in range(num_samples):
    base = vehicle_efficiency[vehicle[i]] * distance[i]
    speed_factor = speed[i] * 0.01
    elevation_factor = elevation[i] * 0.005
    traffic_factor = traffic[i] * 0.3
    noise = np.random.normal(0, 0.5)
    energy.append(base + speed_factor + elevation_factor + traffic_factor + noise)

# Create DataFrame
df = pd.DataFrame({
    'distance': distance,
    'speed': speed,
    'elevation_change': elevation,
    'temperature': temperature,
    'traffic_level': traffic,
    'vehicle_type': vehicle,
    'energy_consumed': energy
})

# Save CSV
df.to_csv("ev_energy_dataset_full.csv", index=False)
print("Dataset created: ev_energy_dataset_full.csv")
