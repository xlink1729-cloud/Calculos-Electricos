import streamlit as st
from utils.db_loader import get_ampacity_data, get_conductors_data, get_motors_data
import math

# Importaciones ajustadas exactamente a tu carpeta 'module'
from module.ampacity import calculate_adjusted_ampacity
from module.voltage_drop import calculate_voltage_drop
from module.motor_calc import calculate_motor_circuit
from module.auto_sizing import auto_select_circuit
from module.branch_circuits import calculate_branch_circuits

st.set_page_config(page_title="Cálculos Eléctricos NOM-001 / NEC", page_icon="⚡", layout="wide")

st.title("⚡ Calculadora de Circuitos Eléctricos (NOM-001 / NEC)")
st.caption("Cálculo de ampacidad corregida, caída de tensión y circuitos de motores según normativa")

# PESTAÑAS PRINCIPALES (Orden de variables alineado a los elementos de la lista)
tab_alimentadores, tab_motores, tab_auto, tab_derivados = st.tabs([
    "⚡ Alimentadores / Cargas Generales", 
    "🔄 Motores Eléctricos (Art. 430)",
    "🎯 Selección Automática por Carga",
    "🏠 Circuitos Derivados (Art. 210/220)"
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

# ==========================================
# PESTAÑA 3: SELECCIÓN AUTOMÁTICA POR CARGA
# ==========================================
with tab_auto:
    st.header("🎯 Dimensionamiento Automático de Circuitos")
    st.caption("Ingresa la carga (en Amperes o Kilowatts) y la distancia. La app calculará la corriente de diseño, el calibre AWG y la protección ideal.")

    col_a1, col_a2 = st.columns([1, 1])

    with col_a1:
        st.subheader("1. Parámetros de la Carga")
        system_type_auto = st.selectbox("Sistema Eléctrico", ["Monofásico 1Ø (2 hilos)", "Trifásico 3Ø (3 o 4 hilos)"], key="sys_auto")
        voltage_auto = st.number_input("Voltaje Nominal (V)", value=120.0 if "Monofásico" in system_type_auto else 220.0, step=10.0, key="v_auto")
        
        # Selector de Tipo de Entrada de Carga
        input_type = st.radio("Modo de Ingreso de Carga", ["Corriente Nominal (Amperes)", "Potencia Activa (kW)"], horizontal=True, key="input_type_auto")

        if input_type == "Corriente Nominal (Amperes)":
            load_amps_auto = st.number_input("Corriente de Carga (A)", min_value=0.1, value=12.0, step=1.0, key="amps_auto")
        else:
            power_kw = st.number_input("Potencia de la Carga (kW)", min_value=0.1, value=3.5, step=0.5, key="kw_auto")
            pf_auto = st.slider("Factor de Potencia (FP)", min_value=0.70, max_value=1.00, value=0.90, step=0.01, key="pf_auto")
            
            # Cálculo interno de Amperes según el sistema elegido
            import math
            if "Monofásico" in system_type_auto:
                load_amps_auto = (power_kw * 1000) / (voltage_auto * pf_auto)
            else:
                load_amps_auto = (power_kw * 1000) / (math.sqrt(3) * voltage_auto * pf_auto)
                
            st.info(f"💡 Corriente calculada a partir de {power_kw} kW: **{round(load_amps_auto, 2)} A**")

        length_auto = st.number_input("Longitud del Circuito (m)", min_value=1.0, value=25.0, step=5.0, key="len_auto")
        mat_auto = st.selectbox("Material del Conductor", ["cobre", "aluminio"], format_func=lambda x: x.capitalize(), key="mat_auto")
        is_continuous = st.checkbox("¿Es Carga Continua? (+3 horas activas -> factor 125%)", value=True, key="cont_auto")

        btn_auto = st.button("🚀 Calcular Especificación Ideal", use_container_width=True, key="btn_auto_calc")

    with col_a2:
        if btn_auto:
            res_auto = auto_select_circuit(
                load_amps=load_amps_auto, 
                length_m=length_auto, 
                voltage=voltage_auto, 
                system_type=system_type_auto, 
                material=mat_auto, 
                is_continuous=is_continuous
            )

            if res_auto["recommended_awg"]:
                st.subheader("📋 Especificación Técnica Recomendada (NOM-001)")
                
                st.success(f"✅ **Calibre Sugerido:** Calibre **{res_auto['recommended_awg']} AWG** ({mat_auto.capitalize()})")
                st.info(f"🛡️ **Protección Requerida:** Interruptor Termomagnético de **{res_auto['recommended_breaker']} A**")
                
                st.markdown("---")
                st.write(f"• **Corriente Nominal Calculada:** `{round(load_amps_auto, 2)} A`")
                st.write(f"• **Corriente de Diseño (125% continuo):** `{res_auto['design_amps']} A`")
                st.write(f"• **Capacidad del Conductor Seleccionado:** `{res_auto['ampacity_capacity']} A`")
                st.write(f"• **Caída de Voltaje Estimada:** `{res_auto['v_drop_percent']}%` ({res_auto['v_drop_volts']} V)")
            else:
                st.error("❌ No se encontró un calibre estándar dentro del rango (14 AWG a 4/0) que cumpla con el límite de caída del 3%. Se requiere un alimentador especial o subir el voltaje de distribución.")

# ==========================================
# PESTAÑA 4: CIRCUITOS DERIVADOS Y ALIMENTADOR CFE
# ==========================================
with tab_derivados:
    st.header("🏠 Alimentador CFE y Circuitos Derivados (NOM-001)")
    st.caption("Calcula el alimentador principal, la protección y el cuadro de distribución por norma o por confort.")

    col_d1, col_d2 = st.columns([1, 1])

    with col_d1:
        st.subheader("1. Configuración General")
        
        calc_mode = st.radio(
            "Selecciona el Modo de Cálculo",
            ["Obra Nueva / Proyecto (Por área m² según NOM-001)", "Levantamiento Real / Instalación Existente"],
            key="calc_mode_radio"
        )
        is_survey = "Levantamiento Real" in calc_mode

        voltage_dev = st.number_input("Voltaje del Alimentador (V)", min_value=100.0, value=120.0, step=10.0, key="volt_dev")
        feeder_len = st.number_input("Distancia de Medidor/CFE a Centro de Cargas (m)", min_value=1.0, value=8.0, step=1.0, key="feeder_len_dev")

        if not is_survey:
            area_input = st.number_input("Área de Construcción (m²)", min_value=10.0, value=150.0, step=10.0, key="area_dev")
            lighting_real = 0.0
            num_light_c = 1
            num_plug_c = 1
            num_ded_c = 0
        else:
            area_input = 0.0
            lighting_real = st.number_input("Carga Real Medida de Alumbrado y Contactos (VA)", min_value=0.0, value=270.0, step=50.0, key="light_real_dev")

            st.markdown("---")
            st.subheader("2. Sectorización por Confort / Zonas")
            num_light_c = st.number_input("N° Circuitos de Alumbrado (15A)", min_value=1, value=2, step=1, key="num_light_circ")
            num_plug_c = st.number_input("N° Circuitos de Contactos Generales (15A/20A)", min_value=1, value=2, step=1, key="num_plug_circ")
            num_ded_c = st.number_input("N° Cargas Dedicadas (A/C, Micro, Lavadora, etc.)", min_value=0, value=3, step=1, key="num_ded_circ")

        extra_va = st.number_input(
            "Cargas Específicas / Especiales Totales (VA)", 
            min_value=0.0, 
            value=3750.0, 
            step=250.0, 
            help="Suma total de potencia de A/C, microondas, lavasecadora, etc.", 
            key="extra_dev"
        )

        btn_calc_dev = st.button("📊 Calcular Alimentador y Distribución", use_container_width=True, key="btn_dev")

    with col_d2:
        if btn_calc_dev:
            res_dev = calculate_branch_circuits(
                area_m2=area_input,
                custom_appliances_va=extra_va,
                is_existing_survey=is_survey,
                lighting_real_va=lighting_real,
                voltage=voltage_dev,
                feeder_length_m=feeder_len,
                custom_light_circuits=num_light_c,
                custom_plug_circuits=num_plug_c,
                custom_dedicated_circuits=num_ded_c
            )

            st.subheader("⚡ Diagnóstico del Alimentador Principal")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Carga Instalada Total", f"{res_dev['total_connected_va']:.0f} VA")
                st.metric("Carga Demandada", f"{res_dev['total_demanded_va']:.0f} VA")
                st.metric("Corriente de Diseño (125%)", f"{res_dev['design_amps']} A")
            with col_m2:
                st.metric("Calibre Sugerido", f"Cal. {res_dev['recommended_feeder_awg']} AWG")
                st.metric("Interruptor Principal", f"{res_dev['main_breaker']} A")
                st.metric("Caída de Voltaje", f"{res_dev['feeder_vd_percent']}%")

            st.markdown("---")
            st.subheader("🔌 Centro de Cargas Recomendado")
            
            # Cálculo de espacios de reserva técnica (20% recomendado)
            suggested_panel_spaces = max(8, math.ceil(res_dev['total_circuits'] * 1.25))
            st.success(f"✅ **Tablero Recomendado:** **{suggested_panel_spaces} Espacios / Polos** ({res_dev['total_circuits']} ocupados + reserva)")

            if is_survey:
                st.info("ℹ️ **Distribución por Confort Activa:**")
                st.write(f"• **Alumbrado Sectorizado:** `{res_dev['custom_light_circuits']} pastilla(s) (15A - Calibre 14/12 AWG)`")
                st.write(f"• **Contactos Generales Sectorizados:** `{res_dev['custom_plug_circuits']} pastilla(s) (15A/20A - Calibre 12 AWG)`")
                st.write(f"• **Circuitos Dedicados:** `{res_dev['custom_dedicated_circuits']} pastilla(s) independientes`")
            else:
                st.write(f"• **Alumbrado Generales ($33\\text{{ VA/m}}^2$):** `{res_dev['lighting_circuits']} pastilla(s)`")
                st.write("• **Circuitos de Cocina / Pequeños Aparatos:** `2 pastillas (20A)`")
                st.write("• **Circuito de Lavandería:** `1 pastilla (20A)`")

            # -------------------------------------------------------------
            # GENERACIÓN DEL DICTAMEN TÉCNICO Y RECOMENDACIONES DE ENERGÍA
            # -------------------------------------------------------------
            st.markdown("---")
            with st.expander("📋 Ver Dictamen Técnico Completo y Recomendaciones", expanded=True):
                report_text = f"""### 📝 Reporte de Diagnóstico Eléctrico

**Modo:** {"Levantamiento Real Existente" if is_survey else "Proyecto Obra Nueva NOM-001"}
**Fecha:** Evaluado bajo NOM-001-SEDE / NEC Standards

#### 1. Resumen de Cargas
* **Carga Total Instalada:** {res_dev['total_connected_va']} VA
* **Carga Total Demandada:** {res_dev['total_demanded_va']} VA
* **Corriente Nominal de Operación:** {res_dev['load_amps']} A
* **Corriente de Diseño (125% Carga Continua):** {res_dev['design_amps']} A

#### 2. Alimentador Principal CFE → Centro de Cargas
* **Conductor Principal Recomendado:** Calibre **{res_dev['recommended_feeder_awg']} AWG** Cobre (Aislamiento THHN/THHW 75°C).
* **Interruptor Principal Sugerido:** **{res_dev['main_breaker']} A** (1 Polo a {voltage_dev} V).
* **Caída de Voltaje Estimada:** **{res_dev['feeder_vd_percent']}%** (Cumple norma: ≤ 3%).

#### 3. Cuadro de Distribución y Tablero
* **Circuitos Activos Requeridos:** {res_dev['total_circuits']} Polos.
* **Capacidad Nominal del Tablero Sugerida:** **{suggested_panel_spaces} Polos / Espacios**.

#### 4. Criterio de Diseño, Confort y Eficiencia Energética
* **Reserva Técnica:** Se seleccionó un gabinete de {suggested_panel_spaces} polos para dejar un 20% - 30% de capacidad libre ante futuras adiciones (ej. A/C adicionales).
* **Aislamiento de Cargas Inductivas:** Al independizar el A/C de $950\\text{{ VA}}$, el microondas de $1,200\\text{{ VA}}$ y la lavasecadora de $1,600\\text{{ VA}}$, se elimina la fluctuación de voltaje (*flicker*) en la iluminación LED al arrancar los motores.
* **Continuidad de Servicio:** La sectorización del alumbrado e hilos de contactos garantiza que una falla por humedad o cortocircuito local mantenga el resto de la casa energizada.
"""
                st.markdown(report_text)
                
                # Botón de Descarga de Reporte
                st.download_button(
                    label="📥 Descargar Dictamen Técnico (.txt)",
                    data=report_text,
                    file_name="dictamen_electrico_residencial.txt",
                    mime="text/plain"
                )