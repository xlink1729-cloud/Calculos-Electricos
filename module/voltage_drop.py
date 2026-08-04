import math
from utils.db_loader import get_conductors_data

def calculate_voltage_drop(
    material: str,
    awg: str,
    current_amps: float,
    length_meters: float,
    voltage_nominal: float,
    system_type: str = "Monofásico 1Ø (2 hilos)",
    power_factor: float = 0.90
) -> dict:
    """
    Calcula la caída de voltaje (en Voltios y porcentaje) según NOM-001 / NEC Cap 9.
    
    system_type: 'Monofásico 1Ø (2 hilos)' o 'Trifásico 3Ø (3 o 4 hilos)'
    """
    conductors_data = get_conductors_data()
    
    if material not in conductors_data or awg not in conductors_data[material]:
        raise ValueError(f"Calibre {awg} o material {material} no encontrado en la base de datos.")
    
    cond_info = conductors_data[material][awg]
    
    # Resistencia y reactancia en ohm/km
    r_ohm_km = cond_info["resistance_pvc_ohm_km"]
    x_ohm_km = cond_info["reactance_pvc_ohm_km"]
    
    # Ángulo del factor de potencia
    cos_phi = power_factor
    sin_phi = math.sqrt(1 - cos_phi**2)
    
    # Impedancia eficaz (Z) en ohm/km
    z_ohm_km = (r_ohm_km * cos_phi) + (x_ohm_km * sin_phi)
    
    # Convertir longitud a kilómetros
    length_km = length_meters / 1000.0
    
    # Factor de fase (2 para monofásico, sqrt(3) para trifásico)
    phase_factor = 2.0 if "Monofásico" in system_type else math.sqrt(3)
    
    # Caída de voltaje en Volts
    v_drop = phase_factor * length_km * current_amps * z_ohm_km
    
    # Porcentaje de caída de voltaje
    v_drop_percent = (v_drop / voltage_nominal) * 100.0
    
    # Recomendación normativa: Max 3% en derivado, max 5% total alimentador+derivado
    status = "OK" if v_drop_percent <= 3.0 else ("Advertencia (> 3%)" if v_drop_percent <= 5.0 else "Crítico (> 5%)")
    
    return {
        "v_drop_volts": round(v_drop, 2),
        "v_drop_percent": round(v_drop_percent, 2),
        "v_final": round(voltage_nominal - v_drop, 2),
        "status": status,
        "impedance_z": round(z_ohm_km, 4)
    }