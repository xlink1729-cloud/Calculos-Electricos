import streamlit as st
from utils.db_loader import get_ampacity_data, get_conductors_data, get_motors_data
from modules.ampacity import calculate_adjusted_ampacity
from modules.voltage_drop import calculate_voltage_drop
from modules.motor_calc import calculate_motor_circuit

st.set_page_config(page_title="Cálculos Eléctricos NOM-001 / NEC", page_icon="⚡", layout="wide")

st.title("⚡ Calculadora de Circuitos Eléctricos (NOM-001 / NEC)")
st.caption("Cálculo de ampacidad corregida, caída de tensión y circuitos de motores según normativa")

# PESTAÑAS PRINCIPALES
tab_alimentadores, tab_motores = st.tabs([
    "⚡ Alimentadores / Cargas Generales", 
    "🔄 Motores Eléctricos (Art. 430)"
])

# ==========================================
# PESTAÑA 1: ALIMENTADORES Y CAÍDA DE TENSIÓN
# ==========================================
with tab_alimentadores:
    ampacity_db = get_ampacity_data()

    st.sidebar.header("⚙️ Parámetros de Alimentadores")
    material = st.sidebar.selectbox("Material del Conductor", options=["cobre", "aluminio"], format_func=lambda x: x.capitalize())

    available_awg = list(ampacity_db[material].keys())
    awg = st.sidebar.selectbox("Calibre del Conductor (AWG / kcmil)", options=available_awg, index=available_awg.index("10") if "10" in available_awg else 0)

    temp_rating = st.sidebar.selectbox("Aislamiento / Temp. Terminales", options=["60C", "75C", "90C"])

    st.sidebar.subheader("Condiciones de Instalación")
    ambient_temp_c = st.sidebar.slider("Temperatura Ambiente (°C)", min_value=21, max_value=50, value=30, step=1)
    num_conductors = st.sidebar.number_input("Conductores Portadores de Corriente", min_value=1, max_value=40, value=3)

    st.sidebar.subheader("Carga y Distancia")
    system_type = st.sidebar.selectbox("Tipo de Sistema", ["Monofásico 1Ø (2 hilos)", "Trifásico 3Ø (3 o 4 hilos)"])
    voltage_nominal = st.sidebar.number_input("Voltaje Nominal (V)", value=120.0 if "Monofásico" in system_type else 220.0, step=10.0)
    current_amps = st.sidebar.number_input("Corriente de Carga (A)", min_value=0.1, value=20.0, step=1.0)
    length_meters = st.sidebar.number_input("Longitud del Circuito (m)", min_value=1.0, value=30.0, step=5.0)
    power_factor = st.sidebar.slider("Factor de Potencia (FP)", min_value=0.70, max_value=1.00, value=0.90, step=0.01)

    # Panel de Resultados
    col1, col2 = st.columns(2)

    amp_res = calculate_adjusted_ampacity(material, awg, temp_rating, ambient_temp_c, num_conductors)

    with col1:
        st.subheader("1. Ampacidad del Conductor")
        st.metric("Ampacidad Corregida", f"{amp_res['adjusted_ampacity']} A")
        
        st.write(f"• **Ampacidad Base (Tabla 310.16):** {amp_res['base_ampacity']} A")
        st.write(f"• **Factor Temp. Ambiente ({ambient_temp_c}°C):** {amp_res['f_temp']}")
        st.write(f"• **Factor Agrupamiento ({num_conductors} cond.):** {amp_res['f_group']}")
        
        if current_amps > amp_res['adjusted_ampacity']:
            st.error(f"⚠️ La corriente de carga ({current_amps} A) supera la ampacidad corregida ({amp_res['adjusted_ampacity']} A).")
        else:
            st.success("✅ El calibre soporta la corriente de carga asignada.")

    vd_res = calculate_voltage_drop(material, awg, current_amps, length_meters, voltage_nominal, system_type, power_factor)

    with col2:
        st.subheader("2. Caída de Voltaje")
        
        delta_v_color = "normal" if vd_res['v_drop_percent'] <= 3.0 else "inverse"
        st.metric("Caída de Voltaje (%)", f"{vd_res['v_drop_percent']} %", delta=f"{vd_res['v_drop_volts']} V", delta_color=delta_v_color)
        
        st.write(f"• **Voltaje en la Carga:** {vd_res['v_final']} V")
        st.write(f"• **Impedancia Eficaz (Z):** {vd_res['impedance_z']} Ω/km")
        
        if vd_res['v_drop_percent'] <= 3.0:
            st.success("✅ Caída de voltaje dentro del límite del 3%.")
        elif vd_res['v_drop_percent'] <= 5.0:
            st.warning("⚠️ Caída entre 3% y 5%. Aceptable solo para alimentador total + derivado.")
        else:
            st.error("❌ Caída de voltaje superior al 5%. Aumenta el calibre.")


# ==========================================
# PESTAÑA 2: MOTORES ELÉCTRICOS (ART. 430)
# ==========================================
with tab_motores:
    st.header("🔄 Circuito Derivado de Motor Trifásico")
    st.caption("Dimensionamiento de alimentador y protecciones conforme al Artículo 430 NOM-001/NEC")

    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.subheader("Datos de la Carga")
        hp_selected = st.selectbox("Potencia Nominal (HP)", options=["0.5", "0.75", "1", "1.5", "2", "3", "5", "7.5", "10", "15", "20", "25", "30", "50"])
        voltage_selected = st.selectbox("Voltaje de Operación", options=["220V", "440V"])
        
        calc_motor = st.button("🚀 Calcular Circuito de Motor", use_container_width=True)

    with col_m2:
        if calc_motor:
            motor_res = calculate_motor_circuit(hp_selected, voltage_selected)
            
            st.subheader("Resultados del Dimensionamiento")
            st.metric("Corriente a Carga Plena (FLC / NOM)", f"{motor_res['flc']} A")
            
            st.markdown("---")
            st.write(f"• **Ampacidad Mínima Conductor (125% FLC - Art. 430.22):** `{motor_res['conductor_min_ampacity']} A`")
            st.write(f"• **Protección Máx. Cortocircuito / ITM (Art. 430.52):** `{motor_res['breaker_max_calc']} A`")
            st.write(f"• **Termomagnético Comercial Sugerido:** `{motor_res['breaker_suggested']} A`")
            st.write(f"• **Rango de Ajuste Sobrecarga (115%-125%):** `{motor_res['overload_range']}`")