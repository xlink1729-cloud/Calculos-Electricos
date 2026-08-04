from modules.ampacity import calculate_adjusted_ampacity
from modules.voltage_drop import calculate_voltage_drop

def auto_select_circuit(load_amps: float, length_m: float, voltage: float, system_type: str, material: str = "cobre", temp_rating: str = "75C", is_continuous: bool = True) -> dict:
    """
    Dimensiona automáticamente el calibre AWG mínimo que cumple con Ampacidad y Caída de Voltaje (≤3%).
    """
    # 1. Aplicar factor de carga continua (125% según Art. 210.19 / 215.2)
    design_amps = load_amps * 1.25 if is_continuous else load_amps
    
    # Lista ordenada de calibres a evaluar
    awg_candidates = ["14", "12", "10", "8", "6", "4", "2", "1/0", "2/0", "3/0", "4/0"]
    
    # 2. Filtrar calibres mínimos por norma (14 AWG para Cobre, 12 AWG para Aluminio)
    if material == "aluminio" and "14" in awg_candidates:
        awg_candidates.remove("14")

    selected_awg = None
    final_amp_res = None
    final_vd_res = None
    
    # 3. Iterar hasta encontrar el calibre que cumpla con AMBAS condiciones
    for awg in awg_candidates:
        amp_res = calculate_adjusted_ampacity(material, awg, temp_rating, ambient_temp_c=30, num_conductors=3)
        
        # Condición A: ¿Soporta la corriente de diseño?
        if amp_res["adjusted_ampacity"] >= design_amps:
            vd_res = calculate_voltage_drop(material, awg, load_amps, length_m, voltage, system_type, power_factor=0.90)
            
            # Condición B: ¿La caída de voltaje es menor o igual al 3%?
            if vd_res["v_drop_percent"] <= 3.0:
                selected_awg = awg
                final_amp_res = amp_res
                final_vd_res = vd_res
                break  # Encontrado el calibre óptimo mínimo

    # 4. Seleccionar interruptor termomagnético comercial superior
    breaker_size = select_commercial_breaker(design_amps)

    return {
        "design_amps": round(design_amps, 2),
        "recommended_awg": selected_awg,
        "recommended_breaker": breaker_size,
        "ampacity_capacity": final_amp_res["adjusted_ampacity"] if final_amp_res else None,
        "v_drop_percent": final_vd_res["v_drop_percent"] if final_vd_res else None,
        "v_drop_volts": final_vd_res["v_drop_volts"] if final_vd_res else None,
    }

def select_commercial_breaker(amps: float) -> int:
    standard_breakers = [15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 225, 250, 300, 400]
    for b in standard_breakers:
        if b >= amps:
            return b
    return standard_breakers[-1]
