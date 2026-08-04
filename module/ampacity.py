from utils.db_loader import get_ampacity_data, get_temp_correction_data

def get_temp_factor(temp_c: int, temp_rating: str, temp_data: list) -> float:
    """Obtiene el factor de corrección por temperatura ambiente."""
    # Convertir a string por si viene como entero desde el slider/number_input
    temp_rating_str = str(temp_rating).replace("C", "")
    key = f"factor_{temp_rating_str}C"  # Busca 'factor_60C', 'factor_75C', etc.
    
    for row in temp_data:
        if row["min"] <= temp_c <= row["max"]:
            return row.get(key, 1.0)
    return 1.0

def get_grouping_factor(num_conductors: int) -> float:
    """Obtiene el factor de ajuste por número de conductores en canalización."""
    if num_conductors <= 3:
        return 1.0
    elif num_conductors <= 6:
        return 0.80
    elif num_conductors <= 9:
        return 0.70
    elif num_conductors <= 20:
        return 0.50
    elif num_conductors <= 30:
        return 0.45
    elif num_conductors <= 40:
        return 0.40
    else:
        return 0.35

def calculate_adjusted_ampacity(material: str, awg: str, temp_rating: str, ambient_temp_c: int, num_conductors: int) -> dict:
    ampacity_data = get_ampacity_data()
    temp_data = get_temp_correction_data()["ambient_temp_c"]
    
    # Ampacidad base de la tabla 310.16
    base_ampacity = ampacity_data[material][awg][str(temp_rating)]
    
    # Factores de corrección (se pasa ambient_temp_c corregido)
    f_temp = get_temp_factor(ambient_temp_c, temp_rating, temp_data)
    f_group = get_grouping_factor(num_conductors)
    
    # Ampacidad final ajustada
    adjusted_ampacity = base_ampacity * f_temp * f_group
    
    return {
        "base_ampacity": base_ampacity,
        "f_temp": f_temp,
        "f_group": f_group,
        "adjusted_ampacity": round(adjusted_ampacity, 2)
    }