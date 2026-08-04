import math
from utils.db_loader import get_conductors_data, get_conduit_data

def get_max_allowed_fill_percentage(total_conductors_count: int) -> float:
    """Devuelve el % máximo de ocupación permitido según Cap 9, Tabla 1."""
    if total_conductors_count == 1:
        return 53.0
    elif total_conductors_count == 2:
        return 31.0
    else:
        return 40.0  # 3 o más conductores

def calculate_conduit_fill(
    conduit_type: str,
    conductors_list: list
) -> dict:
    """
    Calcula el llenado de tubería.
    
    conductors_list: Lista de diccionarios con la mezcla de cables, ej:
    [
        {"material": "cobre", "awg": "10", "quantity": 3},
        {"material": "cobre", "awg": "12", "quantity": 1} # Tierra
    ]
    """
    conductors_db = get_conductors_data()
    conduit_db = get_conduit_data()
    
    if conduit_type not in conduit_db:
        raise ValueError(f"Tipo de tubo {conduit_type} no soportado.")
        
    total_conductors_area = 0.0
    total_conductors_count = 0
    
    # Calcular el área total ocupada por todos los conductores
    for item in conductors_list:
        mat = item["material"]
        awg = str(item["awg"])
        qty = int(item["quantity"])
        
        cond_info = conductors_db[mat][awg]
        diameter_mm = cond_info["diameter_mm"]
        
        # Área transversal del cable (π * d² / 4)
        single_area = (math.pi * (diameter_mm ** 2)) / 4.0
        
        total_conductors_area += single_area * qty
        total_conductors_count += qty

    if total_conductors_count == 0:
        return {"error": "No se han agregado conductores."}

    max_fill_percent = get_max_allowed_fill_percentage(total_conductors_count)
    
    # Evaluar la ocupación para cada diámetro comercial de tubo
    conduit_evaluations = []
    recommended_trade_size = None
    
    for trade_size, dimensions in conduit_db[conduit_type].items():
        total_pipe_area = dimensions["total_area_mm2"]
        allowed_area = total_pipe_area * (max_fill_percent / 100.0)
        actual_fill_percent = (total_conductors_area / total_pipe_area) * 100.0
        
        fits = total_conductors_area <= allowed_area
        
        eval_data = {
            "trade_size": trade_size,
            "total_pipe_area_mm2": total_pipe_area,
            "allowed_area_mm2": round(allowed_area, 2),
            "actual_fill_percent": round(actual_fill_percent, 2),
            "fits": fits
        }
        
        conduit_evaluations.append(eval_data)
        
        if fits and recommended_trade_size is None:
            recommended_trade_size = eval_data

    return {
        "total_conductors_count": total_conductors_count,
        "total_conductors_area_mm2": round(total_conductors_area, 2),
        "max_allowed_fill_percent": max_fill_percent,
        "recommended_conduit": recommended_trade_size,
        "all_evaluations": conduit_evaluations
    }