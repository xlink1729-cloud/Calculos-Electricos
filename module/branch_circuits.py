import math
from module.ampacity import calculate_adjusted_ampacity
from module.voltage_drop import calculate_voltage_drop

def calculate_branch_circuits(
    area_m2: float = 0.0, 
    custom_appliances_va: float = 0.0, 
    is_existing_survey: bool = False,
    lighting_real_va: float = 0.0,
    voltage: float = 120.0,
    feeder_length_m: float = 10.0,
    custom_light_circuits: int = 1,
    custom_plug_circuits: int = 1,
    custom_dedicated_circuits: int = 0
) -> dict:
    """
    Calcula circuitos derivados, factor de demanda, alimentador principal CFE 
    y dimensiona el centro de cargas según NOM-001-SEDE / NEC.
    Soporta modo Obra Nueva y Levantamiento Real con distribución por confort.
    """
    if is_existing_survey:
        # MODO LEVANTAMIENTO REAL
        lighting_load_va = lighting_real_va
        small_appliances_va = 0.0
        laundry_va = 0.0
        general_connected_va = lighting_real_va
    else:
        # MODO PROYECTO / OBRA NUEVA (NOM-001)
        lighting_load_va = area_m2 * 33.0
        small_appliances_va = 2 * 1500.0  # 3,000 VA (Cocina)
        laundry_va = 1500.0              # 1,500 VA (Lavandería)
        general_connected_va = lighting_load_va + small_appliances_va + laundry_va

    total_connected_va = general_connected_va + custom_appliances_va

    # Factor de Demanda (Tabla 220.42) sobre Carga General
    if general_connected_va <= 3000.0:
        demanded_general_va = general_connected_va
    elif general_connected_va <= 120000.0:
        demanded_general_va = 3000.0 + ((general_connected_va - 3000.0) * 0.35)
    else:
        demanded_general_va = 3000.0 + (117000.0 * 0.35) + ((general_connected_va - 120000.0) * 0.25)

    total_demanded_va = demanded_general_va + custom_appliances_va

    # Cálculo de Corriente del Alimentador Principal (CFE -> Centro de Cargas)
    # Factor de potencia estimado de 0.90
    load_amps = total_demanded_va / (voltage * 0.90) if voltage > 0 else 0.0
    design_amps = load_amps * 1.25  # 125% Carga continua / factor de seguridad

    # Selección de Calibre de Alimentador y Verificación de Caída de Voltaje
    awg_candidates = ["12", "10", "8", "6", "4", "2", "1/0"]
    selected_awg = "8"
    feeder_vd_percent = 0.0

    for awg in awg_candidates:
        amp_res = calculate_adjusted_ampacity("cobre", awg, "75C", ambient_temp_c=30, num_conductors=3)
        if amp_res["adjusted_ampacity"] >= design_amps:
            vd_res = calculate_voltage_drop("cobre", awg, load_amps, feeder_length_m, voltage, "Monofásico 1Ø (2 hilos)")
            if vd_res["v_drop_percent"] <= 3.0:
                selected_awg = awg
                feeder_vd_percent = vd_res["v_drop_percent"]
                break

    # Interruptor Principal (Breaker) Comercial
    standard_breakers = [15, 20, 30, 40, 50, 60, 70, 80, 100]
    main_breaker = standard_breakers[-1]
    for b in standard_breakers:
        if b >= design_amps:
            main_breaker = b
            break

    # Conteo de Polos / Circuitos Derivados
    if is_existing_survey:
        # Distribución por Zonas / Confort definida por el usuario
        total_circuits = custom_light_circuits + custom_plug_circuits + custom_dedicated_circuits
        min_lighting_circuits = custom_light_circuits
    else:
        # Mínimo normativo automático para obra nueva
        va_per_15a_circuit = voltage * 15.0 * 0.8
        min_lighting_circuits = math.ceil(lighting_load_va / va_per_15a_circuit) if lighting_load_va > 0 else 1
        total_circuits = min_lighting_circuits + 2 + 1  # Alumbrado + 2 Cocina + 1 Lavandería

    return {
        "is_existing_survey": is_existing_survey,
        "lighting_load_va": round(lighting_load_va, 2),
        "small_appliances_va": round(small_appliances_va, 2),
        "laundry_va": round(laundry_va, 2),
        "general_connected_va": round(general_connected_va, 2),
        "custom_appliances_va": round(custom_appliances_va, 2),
        "total_connected_va": round(total_connected_va, 2),
        "demanded_general_va": round(demanded_general_va, 2),
        "total_demanded_va": round(total_demanded_va, 2),
        "load_amps": round(load_amps, 2),
        "design_amps": round(design_amps, 2),
        "recommended_feeder_awg": selected_awg,
        "main_breaker": main_breaker,
        "feeder_vd_percent": feeder_vd_percent,
        "lighting_circuits": min_lighting_circuits,
        "total_circuits": total_circuits,
        "custom_light_circuits": custom_light_circuits,
        "custom_plug_circuits": custom_plug_circuits,
        "custom_dedicated_circuits": custom_dedicated_circuits
    }
