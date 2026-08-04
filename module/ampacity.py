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
    temp_json = get_temp_correction_data()
    temp_data = temp_json["ambient_temp_c"]
    
    # Normalizar textos
    mat_str = str(material).lower().strip() # 'cobre' o 'aluminio' / 'copper'
    # Intentar coincidencia exacta o en inglés según tu JSON
    if mat_str not in ampacity_data:
        mat_map = {"cobre": "Copper", "aluminio": "Aluminum"}
        mat_str = mat_map.get(mat_str, mat_str)

    awg_str = str(awg).strip()
    
    # Manejar si el JSON usa '60' o '60C'
    raw_temp = str(temp_rating).strip()
    clean_temp = raw_temp.replace("C", "").strip()
    
    # Obtener el diccionario del calibre seleccionado
    awg_dict = ampacity_data[mat_str][awg_str]
    
    # Buscar el valor de ampacidad de forma flexible
    if raw_temp in awg_dict:
        base_ampacity = float(awg_dict[raw_temp])
    elif clean_temp in awg_dict:
        base_ampacity = float(awg_dict[clean_temp])
    elif f"{clean_temp}C" in awg_dict:
        base_ampacity = float(awg_dict[f"{clean_temp}C"])
    else:
        raise KeyError(f"No se encontró el aislamiento '{temp_rating}' para {awg_str} en {mat_str}.")
    
    # Factores de corrección
    f_temp = get_temp_factor(ambient_temp_c, clean_temp, temp_data)
    f_group = get_grouping_factor(num_conductors)
    
    adjusted_ampacity = base_ampacity * f_temp * f_group
    
    return {
        "base_ampacity": base_ampacity,
        "f_temp": f_temp,
        "f_group": f_group,
        "adjusted_ampacity": round(adjusted_ampacity, 2)
    }