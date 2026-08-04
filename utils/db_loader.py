import json
import os
import streamlit as st

@st.cache_data
def load_json_data(file_name: str) -> dict:
    """Carga un archivo JSON desde la carpeta data/."""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_path, "data", file_name)
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_ampacity_data():
    return load_json_data("ampacity_310_16.json")

def get_conductors_data():
    return load_json_data("conductors.json")

def get_temp_correction_data():
    return load_json_data("temp_correction.json")

def get_conduit_data():
    return load_json_data("conduit_dimensions.json")