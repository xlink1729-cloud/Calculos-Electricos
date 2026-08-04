import streamlit as st
from utils.db_loader import get_ampacity_data, get_conductors_data
from module.ampacity import calculate_adjusted_ampacity
from module.voltage_drop import calculate_voltage_drop

st.set_page_config(page_title="Cálculos Eléctricos NOM-001 / NEC", page_icon="⚡", layout="wide")

st.title("⚡ Calculadora de Conductores Eléctricos (NOM-001 / NEC)")
st.caption("Cálculo de ampacidad corregida y caída de tensión según normativa")

# Cargar opciones dinámicas desde la BD
ampacity_db = get_ampacity_data()
conductors_db = get_conductors_data()

# --- BARRA LATERAL (ENTRADAS DE PARÁMETROS) ---
st.sidebar.header("⚙️ Parámetros de la Instalación")

material = st.sidebar.selectbox("Material del Conductor", options=["cobre", "aluminio"], format_func=lambda x: x.capitalize())

# Filtrar calibres disponibles según el material seleccionado
available_awg = list(ampacity_db[material].keys())
awg = st.sidebar.selectbox("Calibre del Conductor (AWG / kcmil)", options=available_awg, index=available_awg.index("10") if "10" in available_awg else 0)

temp_rating = st.sidebar.selectbox("Aislamiento / Temperatura de Terminales", options=["60C", "75C", "90C"])

st.sidebar.subheader("Condiciones de Instalación")
ambient_temp = st.sidebar.slider("Temperatura Ambiente (°C)", min_value=21, max_value=50, value=30, step=1)
num_conductors = st.sidebar.number_input("Número de Conductores Portadores de Corriente", min_value=1, max_value=40, value=3)

st.sidebar.subheader("Carga y Distancia")
system_type = st.sidebar.selectbox("Tipo de Sistema", ["Monofásico 1Ø (2 hilos)", "Trifásico 3Ø (3 o 4 hilos)"])
voltage_nominal = st.sidebar.number_input("Voltaje Nominal (V)", value=120.0 if "Monofásico" in system_type else 220.0, step=10.0)
current_amps = st.sidebar.number_input("Corriente de Carga (A)", min_value=0.1, value=20.0, step=1.0)
length_meters = st.sidebar.number_input("Longitud del Circuito (m)", min_value=1.0, value=30.0, step=5.0)
power_factor = st.sidebar.slider("Factor de Potencia (FP)", min_value=0.70, max_value=1.00, value=0.90, step=0.01)

# --- PANEL PRINCIPAL DE RESULTADOS ---
col1, col2 = st.columns(2)

# CÁLCULO 1: AMPACIDAD
amp_res = calculate_adjusted_ampacity(material, awg, temp_rating, ambient_temp, num_conductors)

with col1:
    st.subheader("1. Ampacidad del Conductor")
    st.metric("Ampacidad Corregida", f"{amp_res['adjusted_ampacity']} A")
    
    st.write(f"• **Ampacidad Base (Tabla 310.16):** {amp_res['base_ampacity']} A")
    st.write(f"• **Factor por Temp. Ambiente ({ambient_temp}°C):** {amp_res['f_temp']}")
    st.write(f"• **Factor por Agrupamiento ({num_conductors} cond.):** {amp_res['f_group']}")
    
    if current_amps > amp_res['adjusted_ampacity']:
        st.error(f"⚠️ La corriente de carga ({current_amps} A) supera la ampacidad corregida ({amp_res['adjusted_ampacity']} A). ¡Aumenta el calibre!")
    else:
        st.success("✅ El calibre soporta la corriente de carga asignada.")

# CÁLCULO 2: CAÍDA DE VOLTAJE
vd_res = calculate_voltage_drop(material, awg, current_amps, length_meters, voltage_nominal, system_type, power_factor)

with col2:
    st.subheader("2. Caída de Voltaje")
    
    delta_v_color = "normal" if vd_res['v_drop_percent'] <= 3.0 else "inverse"
    st.metric("Caída de Voltaje (%)", f"{vd_res['v_drop_percent']} %", delta=f"{vd_res['v_drop_volts']} V", delta_color=delta_v_color)
    
    st.write(f"• **Voltaje en la Carga:** {vd_res['v_final']} V")
    st.write(f"• **Impedancia Eficaz (Z):** {vd_res['impedance_z']} Ω/km")
    
    if vd_res['v_drop_percent'] <= 3.0:
        st.success("✅ Caída de voltaje dentro del límite recomendado del 3% (Circuitos derivados).")
    elif vd_res['v_drop_percent'] <= 5.0:
        st.warning("⚠️ Caída entre 3% y 5%. Aceptable solo si es el alimentador total + derivado combinados.")
    else:
        st.error("❌ Caída de voltaje superior al 5%. Se recomienda subir de calibre para evitar pérdidas exesivas.")