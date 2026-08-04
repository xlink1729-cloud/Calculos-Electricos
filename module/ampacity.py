from utils.db_loader import get_ampacity_data, get_temp_correction_data

def get_temp_factor(temp_c: int, temp_rating, temp_data: list) -> float:
    """Obtiene el factor de corrección por temperatura ambiente."""
    # Forzamos a string y quitamos cualquier 'C' sobrante para buscar 'factor_75C'
    temp_rating_str = str(temp_rating).replace("C", "").strip()
    key = f"factor_{temp_rating_str}C"
    
    for row in temp_data:
        if row["min"] <= int(temp_c) <= row["max"]:
            return float(row.get(key, 1.0))
    return 1.0

def get_grouping_factor(num_conductors: int) -> float:
    """Obtiene el factor de ajuste por número de conductores en canalización."""
    num = int(num_conductors)
    if num <= 3:
        return 1.0
    elif num <= 6:
        return 0.80
    elif num <= 9:
        return 0.70
    elif num <= 20:
        return 0.50
    elif num <= 30:
        return 0.45
    elif num <= 40:
        return 0.40
    else:
        return 0.35

def calculate_adjusted_ampacity(material: str, awg, temp_rating, ambient_temp_c, num_conductors) -> dict:
    ampacity_data = get_ampacity_data()
    temp_data = get_temp_correction_data()["ambient_temp_c"]
    
    # Asegurar conversión a STRING para las llaves del JSON
    mat_str = str(material).strip()
    awg_str = str(awg).strip()
    temp_rating_str = str(temp_rating).replace("C", "").strip()
    
    # Ampacidad base de la tabla 310.16
    base_ampacity = float(ampacity_data[mat_str][awg_str][temp_rating_str])
    
    # Factores de corrección
    f_temp = get_temp_factor(ambient_temp_c, temp_rating_str, temp_data)
    f_group = get_grouping_factor(num_conductors)
    
    # Ampacidad final ajustada
    adjusted_ampacity = base_ampacity * f_temp * f_group
    
    return {
        "base_ampacity": base_ampacity,
        "f_temp": f_temp,
        "f_group": f_group,
        "adjusted_ampacity": round(adjusted_ampacity, 2)
    }