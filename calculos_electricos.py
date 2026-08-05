import streamlit as st
from utils.db_loader import get_ampacity_data, get_conductors_data, get_motors_data
import math

# Importaciones ajustadas exactamente a tu carpeta 'module'
from module.ampacity import calculate_adjusted_ampacity
from module.voltage_drop import calculate_voltage_drop
from module.motor_calc import calculate_motor_circuit
from module.auto_sizing import auto_select_circuit
from module.branch_circuits import (
    calculate_branch_circuits,
    audit_service_entrance_health,
    calculate_phase_balance,
    calculate_solar_pv_system,
    generate_pdf_audit_report,
)

st.set_page_config(page_title="Cálculos Eléctricos NOM-001 / NEC", page_icon="⚡", layout="wide")

st.title("⚡ Calculadora de Circuitos Eléctricos (NOM-001 / NEC)")
st.caption("Cálculo de ampacidad corregida, caída de tensión y circuitos de motores según normativa")

# PESTAÑAS PRINCIPALES (Orden de variables alineado a los elementos de la lista)
tab_alimentadores, tab_motores, tab_auto, tab_derivados, tab_auditoria, tab_balanceo, tab_solar = st.tabs([
    "⚡ Alimentadores / Cargas Generales", 
    "🔄 Motores Eléctricos (Art. 430)",
    "🎯 Selección Automática por Carga",
    "🏠 Circuitos Derivados (Art. 210/220)",
    "🔍 Levantamiento Real / Auditoría",
    "⚖️ Cuadro de Cargas y Balanceo 2F",
    "☀️ Dimensionamiento Solar (Art. 690)"
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
            [
                "Obra Nueva / Proyecto (Por área m² según NOM-001)",
                "Levantamiento Real / Instalación Existente",
            ],
            key="calc_mode_radio",
        )
        is_survey = "Levantamiento Real" in calc_mode

        voltage_dev = st.number_input(
            "Voltaje del Alimentador (V)",
            min_value=100.0,
            value=120.0,
            step=10.0,
            key="volt_dev",
        )
        feeder_len = st.number_input(
            "Distancia de Medidor/CFE a Centro de Cargas (m)",
            min_value=1.0,
            value=8.0,
            step=1.0,
            key="feeder_len_dev",
        )

        if not is_survey:
            area_input = st.number_input(
                "Área de Construcción (m²)",
                min_value=10.0,
                value=150.0,
                step=10.0,
                key="area_dev",
            )
            lighting_real = 0.0
            num_light_c = 1
            num_plug_c = 1
            num_ded_c = 0
        else:
            area_input = 0.0
            lighting_real = st.number_input(
                "Carga Real Medida de Alumbrado y Contactos (VA)",
                min_value=0.0,
                value=270.0,
                step=50.0,
                key="light_real_dev",
            )

            st.markdown("---")
            st.subheader("2. Sectorización por Confort / Zonas")
            num_light_c = st.number_input(
                "N° Circuitos de Alumbrado (15A)",
                min_value=1,
                value=2,
                step=1,
                key="num_light_circ",
            )
            num_plug_c = st.number_input(
                "N° Circuitos de Contactos Generales (15A/20A)",
                min_value=1,
                value=2,
                step=1,
                key="num_plug_circ",
            )
            num_ded_c = st.number_input(
                "N° Cargas Dedicadas (A/C, Micro, Lavadora, etc.)",
                min_value=0,
                value=3,
                step=1,
                key="num_ded_circ",
            )

        extra_va = st.number_input(
            "Cargas Específicas / Especiales Totales (VA)",
            min_value=0.0,
            value=3750.0,
            step=250.0,
            key="extra_dev",
        )

        if st.button("📊 Calcular Alimentador y Distribución", use_container_width=True, key="btn_dev"):
            st.session_state["res_dev"] = calculate_branch_circuits(
                area_m2=area_input,
                custom_appliances_va=extra_va,
                is_existing_survey=is_survey,
                lighting_real_va=lighting_real,
                voltage=voltage_dev,
                feeder_length_m=feeder_len,
                custom_light_circuits=num_light_c,
                custom_plug_circuits=num_plug_c,
                custom_dedicated_circuits=num_ded_c,
            )

    with col_d2:
        if "res_dev" in st.session_state and st.session_state["res_dev"] is not None:
            res_dev = st.session_state["res_dev"]

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

            # Verificación de la existencia de la función antes de invocar
            if "generate_pdf_audit_report" in globals() or "generate_pdf_audit_report" in locals():
                pdf_data = generate_pdf_audit_report(res_dev)
                st.download_button(
                    label="📥 Descargar Dictamen Técnico (.pdf)",
                    data=pdf_data,
                    file_name="dictamen_electrico_residencial.pdf",
                    mime="application/pdf",
                    key="dl_pdf_dev",
                )
            else:
                st.error("⚠️ La función `generate_pdf_audit_report` no se ha encontrado en el código. Verifica que esté definida o importada correctamente al inicio del script.")
        else:
            st.info("👈 Presiona **'Calcular Alimentador y Distribución'** para ver el resultado y habilitar la descarga del dictamen.")

# ==========================================
# PESTAÑA 5: LEVANTAMIENTO REAL / AUDITORÍA
# ==========================================
with tab_auditoria:
    st.header("Auditoría Técnica de Instalación Existente")
    st.markdown("Evaluación del estado de la acometida, protecciones principales y riesgo de falla térmica.")

    st.subheader("1. Cargas Medidas y Especificadas")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        load_lighting_contacts = st.number_input(
            "Carga Medida en Alumbrado / Contactos Generales (VA):",
            min_value=0.0,
            value=270.0,
            step=50.0,
            help="Consumo estimado o medido en circuitos de uso general."
        )
        
        num_circuits_lighting = st.number_input("N° Circuitos de Alumbrado:", min_value=1, value=2)
        num_circuits_outlets = st.number_input("N° Circuitos de Contactos Generales:", min_value=1, value=2)

    with col_c2:
        st.markdown("**Cargas Específicas / Dedicadas (VA):**")
        ac_va = st.number_input("A/C Minisplit Inverter (VA):", min_value=0.0, value=950.0, step=50.0)
        micro_va = st.number_input("Horno Microondas (VA):", min_value=0.0, value=1200.0, step=50.0)
        washer_va = st.number_input("Lavasecadora / Área de Lavado (VA):", min_value=0.0, value=1600.0, step=50.0)
        
        num_circuits_dedicated = st.number_input("N° Cargas Dedicadas Independientes:", min_value=1, value=3)

    # Cálculo de carga total continua para la auditoría
    total_va = load_lighting_contacts + ac_va + micro_va + washer_va
    voltage = 120.0  # Voltaje de fase nominal
    i_total = total_va / voltage  # Corriente total de diseño (A)

    st.markdown("---")
    st.subheader("2. Parámetros de la Acometida Actual (Infraestructura Existente)")
    
    col_a1, col_a2, col_a3 = st.columns(3)

    with col_a1:
        protection_type = st.radio(
            "Tipo de Protección Principal Existente:",
            ["Fusible (Cartucho)", "ITM (Pastilla/Breaker)"],
            index=0,
            help="Selecciona si el interruptor general usa fusibles de listón o pastilla termomagnética."
        )

    with col_a2:
        current_itm = st.selectbox(
            "Capacidad de Protección Actual (A):",
            [15, 20, 30, 40, 50, 60],
            index=2,  # 30A por defecto
            help="Valor nominal estampado en el fusible o la pastilla principal."
        )

    with col_a3:
        existing_awg = st.selectbox(
            "Calibre del Cable Alimentador Existente (AWG):",
            [14, 12, 10, 8, 6, 4],
            index=2,  # 10 AWG por defecto
            help="Calibre del cable de cobre que va desde la mufa/medidor hasta el tablero."
        )

    # --- Ejecución de la Auditoría ---
    health = audit_service_entrance_health(
        main_protection_type="Fusible" if "Fusible" in protection_type else "ITM",
        main_protection_amps=current_itm,
        existing_wire_awg=existing_awg,
        total_continuous_amps=i_total
    )

    st.markdown("---")
    st.subheader("3. Dictamen de Salud y Evaluación de Riesgo")

    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.metric(
            label="Corriente Demandada Sostenida",
            value=f"{i_total:.1f} A"
        )
    with col_m2:
        st.metric(
            label="Capacidad de Protección Actual",
            value=f"{current_itm} A"
        )
    with col_m3:
        st.metric(
            label="Porcentaje de Carga Sostenida",
            value=f"{health['load_percentage']}%",
            delta=f"Límite seguro NOM (80%): {health['safe_limit_amps']:.1f} A",
            delta_color="inverse" if health["load_percentage"] > 80 else "normal"
        )

    # Visualización de Alertas según Gravedad
    if health["status"] == "PELIGRO":
        st.error("🚨 **RIESGO CRÍTICO DETECTADO EN LA INSTALACIÓN**")
    elif health["status"] == "ADVERTENCIA":
        st.warning("⚠️ **ADVERTENCIA DE DEGRADACIÓN Y FATIGA TÉRMICA**")
    else:
        st.success("✅ **ACOMETIDA OPERANDO DENTRO DE PARÁMETROS SEGUROS**")

    # Lista de Riesgos Detectados
    st.markdown("**Hallazgos de la Evaluación:**")
    for risk in health["risks"]:
        st.write(f"- {risk}")

    # Acción Correctiva Recomendada
    st.info(f"💡 **Recomendación Técnica de Remediación:** {health['recommended_action']}")

    # Sugerencia de Dimensión de Tablero
    total_active_circuits = num_circuits_lighting + num_circuits_outlets + num_circuits_dedicated
    suggested_panel_spaces = max(8, math.ceil(total_active_circuits * 1.25))

    st.write(f"📌 **Espacios mínimos requeridos en Tablero Principal:** {suggested_panel_spaces} Polos (para {total_active_circuits} circuitos activos y reserva del 25%).")

# ==========================================
# PESTAÑA 6: CUADRO DE CARGAS Y BALANCEO (2F)
# ==========================================
with tab_balanceo:
    st.header("⚖️ Cuadro de Cargas y Balanceo de Fases (Sistemas 2F-1N / 220V)")
    st.markdown("Distribución de circuitos derivados para minimizar el retorno por el conductor neutro.")

    st.subheader("1. Configuración de Circuitos Derivados")

    # Ejemplo de tabla dinámica/editable para definir cargas y asignar fase
    default_circuits = [
        {"Circuito": "C1 - Alumbrado Social", "Carga (VA)": 600, "Fase": "A"},
        {"Circuito": "C2 - Alumbrado Privado", "Carga (VA)": 500, "Fase": "B"},
        {"Circuito": "C3 - Contactos Recámaras", "Carga (VA)": 1200, "Fase": "A"},
        {"Circuito": "C4 - Contactos Sala/Comedor", "Carga (VA)": 1200, "Fase": "B"},
        {"Circuito": "C5 - A/C Minisplit Recámara", "Carga (VA)": 950, "Fase": "A"},
        {"Circuito": "C6 - Horno Microondas", "Carga (VA)": 1200, "Fase": "B"},
        {"Circuito": "C7 - Lavasecadora", "Carga (VA)": 1600, "Fase": "A"},
    ]

    edited_df = st.data_editor(
        default_circuits,
        column_config={
            "Circuito": st.column_config.TextColumn("Nombre / Descripción", required=True),
            "Carga (VA)": st.column_config.NumberColumn("Potencia (VA)", min_value=0, max_value=10000, step=100),
            "Fase": st.column_config.SelectboxColumn("Asignación de Fase", options=["A", "B", "AB (220V)"], required=True)
        },
        num_rows="dynamic",
        use_container_width=True
    )

    # Convertir datos editados a lista interna para el cálculo
    formatted_circuits = [
        {"name": row["Circuito"], "va": float(row["Carga (VA)"]), "phase": row["Fase"]}
        for row in edited_df
    ]

    # --- Ejecutar Cálculo de Balanceo ---
    balance = calculate_phase_balance(formatted_circuits)

    st.markdown("---")
    st.subheader("2. Resultados del Balanceo de Fases")

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)

    with col_b1:
        st.metric("Carga Fase A", f"{balance['va_phase_a']:.0f} VA", f"{(balance['va_phase_a']/120):.1f} A @ 120V")
    with col_b2:
        st.metric("Carga Fase B", f"{balance['va_phase_b']:.0f} VA", f"{(balance['va_phase_b']/120):.1f} A @ 120V")
    with col_b3:
        st.metric("Carga Total Instalada", f"{balance['total_va']:.0f} VA")
    with col_b4:
        st.metric(
            "Desbalance de Fases", 
            f"{balance['unbalance_pct']}%",
            delta="Límite NOM: < 15%",
            delta_color="inverse" if balance['unbalance_pct'] > 15 else "normal"
        )

    # Mensajes de Diagnóstico
    if balance["status"] == "CRÍTICO":
        st.error(f"🚨 **DESBALANCE CRÍTICO:** {balance['message']}")
    elif balance["status"] == "ACEPTABLE":
        st.warning(f"⚠️ **DESBALANCE ACEPTABLE:** {balance['message']}")
    else:
        st.success(f"✅ **SISTEMA BALANCEADO:** {balance['message']}")

# ==========================================
# PESTAÑA 7: DIMENSIONAMIENTO SOLAR (ART. 690)
# ==========================================
with tab_solar:
    st.header("☀️ Dimensionamiento de Sistema Fotovoltaico Interconectado (NOM-001 Art. 690)")
    st.markdown("Cálculo de arreglos fotovoltaicos, cobertura energética y requerimientos de protección AC conforme a normativa CFE / NOM.")

    st.subheader("1. Parámetros de Consumo y Radiación")

    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        monthly_kwh = st.number_input(
            "Consumo Promedio Mensual (kWh/mes):",
            min_value=50.0,
            max_value=10000.0,
            value=450.0,
            step=50.0,
            help="Consumo tomado del recibo de CFE (promedio bimestral / 2 o promedio mensual)."
        )

    with col_s2:
        hsp_input = st.number_input(
            "Horas Solar Pico (HSP - kWh/m²/día):",
            min_value=3.0,
            max_value=7.0,
            value=5.2,
            step=0.1,
            help="Promedio para la región (ej. Monterrey / ZMM ~ 5.0 - 5.5 HSP)."
        )

    with col_s3:
        panel_power = st.selectbox(
            "Potencia del Panel Solar (Wp):",
            [450, 500, 550, 580, 600, 650],
            index=2,  # 550Wp por defecto
            help="Potencia nominal del módulo fotovoltaico a seleccionar."
        )

    # Parámetros avanzados en expansor opcional
    with st.expander("⚙️ Parámetros Avanzados del Sistema (Eficiencia y Pérdidas)"):
        efficiency_factor = st.slider(
            "Factor de Rendimiento Global (Performance Ratio):",
            min_value=0.70,
            max_value=0.90,
            value=0.82,
            step=0.01,
            help="Considera pérdidas por temperatura en celdas, suciedad, inversores y caída de tensión en DC/AC (NOM recomienda 0.80 - 0.85)."
        )

    # --- Ejecutar Cálculo Solar ---
    solar_res = calculate_solar_pv_system(
        monthly_consumption_kwh=monthly_kwh,
        panel_power_wp=panel_power,
        hsp=hsp_input,
        system_efficiency=efficiency_factor
    )

    if solar_res:
        st.markdown("---")
        st.subheader("2. Resultados del Arreglo Fotovoltaico")

        col_r1, col_r2, col_r3, col_r4 = st.columns(4)

        with col_r1:
            st.metric("Número de Paneles", f"{solar_res['num_panels']} Módulos", f"{panel_power} Wp c/u")
        with col_r2:
            st.metric("Capacidad Instalada", f"{solar_res['installed_capacity_kwp']} kWp")
        with col_r3:
            st.metric("Generación Estimada", f"{solar_res['monthly_generation_kwh']} kWh/mes")
        with col_r4:
            st.metric(
                "Cobertura Energética", 
                f"{solar_res['coverage_pct']}%",
                delta="Meta: ~100%"
            )

        st.markdown("---")
        st.subheader("3. Especificaciones de Protección AC e Interconexión (NOM-001 Art. 690-8)")

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.info(
                f"⚡ **Corriente Salida AC Inversor (220V 2F):** {solar_res['ac_current_220v']} A\n\n"
                f"🛡️ **Protección Mínima ITM AC (125% Cont.):** {solar_res['min_ac_protection_amps']} A\n\n"
                f"📌 **Interruptor Sugerido:** ITM 2P-{math.ceil(solar_res['min_ac_protection_amps'] / 5) * 5}A en Tablero Principal."
            )

        with col_p2:
            st.warning(
                "📋 **Criterios de Cumplimiento Normativo (NOM-001 / CFE):**\n"
                "- El interruptor de interconexión debe ser de acceso exclusivo para mantenimiento.\n"
                "- Calibre de conductores AC dimensionado al 125% de la corriente nominal del inversor.\n"
                "- Inversor con certificación **UL 1741 / IEEE 1547** para desconexión anti-isla."
            )

        # --- SECCIÓN 4: AUDITORÍA DE ESPACIO Y BATERÍAS ---
        st.markdown("---")
        st.subheader("4. Auditoría de Espacio en Azotea y Respaldo por Baterías (NOM Art. 706)")

        col_sub1, col_sub2 = st.columns(2)

        with col_sub1:
            st.markdown("**📐 Levantamiento Físico en Azotea:**")
            area_available = st.number_input(
                "Área útil disponible en Azotea (m²):", 
                min_value=0.0, 
                value=35.0, 
                step=5.0,
                help="Espacio plano o inclinado sin sombras de tinacos, pretiles o A/C."
            )
            
            # Área requerida estimada (2.6 m² aprox. por panel de 550Wp)
            required_area = solar_res["num_panels"] * 2.6
            
            st.write(f"• **Área requerida por los {solar_res['num_panels']} paneles:** {required_area:.1f} m²")
            if area_available >= required_area:
                st.success(f"✅ Espacio suficiente ({area_available - required_area:.1f} m² libres para pasillos de mantenimiento).")
            else:
                st.error(f"⚠️ Espacio insuficiente en azotea. Faltan {required_area - area_available:.1f} m² o se requiere usar módulos de mayor potencia.")

        with col_sub2:
            st.markdown("**🔋 Sistema de Almacenamiento con Baterías (Opcional):**")
            use_batteries = st.checkbox("¿Requiere Respaldo en Cargas Críticas / Sistema Híbrido?")

            if use_batteries:
                # Verificar si existen datos calculados previamente en session_state
                suggested_critical_va = 1500.0
                if 'calculated_circuits' in st.session_state and st.session_state['calculated_circuits']:
                    # Sumar solo circuitos marcados o cargas relevantes (ej. A/C + Refrigerador/Contactos)
                    suggested_critical_va = sum(c['Carga (VA)'] for c in st.session_state['calculated_circuits'] if 'A/C' in c['Circuito'] or 'Contactos' in c['Circuito'])
                    if suggested_critical_va == 0:
                        suggested_critical_va = sum(c['Carga (VA)'] for c in st.session_state['calculated_circuits']) / 2

                critical_va = st.number_input(
                    "Carga Crítica a Respaldar (VA):", 
                    min_value=100.0, 
                    value=float(suggested_critical_va), 
                    step=100.0, 
                    help="Carga vinculada a la auditoría anterior o ingresada manualmente."
                )
                
                backup_hrs = st.slider("Horas de Autonomía Requeridas:", min_value=1, max_value=24, value=6)
                bat_type = st.selectbox("Tecnología de Batería:", ["Litio (LiFePO4) - DoD 85%", "Plomo-Ácido / GEL - DoD 50%"])

                # Lógica interna de cálculo de baterías
                dod = 0.85 if "Litio" in bat_type else 0.50
                required_wh = (critical_va * backup_hrs) / (dod * 0.90)
                capacity_ah_48v = required_wh / 48.0
                num_modules = math.ceil((required_wh / 1000.0) / 4.8)  # Módulos estándar de 4.8 kWh (48V 100Ah)

                st.info(
                    f"📦 **Banco de Baterías Requerido (48V DC):**\n"
                    f"- **Energía Total Requerida:** {required_wh / 1000.0:.2f} kWh ({capacity_ah_48v:.1f} Ah @ 48V)\n"
                    f"- **Módulos Recomendados:** {num_modules} Batería(s) de Litio 48V 100Ah (4.8 kWh c/u)\n"
                    f"- **Profundidad de Descarga (DoD):** {int(dod * 100)}%"
                )
# cambio

