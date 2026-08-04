import json
import os

# Obtiene la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_ampacity_data():
    path = os.path.join(BASE_DIR, "data", "ampacity_310_16.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_temp_correction_data():
    path = os.path.join(BASE_DIR, "data", "temp_correction.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_conductors_data():
    path = os.path.join(BASE_DIR, "data", "conductors.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_conduit_data():
    path = os.path.join(BASE_DIR, "data", "conduit_dimensions.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)