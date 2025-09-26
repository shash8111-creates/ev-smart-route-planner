def estimate_energy_kwh(distance_km, avg_speed_kmh, ascent_m, vehicle_mass_kg,
                        base_wh_per_km, hvac_on=True, reserve_frac=0.1):
    """Estimate EV energy consumption in kWh"""
    wh_per_km = base_wh_per_km

    # HVAC penalty
    if hvac_on:
        wh_per_km *= 1.1

    # Elevation penalty
    wh_from_ascent = (vehicle_mass_kg * 9.81 * ascent_m) / 3.6e6 * 1000
    extra_wh_per_km = wh_from_ascent / distance_km if distance_km > 0 else 0
    wh_per_km += extra_wh_per_km

    # Speed penalty
    if avg_speed_kmh > 90:
        wh_per_km *= 1.15

    total_wh = wh_per_km * distance_km
    total_kwh = total_wh / 1000.0
    total_kwh *= (1 + reserve_frac)

    return total_kwh
