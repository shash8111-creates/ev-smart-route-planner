# train_rf.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib

# Load dataset
df = pd.read_csv("ev_energy_dataset_full.csv")  # or your CSV file

# Features and target
X = df.drop(columns=['energy_consumed'])
y = df['energy_consumed']

# One-hot encode vehicle_type
X = pd.get_dummies(X, columns=['vehicle_type'])

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train Random Forest
rf = RandomForestRegressor(n_estimators=200, random_state=42)
rf.fit(X_train, y_train)

# Save model
joblib.dump(rf, "rf_ev_model.pkl")
print("Random Forest model saved as rf_ev_model.pkl")

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib

# Load dataset
df = pd.read_csv("ev_energy_dataset_full.csv")  # or your CSV file

# Features and target
X = df.drop(columns=['energy_consumed'])
y = df['energy_consumed']

# One-hot encode vehicle_type
X = pd.get_dummies(X, columns=['vehicle_type'])

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train Random Forest
rf = RandomForestRegressor(n_estimators=200, random_state=42)
rf.fit(X_train, y_train)

# Save model
joblib.dump(rf, "rf_ev_model.pkl")
print("Random Forest model saved as rf_ev_model.pkl")

# Save feature order for Streamlit app
feature_order = X_train.columns.tolist()
joblib.dump(feature_order, "rf_feature_order.pkl")
print("Feature order saved as rf_feature_order.pkl")

