from utils.db_loader import get_motors_data

def calculate_motor_circuit(hp: str, voltage: str, pf: float = 0.85, eff: float = 0.90) -> dict:
    motors_data = get_motors_data()
    
    # 1. Obtener FLC de tabla normativa
    flc = float(motors_data["three_phase"][voltage][str(hp)])
    
    # 2. Corriente de diseño para el conductor (125% FLC - Art. 430.22)
    conductor_ampacity_req = flc * 1.25
    
    # 3. Protección contra cortocircuito / termomagnético (250% FLC max - Art. 430.52)
    breaker_max = flc * 2.50
    # Seleccionar interruptor comercial estándar inmediato inferior o superior según regla
    breaker_commercial = select_commercial_breaker(breaker_max)
    
    # 4. Protección contra sobrecarga / Relevador térmico (115% - 125% FLC)
    overload_min = flc * 1.15
    overload_max = flc * 1.25
    
    return {
        "flc": flc,
        "conductor_min_ampacity": round(conductor_ampacity_req, 2),
        "breaker_max_calc": round(breaker_max, 2),
        "breaker_suggested": breaker_commercial,
        "overload_range": f"{round(overload_min, 2)} A - {round(overload_max, 2)} A"
    }

def select_commercial_breaker(ampacity: float) -> int:
    standard_sizes = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150, 175, 200, 225, 250, 300, 350, 400]
    for size in standard_sizes:
        if size >= ampacity:
            return size
    return standard_sizes[-1]
