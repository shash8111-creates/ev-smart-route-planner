# ⚡ EV Smart AI Route Planner

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ev-smart-route-planner-jypwxfgqnggjiymffodb5y.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An intelligent route planning system for Electric Vehicles using Machine Learning to optimize energy consumption, predict State of Charge (SOC), and locate charging stations along your journey.

## 🎯 Project Overview

This EV Smart Route Planner helps electric vehicle owners plan efficient trips by:
- Predicting energy consumption using Random Forest ML model
- Calculating optimal routes with real-time SOC estimates
- Finding nearby charging stations along the route
- Supporting multiple drive modes (Eco, Normal, Sport)
- Providing interactive map visualization

**Live Demo:** [https://ev-smart-route-planner-jypwxfgqnggjiymffodb5y.streamlit.app/](https://ev-smart-route-planner-jypwxfgqnggjiymffodb5y.streamlit.app/)

---

## 🚀 Features

### Current Implementation (v1.0)
- ✅ **ML-Powered Energy Prediction**: Random Forest model trained on synthetic EV data
- ✅ **Route Calculation**: OSRM-based routing between any two locations
- ✅ **SOC Estimation**: Real-time State of Charge prediction
- ✅ **Charging Station Finder**: OpenStreetMap Overpass API integration
- ✅ **Vehicle Profiles**: Support for 4 Indian EV models (Tata Nexon EV, MG ZS EV, Hyundai Kona EV, Mahindra eVerito)
- ✅ **Drive Modes**: Eco, Normal, Sport driving optimization
- ✅ **Interactive Maps**: Folium-powered route visualization

### 🔮 Upcoming Features
- 🔄 Weather impact integration
- 🔄 Elevation-based energy calculation
- 🔄 Real-time traffic integration
- 🔄 Advanced ML models (XGBoost, LightGBM)
- 🔄 Live charging station availability
- 🔄 Multi-stop trip planning
- 🔄 User authentication and trip history

---

## 🛠️ Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|  
| **Frontend** | Streamlit | 1.30.0 |
| **ML Framework** | Scikit-learn | 1.3.0 |
| **Data Processing** | Pandas, NumPy | 2.1.0, 1.26.0 |
| **Mapping** | Folium | 0.14.0 |
| **Deployment** | Streamlit Cloud | - |

---

## 📦 Installation & Setup

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/shash8111-creates/ev-smart-route-planner.git
cd ev-smart-route-planner
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
streamlit run ev_route_rf.py
```

5. **Open in browser**: http://localhost:8501

---

## 🎮 Usage Guide

1. Enter Start Location (e.g., "Bangalore, India")
2. Enter Destination (e.g., "Mysore, India")
3. Select Vehicle from 4 EV models
4. Choose Drive Mode (Eco/Normal/Sport)
5. Set Current Battery %
6. Click "Plan Route"
7. View route, energy consumption, and charging stations

---

## 📁 Project Structure

```
ev-smart-route-planner/
├── ev_route_rf.py                      # Main Streamlit app
├── generate_dataset.py                 # Data generator
├── train_rf.py                         # Model training
├── requirements.txt                    # Dependencies
├── ev_energy_dataset_full_updated.csv  # Dataset
└── README.md                           # Documentation
```

---

## 🗺️ Roadmap

### Phase 1: Core Enhancements
- [ ] Weather API integration
- [ ] Elevation profile analysis
- [ ] Traffic data integration

### Phase 2: Advanced Features
- [ ] User authentication
- [ ] Trip history & analytics
- [ ] Multi-stop planning
- [ ] Cost optimization

### Phase 3: Production Ready
- [ ] Mobile responsiveness
- [ ] API development
- [ ] Database integration
- [ ] CI/CD pipeline

---

## 👨‍💻 Author

**Shashank**
- GitHub: [@shash8111-creates](https://github.com/shash8111-creates)
- Email: 1AH22CS154@acsce.edu.in

---

## 📝 License

This project is licensed under the MIT License.

---

**⭐ If you find this project useful, please consider giving it a star!**
