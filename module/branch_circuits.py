import math

def calculate_branch_circuits(area_m2: float, custom_appliances_va: float = 0.0) -> dict:
    """
    Calcula los circuitos derivados requeridos para una casa-habitación 
    según la NOM-001-SEDE / NEC Art. 210 y 220.
    """
    # 1. Carga de alumbrado y contactos generales (33 VA/m² Art. 220.12)
    lighting_load_va = area_m2 * 33.0
    
    # 2. Cargas fijas obligatorias (Art. 210.11(C))
    small_appliances_va = 2 * 1500.0  # Mínimo 2 circuitos de 1500 VA (Cocina/Comedor)
    laundry_va = 1500.0              # Mínimo 1 circuito de 1500 VA (Lavandería)
    
    total_general_va = lighting_load_va + small_appliances_va + laundry_va + custom_appliances_va
    
    # 3. Cantidad de circuitos derivados recomendados (Capacidad de 15A a 120V = 1800 VA | 20A a 120V = 2400 VA)
    # Por norma, cargas continuas se calculan al 80% de capacidad del circuito (15A * 120V * 0.8 = 1440 VA)
    va_per_15a_circuit = 120.0 * 15.0 * 0.8  # 1,440 VA
    va_per_20a_circuit = 120.0 * 20.0 * 0.8  # 1,920 VA
    
    circuits_15a_lighting = math.ceil(lighting_load_va / va_per_15a_circuit)
    
    return {
        "area_m2": area_m2,
        "lighting_load_va": round(lighting_load_va, 2),
        "small_appliances_va": small_appliances_va,
        "laundry_va": laundry_va,
        "total_general_va": round(total_general_va, 2),
        "min_lighting_circuits_15a": max(1, circuits_15a_lighting),
        "small_appliance_circuits_20a": 2,
        "laundry_circuits_20a": 1,
        "total_min_circuits": max(1, circuits_15a_lighting) + 2 + 1
    }
