import math

def calculate_branch_circuits(area_m2: float, custom_appliances_va: float = 0.0) -> dict:
    """
    Calcula los circuitos derivados y la carga con Factor de Demanda
    para casa-habitación según NOM-001-SEDE / NEC (Art. 210 y 220).
    """
    # 1. Carga de alumbrado y contactos generales (33 VA/m² - Art. 220.12)
    lighting_load_va = area_m2 * 33.0
    
    # 2. Cargas fijas obligatorias (Art. 210.11(C))
    small_appliances_va = 2 * 1500.0  # 2 circuitos de 1,500 VA (Cocina)
    laundry_va = 1500.0              # 1 circuito de 1,500 VA (Lavandería)
    
    # Carga Conectada Total (General)
    general_connected_va = lighting_load_va + small_appliances_va + laundry_va
    
    # 3. Aplicación del Factor de Demanda (Tabla 220.42)
    if general_connected_va <= 3000.0:
        demanded_general_va = general_connected_va
    elif general_connected_va <= 120000.0:
        demanded_general_va = 3000.0 + ((general_connected_va - 3000.0) * 0.35)
    else:
        demanded_general_va = 3000.0 + (117000.0 * 0.35) + ((general_connected_va - 120000.0) * 0.25)

    # Carga total de diseño para el alimentador principal (demanda + cargas especiales 100%)
    total_demanded_va = demanded_general_va + custom_appliances_va
    
    # 4. Cantidad de circuitos derivados recomendados
    # Capacidad al 80% continuo para 15A a 120V = 1,440 VA
    va_per_15a_circuit = 120.0 * 15.0 * 0.8
    circuits_15a_lighting = math.ceil(lighting_load_va / va_per_15a_circuit)
    
    return {
        "area_m2": area_m2,
        "lighting_load_va": round(lighting_load_va, 2),
        "small_appliances_va": small_appliances_va,
        "laundry_va": laundry_va,
        "general_connected_va": round(general_connected_va, 2),
        "demanded_general_va": round(demanded_general_va, 2),
        "total_demanded_va": round(total_demanded_va, 2),
        "min_lighting_circuits_15a": max(1, circuits_15a_lighting),
        "small_appliance_circuits_20a": 2,
        "laundry_circuits_20a": 1,
        "total_min_circuits": max(1, circuits_15a_lighting) + 2 + 1
    }
