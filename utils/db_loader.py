from utils.db_loader import get_ampacity_data, get_temp_correction_data

def get_temp_factor(temp_c: int, temp_rating: str, temp_data: list) -> float:
    temp_rating_str = str(temp_rating).replace("C", "").strip()
    key = f"factor_{temp_rating_str}C"
    
    for row in temp_data:
        if row["min"] <= int(temp_c) <= row["max"]:
            return float(row.get(key, 1.0))
    return 1.0

def get_grouping_factor(num_conductors: int) -> float:
    num = int(num_conductors)
    if num <= 3: return 1.0
    elif num <= 6: return 0.80
    elif num <= 9: return 0.70
    elif num <= 20: return 0.50
    elif num <= 30: return 0.45
    elif num <= 40: return 0.40
    else: return 0.35

def calculate_adjusted_ampacity(material: str, awg, temp_rating, ambient_temp_c, num_conductors) -> dict:
    ampacity_data = get_ampacity_data()
    
    # 1. Extraer lista de temperaturas
    temp_json = get_temp_correction_data()
    temp_data = temp_json["ambient_temp_c"]
    
    # 2. Formatear llaves
    mat_str = str(material).strip()
    awg_str = str(awg).strip()
    temp_rating_str = str(temp_rating).replace("C", "").strip()
    
    # 3. Obtener valores
    base_ampacity = float(ampacity_data[mat_str][awg_str][temp_rating_str])
    f_temp = get_temp_factor(ambient_temp_c, temp_rating_str, temp_data)
    f_group = get_grouping_factor(num_conductors)
    
    adjusted_ampacity = base_ampacity * f_temp * f_group
    
    return {
        "base_ampacity": base_ampacity,
        "f_temp": f_temp,
        "f_group": f_group,
        "adjusted_ampacity": round(adjusted_ampacity, 2)
    }