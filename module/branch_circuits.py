import io
import math
from module.ampacity import calculate_adjusted_ampacity
from module.voltage_drop import calculate_voltage_drop
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def calculate_branch_circuits(
    area_m2: float = 0.0, 
    custom_appliances_va: float = 0.0, 
    is_existing_survey: bool = False,
    lighting_real_va: float = 0.0,
    voltage: float = 120.0,
    feeder_length_m: float = 10.0,
    custom_light_circuits: int = 1,
    custom_plug_circuits: int = 1,
    custom_dedicated_circuits: int = 0
) -> dict:
    """
    Calcula circuitos derivados, factor de demanda, alimentador principal CFE 
    y dimensiona el centro de cargas según NOM-001-SEDE / NEC.
    Soporta modo Obra Nueva y Levantamiento Real con distribución por confort.
    """
    if is_existing_survey:
        # MODO LEVANTAMIENTO REAL
        lighting_load_va = lighting_real_va
        small_appliances_va = 0.0
        laundry_va = 0.0
        general_connected_va = lighting_real_va
    else:
        # MODO PROYECTO / OBRA NUEVA (NOM-001)
        lighting_load_va = area_m2 * 33.0
        small_appliances_va = 2 * 1500.0  # 3,000 VA (Cocina)
        laundry_va = 1500.0              # 1,500 VA (Lavandería)
        general_connected_va = lighting_load_va + small_appliances_va + laundry_va

    total_connected_va = general_connected_va + custom_appliances_va

    # Factor de Demanda (Tabla 220.42) sobre Carga General
    if general_connected_va <= 3000.0:
        demanded_general_va = general_connected_va
    elif general_connected_va <= 120000.0:
        demanded_general_va = 3000.0 + ((general_connected_va - 3000.0) * 0.35)
    else:
        demanded_general_va = 3000.0 + (117000.0 * 0.35) + ((general_connected_va - 120000.0) * 0.25)

    total_demanded_va = demanded_general_va + custom_appliances_va

    # Cálculo de Corriente del Alimentador Principal (CFE -> Centro de Cargas)
    # Factor de potencia estimado de 0.90
    load_amps = total_demanded_va / (voltage * 0.90) if voltage > 0 else 0.0
    design_amps = load_amps * 1.25  # 125% Carga continua / factor de seguridad

    # Selección de Calibre de Alimentador y Verificación de Caída de Voltaje
    awg_candidates = ["12", "10", "8", "6", "4", "2", "1/0"]
    selected_awg = "8"
    feeder_vd_percent = 0.0

    for awg in awg_candidates:
        amp_res = calculate_adjusted_ampacity("cobre", awg, "75C", ambient_temp_c=30, num_conductors=3)
        if amp_res["adjusted_ampacity"] >= design_amps:
            vd_res = calculate_voltage_drop("cobre", awg, load_amps, feeder_length_m, voltage, "Monofásico 1Ø (2 hilos)")
            if vd_res["v_drop_percent"] <= 3.0:
                selected_awg = awg
                feeder_vd_percent = vd_res["v_drop_percent"]
                break

    # Interruptor Principal (Breaker) Comercial
    standard_breakers = [15, 20, 30, 40, 50, 60, 70, 80, 100]
    main_breaker = standard_breakers[-1]
    for b in standard_breakers:
        if b >= design_amps:
            main_breaker = b
            break

    # Conteo de Polos / Circuitos Derivados
    if is_existing_survey:
        # Distribución por Zonas / Confort definida por el usuario
        total_circuits = custom_light_circuits + custom_plug_circuits + custom_dedicated_circuits
        min_lighting_circuits = custom_light_circuits
    else:
        # Mínimo normativo automático para obra nueva
        va_per_15a_circuit = voltage * 15.0 * 0.8
        min_lighting_circuits = math.ceil(lighting_load_va / va_per_15a_circuit) if lighting_load_va > 0 else 1
        total_circuits = min_lighting_circuits + 2 + 1  # Alumbrado + 2 Cocina + 1 Lavandería

    return {
        "is_existing_survey": is_existing_survey,
        "lighting_load_va": round(lighting_load_va, 2),
        "small_appliances_va": round(small_appliances_va, 2),
        "laundry_va": round(laundry_va, 2),
        "general_connected_va": round(general_connected_va, 2),
        "custom_appliances_va": round(custom_appliances_va, 2),
        "total_connected_va": round(total_connected_va, 2),
        "demanded_general_va": round(demanded_general_va, 2),
        "total_demanded_va": round(total_demanded_va, 2),
        "load_amps": round(load_amps, 2),
        "design_amps": round(design_amps, 2),
        "recommended_feeder_awg": selected_awg,
        "main_breaker": main_breaker,
        "feeder_vd_percent": feeder_vd_percent,
        "lighting_circuits": min_lighting_circuits,
        "total_circuits": total_circuits,
        "custom_light_circuits": custom_light_circuits,
        "custom_plug_circuits": custom_plug_circuits,
        "custom_dedicated_circuits": custom_dedicated_circuits
    }

def audit_service_entrance_health(
    main_protection_type: str,    # "Fusible" o "ITM"
    main_protection_amps: float,  # ej. 30, 40, 50
    existing_wire_awg: int,       # ej. 10, 8, 6
    total_continuous_amps: float  # Corriente continua calculada
):
    """
    Evalúa la salud de la acometida existente según criterios NOM-001 / NEC.
    """
    # 1. Ampacidad del cable existente (a 75°C cobre)
    ampacity_map = {14: 20, 12: 25, 10: 35, 8: 50, 6: 65, 4: 85}
    wire_capacity = ampacity_map.get(existing_wire_awg, 30)

    # 2. Regla del 80% para carga continua
    safe_continuous_limit = main_protection_amps * 0.80
    load_percentage = (total_continuous_amps / main_protection_amps) * 100

    # 3. Diagnóstico de Riesgos
    risks = []
    status = "OK"  # OK, ADVERTENCIA, PELIGRO

    # Riesgo A: Fatiga Térmica por regla del 80%
    if total_continuous_amps > safe_continuous_limit:
        status = "ADVERTENCIA"
        risks.append(
            f"Carga continua ({total_continuous_amps:.1f}A) supera el 80% de la capacidad "
            f"nominal ({safe_continuous_limit:.1f}A). Riesgo de disparo en falso o degradación térmica."
        )

    # Riesgo B: Protección supera la capacidad del cable
    if main_protection_amps > wire_capacity:
        status = "PELIGRO"
        risks.append(
            f"Protección ({main_protection_amps}A) es mayor que la capacidad del cable "
            f"Calibre {existing_wire_awg} AWG ({wire_capacity}A). ¡Riesgo de sobrecalentamiento e incendio del cableado!"
        )

    # Riesgo C: Uso de Fusibles con Cargas Continuas/Inductivas
    if main_protection_type.upper() == "FUSIBLE":
        if status != "PELIGRO":
            status = "ADVERTENCIA"
        risks.append(
            "El uso de fusibles de cartucho genera resistencia por falso contacto en mordazas "
            "y degradación progresiva del listón. Se recomienda reemplazar por Interruptor Termomagnético (ITM)."
        )

    return {
        "status": status,
        "load_percentage": round(load_percentage, 1),
        "safe_limit_amps": safe_continuous_limit,
        "risks": risks,
        "recommended_action": (
            f"Migrar a ITM de 40A con Alimentador Calibre 8 AWG."
            if status != "OK" else "Acometida en parámetros óptimos."
        )
    }

def calculate_phase_balance(circuits_data: list):
    """
    Recibe una lista de diccionarios con la estructura:
    [{'name': 'C1 - Alumbrado', 'va': 1200, 'phase': 'A'}, ...]
    
    Retorna el balance de cargas entre Fase A y Fase B.
    """
    va_phase_a = sum(c['va'] for c in circuits_data if c['phase'] == 'A')
    va_phase_b = sum(c['va'] for c in circuits_data if c['phase'] == 'B')
    va_220v = sum(c['va'] for c in circuits_data if c['phase'] == 'AB')  # Cargas a 220V (usan ambas fases)

    # Las cargas a 220V aportan la mitad de su potencia a cada fase para el balance
    total_phase_a = va_phase_a + (va_220v / 2)
    total_phase_b = va_phase_b + (va_220v / 2)
    total_system_va = total_phase_a + total_phase_b

    max_phase = max(total_phase_a, total_phase_b)
    min_phase = min(total_phase_a, total_phase_b)

    # Cálculo del desbalance en porcentaje (%)
    if max_phase > 0:
        unbalance_pct = ((max_phase - min_phase) / max_phase) * 100
    else:
        unbalance_pct = 0.0

    # Estado según la Norma (< 10% Excelente, 10-15% Aceptable, > 15% Desbalanceado)
    if unbalance_pct <= 10.0:
        status = "EXCELENTE"
        msg = "Las fases están perfectamente equilibradas conforme a NOM-001."
    elif unbalance_pct <= 15.0:
        status = "ACEPTABLE"
        msg = "Desbalance dentro del límite aceptable (<15%), pero optimizable."
    else:
        status = "CRÍTICO"
        msg = f"Desbalance excesivo ({unbalance_pct:.1f}%). Riesgo de sobrecalentamiento e incremento de corriente en el Neutro."

    return {
        "va_phase_a": total_phase_a,
        "va_phase_b": total_phase_b,
        "total_va": total_system_va,
        "unbalance_pct": round(unbalance_pct, 1),
        "status": status,
        "message": msg
    }

def calculate_solar_pv_system(
    monthly_consumption_kwh: float,
    panel_power_wp: float = 550.0,
    hsp: float = 5.2,
    system_efficiency: float = 0.82
):
    """
    Calcula el dimensionamiento de un sistema fotovoltaico interconectado a la red (SFVI)
    según NOM-001-SEDE Art. 690.
    
    Parameters:
    - monthly_consumption_kwh: Consumo promedio mensual en kWh.
    - panel_power_wp: Potencia nominal del panel solar en Watts pico (ej. 550 Wp).
    - hsp: Horas Solar Pico promedio de la zona (kWh/m²/día).
    - system_efficiency: Factor de rendimiento global (PR - Performance Ratio, ej. 0.82).
    """
    if monthly_consumption_kwh <= 0 or panel_power_wp <= 0:
        return None

    # Consumo promedio diario (considerando mes de 30 días)
    daily_kwh = monthly_consumption_kwh / 30.0

    # Carga fotovoltaica requerida al día considerando pérdidas del sistema
    daily_energy_required_kwh = daily_kwh / system_efficiency

    # Potencia total en Watts pico (Wp) requerida
    total_power_required_wp = (daily_energy_required_kwh / hsp) * 1000.0

    # Número de paneles solares (redondeado al entero superior)
    num_panels = math.ceil(total_power_required_wp / panel_power_wp)

    # Potencia real instalada en kWp
    installed_capacity_kwp = (num_panels * panel_power_wp) / 1000.0

    # Generación estimada mensual (kWh/mes)
    estimated_monthly_generation_kwh = installed_capacity_kwp * hsp * 30.0 * system_efficiency

    # Porcentaje de cobertura del consumo
    coverage_pct = (estimated_monthly_generation_kwh / monthly_consumption_kwh) * 100.0

    # Dimensionamiento de Protección Principal AC (NOM-001 Art. 690-8)
    # Corriente máxima de salida AC estimada a 220V 2F
    ac_current_220v = (installed_capacity_kwp * 1000.0) / (220.0 * 0.95)  # FP ~0.95
    # Factor de seguridad NOM Art. 690 (125% continuo)
    min_ac_protection_amps = ac_current_220v * 1.25

    return {
        "daily_kwh": round(daily_kwh, 2),
        "total_power_wp": round(total_power_required_wp, 1),
        "num_panels": num_panels,
        "installed_capacity_kwp": round(installed_capacity_kwp, 2),
        "monthly_generation_kwh": round(estimated_monthly_generation_kwh, 1),
        "coverage_pct": round(coverage_pct, 1),
        "ac_current_220v": round(ac_current_220v, 1),
        "min_ac_protection_amps": round(min_ac_protection_amps, 1)
    }

def calculate_battery_storage(
    critical_loads_va: float,
    backup_hours: float,
    battery_type: str = "Litio (LiFePO4)",
    system_voltage: float = 48.0
):
    """
    Calcula la capacidad del banco de baterías según cargas críticas y horas de respaldo (NOM Art. 706).
    """
    # Profundidad de descarga (DoD) y eficiencia de conversión
    dod = 0.85 if "Litio" in battery_type else 0.50
    efficiency = 0.90

    # Energía total requerida en Wh
    required_wh = (critical_loads_va * backup_hours) / (dod * efficiency)
    
    # Capacidad en Ampere-hora (Ah) al voltaje del sistema
    capacity_ah = required_wh / system_voltage

    # Ejemplo comercial: Baterías de Litio 48V @ 100Ah (4.8 kWh c/u)
    single_battery_kwh = (system_voltage * 100) / 1000.0
    num_batteries = math.ceil((required_wh / 1000.0) / single_battery_kwh)

    return {
        "required_kwh": round(required_wh / 1000.0, 2),
        "capacity_ah": round(capacity_ah, 1),
        "num_batteries": num_batteries,
        "battery_type": battery_type,
        "dod_pct": int(dod * 100)
    }

def generate_pdf_audit_report(audit_data: dict, balance_data: dict, solar_data: dict = None) -> bytes:
    """
    Genera un informe técnico de auditoría y diseño eléctrico en formato PDF conforme a la NOM-001.
    Retorna los bytes del archivo PDF listo para su descarga.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=0
    )
    h2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E40AF'),
        spaceBefore=10,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#374151')
    )
    alert_style = ParagraphStyle(
        'Alert',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#DC2626') if audit_data.get('status') == 'PELIGRO' else colors.HexColor('#D97706')
    )

    story = []

    # --- Encabezado ---
    story.append(Paragraph("<b>DICTAMEN TÉCNICO DE AUDITORÍA Y DISEÑO ELÉCTRICO</b>", title_style))
    story.append(Paragraph("Norma Oficial Mexicana NOM-001-SEDE | Evaluación Residencial", body_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=15))

    # --- Resumen de Auditoría ---
    story.append(Paragraph("1. Diagnóstico de Salud de la Acometida", h2_style))
    
    audit_table_data = [
        ["Parámetro", "Valor Evaluado", "Criterio de Norma"],
        ["Corriente Demandada Sostenida", f"{audit_data.get('i_total', 0):.1f} A", "Carga Real de Operación"],
        ["Capacidad de Protección", f"{audit_data.get('main_amps', 0)} A", "Límite Continuo NOM (80%)"],
        ["Porcentaje de Carga", f"{audit_data.get('load_percentage', 0)}%", "< 80% Seguro / > 80% Riesgo Térmico"],
        ["Estado del Sistema", audit_data.get('status', 'N/A'), "Dictamen de Seguridad"]
    ]

    t_audit = Table(audit_table_data, colWidths=[180, 150, 200])
    t_audit.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(t_audit)
    story.append(Spacer(1, 10))

    # Riesgos y Recomendaciones
    story.append(Paragraph("<b>Hallazgos de Riesgo Térmico:</b>", body_style))
    for risk in audit_data.get('risks', []):
        story.append(Paragraph(f"• {risk}", alert_style))

    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>Acción Correctiva Sugerida:</b> {audit_data.get('recommended_action', 'N/A')}", body_style))
    story.append(Spacer(1, 15))

    # --- Cuadro de Balanceo de Fases ---
    if balance_data:
        story.append(Paragraph("2. Cuadro de Cargas y Balanceo de Fases (2F-1N)", h2_style))
        
        balance_table_data = [
            ["Fase A (VA)", "Fase B (VA)", "Carga Total (VA)", "Desbalance (%)", "Estado NOM"],
            [
                f"{balance_data.get('va_phase_a', 0):.0f} VA",
                f"{balance_data.get('va_phase_b', 0):.0f} VA",
                f"{balance_data.get('total_va', 0):.0f} VA",
                f"{balance_data.get('unbalance_pct', 0)}%",
                balance_data.get('status', 'N/A')
            ]
        ]
        t_balance = Table(balance_table_data, colWidths=[100, 100, 110, 110, 110])
        t_balance.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_balance)
        story.append(Spacer(1, 5))
        story.append(Paragraph(f"<i>Nota: {balance_data.get('message', '')}</i>", body_style))
        story.append(Spacer(1, 15))

    # --- Dimensión Solar (Si aplica) ---
    if solar_data:
        story.append(Paragraph("3. Dimensionamiento Fotovoltaico (NOM Art. 690)", h2_style))
        solar_table_data = [
            ["Potencia Instalada", "N° Paneles", "Generación Mensual", "Cobertura", "Protección AC"],
            [
                f"{solar_data.get('installed_capacity_kwp', 0)} kWp",
                f"{solar_data.get('num_panels', 0)} Módulos",
                f"{solar_data.get('monthly_generation_kwh', 0)} kWh/mes",
                f"{solar_data.get('coverage_pct', 0)}%",
                f"{solar_data.get('min_ac_protection_amps', 0)} A"
            ]
        ]
        t_solar = Table(solar_table_data, colWidths=[100, 90, 120, 100, 120])
        t_solar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_solar)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()