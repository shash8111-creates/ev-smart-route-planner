def estimate_energy_kwh(distance_km, avg_speed_kmh, ascent_m, vehicle_mass_kg,
                        base_wh_per_km, hvac_on=True):
    """
    Estimate EV energy consumption in kWh with elevation and speed penalties.
    distance_km: total distance in km
    avg_speed_kmh: average speed in km/h
    ascent_m: total elevation gain in meters
    vehicle_mass_kg: mass of the vehicle
    base_wh_per_km: base energy consumption (Wh/km)
    hvac_on: whether HVAC is on
    """
    wh_per_km = base_wh_per_km

    # HVAC penalty
    if hvac_on:
        wh_per_km *= 1.1

    # Elevation penalty (energy to lift the car)
    wh_from_ascent = (vehicle_mass_kg * 9.81 * ascent_m) / 3.6e6 * 1000  # Wh
    extra_wh_per_km = wh_from_ascent / distance_km if distance_km > 0 else 0
    wh_per_km += extra_wh_per_km

    # Speed penalty
    if avg_speed_kmh > 90:
        wh_per_km *= 1.15

    total_wh = wh_per_km * distance_km
    total_kwh = total_wh / 1000.0

    return total_kwh
