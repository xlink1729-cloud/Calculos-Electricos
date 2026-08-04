from modules.ampacity import calculate_adjusted_ampacity
from modules.voltage_drop import calculate_voltage_drop
from utils.db_loader import get_ampacity_data

def recommend_minimum_conductor(
    material: str,
    temp_rating: str,
    ambient_temp: int,
    num_conductors: int,
    current_amps: float,
    length_meters: float,
    voltage_nominal: float,
    system_type: str = "Monofásico 1Ø (2 hilos)",
    power_factor: float = 0.90,
    max_voltage_drop_percent: float = 3.0
) -> dict:
    """
    Evalúa secuencialmente los calibres disponibles y selecciona el menor calibre
    que cumpla tanto con el criterio de ampacidad como con el de caída de voltaje.
    """
    ampacity_data = get_ampacity_data()
    
    if material not in ampacity_data:
        raise ValueError(f"Material {material} no reconocido.")
        
    available_awgs = list(ampacity_data[material].keys())
    
    evaluated_results = []
    recommended_awg = None
    
    for awg in available_awgs:
        # 1. Evaluar Ampacidad
        amp_res = calculate_adjusted_ampacity(
            material=material,
            awg=awg,
            temp_rating=temp_rating,
            ambient_temp=ambient_temp,
            num_conductors=num_conductors
        )
        
        # 2. Evaluar Caída de Voltaje
        vd_res = calculate_voltage_drop(
            material=material,
            awg=awg,
            current_amps=current_amps,
            length_meters=length_meters,
            voltage_nominal=voltage_nominal,
            system_type=system_type,
            power_factor=power_factor
        )
        
        passes_ampacity = amp_res["adjusted_ampacity"] >= current_amps
        passes_vd = vd_res["v_drop_percent"] <= max_voltage_drop_percent
        
        is_valid = passes_ampacity and passes_vd
        
        status_info = {
            "awg": awg,
            "ampacity_ok": passes_ampacity,
            "vd_ok": passes_vd,
            "is_valid": is_valid,
            "adjusted_ampacity": amp_res["adjusted_ampacity"],
            "v_drop_percent": vd_res["v_drop_percent"],
            "v_drop_volts": vd_res["v_drop_volts"]
        }
        
        evaluated_results.append(status_info)
        
        # Primer calibre que cumple ambos requisitos
        if is_valid and recommended_awg is None:
            recommended_awg = status_info
            
    return {
        "recommended": recommended_awg,
        "all_evaluations": evaluated_results
    }