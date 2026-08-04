import math

def calculate_branch_circuits(
    area_m2: float = 0.0, 
    custom_appliances_va: float = 0.0, 
    is_existing_survey: bool = False,
    lighting_real_va: float = 0.0
) -> dict:
    """
    Calcula circuitos derivados y factor de demanda (NOM-001 / NEC).
    Soporta modo Obra Nueva (por superficie/mínimos) y Levantamiento Real.
    """
    if is_existing_survey:
        # MODO LEVANTAMIENTO / CARGA REAL EXISTENTE
        lighting_load_va = lighting_real_va
        small_appliances_va = 0.0
        laundry_va = 0.0
        general_connected_va = lighting_real_va
    else:
        # MODO PROYECTO / OBRA NUEVA (NOM-001 STANDARD)
        lighting_load_va = area_m2 * 33.0
        small_appliances_va = 2 * 1500.0  # 3,000 VA
        laundry_va = 1500.0              # 1,500 VA
        general_connected_va = lighting_load_va + small_appliances_va + laundry_va

    # Carga total conectada (General + Específicas)
    total_connected_va = general_connected_va + custom_appliances_va

    # Aplicación del Factor de Demanda (Tabla 220.42) sobre la Carga General
    if general_connected_va <= 3000.0:
        demanded_general_va = general_connected_va
    elif general_connected_va <= 120000.0:
        demanded_general_va = 3000.0 + ((general_connected_va - 3000.0) * 0.35)
    else:
        demanded_general_va = 3000.0 + (117000.0 * 0.35) + ((general_connected_va - 120000.0) * 0.25)

    # Carga total con factor de demanda para la acometida
    total_demanded_va = demanded_general_va + custom_appliances_va

    # Estimación de circuitos mínimos de alumbrado (15A @ 120V)
    va_per_15a_circuit = 120.0 * 15.0 * 0.8  # 1,440 VA por circuito al 80%
    min_lighting_circuits = math.ceil(lighting_load_va / va_per_15a_circuit) if lighting_load_va > 0 else 1

    return {
        "is_existing_survey": is_existing_survey,
        "lighting_load_va": round(lighting_load_va, 2),
        "small_appliances_va": small_appliances_va,
        "laundry_va": laundry_va,
        "general_connected_va": round(general_connected_va, 2),
        "custom_appliances_va": round(custom_appliances_va, 2),
        "total_connected_va": round(total_connected_va, 2),
        "demanded_general_va": round(demanded_general_va, 2),
        "total_demanded_va": round(total_demanded_va, 2),
        "min_lighting_circuits_15a": min_lighting_circuits,
    }
