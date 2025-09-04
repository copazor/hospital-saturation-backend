from typing import Optional

def calculate_medico_quirurgico_score(
    scenario: str,
    hospitalized_patients: int,
    esi_c2_patients: int,
    reanimador_patients: int,
    critical_patient_protocol: str, # "none", "amarilla", "roja"
    waiting_72_hours_patients: int,
    sar_active: bool = False,
    sar_patients: int = 0
) -> dict:
    score = 0
    sar_activated = False
    forced_red_key = False

    print(f"DEBUG: Inicio de cálculo. Score inicial: {score}")
    print(f"DEBUG: Datos recibidos: scenario={scenario}, hospitalized_patients={hospitalized_patients}, esi_c2_patients={esi_c2_patients}, reanimador_patients={reanimador_patients}, critical_patient_protocol={critical_patient_protocol}, waiting_72_hours_patients={waiting_72_hours_patients}, sar_active={sar_active}, sar_patients={sar_patients}")
    print(f"DEBUG: Tipo de sar_active: {type(sar_active)}, Valor de sar_active: {sar_active}")
    print(f"DEBUG: Tipo de sar_patients: {type(sar_patients)}, Valor de sar_patients: {sar_patients}")

    # Lógica de cálculo del score para el protocolo Médico/Quirúrgico

    # Criterios para Número de pacientes hospitalizados
    if scenario == "capacidad_reducida":
        if hospitalized_patients >= 60:
            score += 3
            print(f"DEBUG: Hospitalizados (>=60): +3. Score actual: {score}")
        elif hospitalized_patients >= 55:
            score += 2
            print(f"DEBUG: Hospitalizados (>=55): +2. Score actual: {score}")
        elif hospitalized_patients >= 50:
            score += 1
            print(f"DEBUG: Hospitalizados (>=50): +1. Score actual: {score}")
    elif scenario == "capacidad_completa":
        if hospitalized_patients >= 65:
            score += 3
            print(f"DEBUG: Hospitalizados (>=65): +3. Score actual: {score}")
        elif hospitalized_patients >= 60:
            score += 2
            print(f"DEBUG: Hospitalizados (>=60): +2. Score actual: {score}")
        elif hospitalized_patients >= 55:
            score += 1
            print(f"DEBUG: Hospitalizados (>=55): +1. Score actual: {score}")

    # Criterios para Número total de ESI C2
    if esi_c2_patients >= 30:
        score += 2
        print(f"DEBUG: ESI C2 (>=30): +2. Score actual: {score}")
    elif esi_c2_patients >= 15:
        score += 1
        print(f"DEBUG: ESI C2 (>=15): +1. Score actual: {score}")

    # Criterios para Sobresaturación Aguda de Reanimador (SAR)
    if sar_active:
        sar_activated = True
        print(f"DEBUG: SAR activo. sar_patients: {sar_patients}")
        if scenario == "capacidad_reducida":
            if sar_patients >= 8: # Nivel 2: 8 o más pacientes (capacidad reducida)
                score += 7
                forced_red_key = True
                print(f"DEBUG: SAR Nivel 2 (Cap. Reducida): +7. Score actual: {score}. Clave Roja forzada.")
            elif sar_patients >= 6: # Nivel 1: 6 a 7 pacientes (capacidad reducida)
                score += 5
                print(f"DEBUG: SAR Nivel 1 (Cap. Reducida): +5. Score actual: {score}")
        elif scenario == "capacidad_completa":
            if sar_patients >= 10: # Nivel 2: 10 o más pacientes (capacidad completa)
                score += 7
                forced_red_key = True
                print(f"DEBUG: SAR Nivel 2 (Cap. Completa): +7. Score actual: {score}. Clave Roja forzada.")
            elif sar_patients >= 8: # Nivel 1: 8 a 9 pacientes (capacidad completa)
                score += 5
                print(f"DEBUG: SAR Nivel 1 (Cap. Completa): +5. Score actual: {score}")
    
    # Criterios para Número de pacientes en Reanimador (solo si SAR no está activo)
    if not sar_activated:
        print(f"DEBUG: SAR no activo. Evaluando pacientes en Reanimador: {reanimador_patients}")
        if scenario == "capacidad_reducida":
            if reanimador_patients >= 8: # Nivel 2: 8 o más pacientes (capacidad reducida)
                score += 7
                forced_red_key = True
                print(f"DEBUG: Pacientes en Reanimador (Cap. Reducida) >=8: +7. Score actual: {score}. Clave Roja forzada.")
            elif reanimador_patients >= 6: # Nivel 1: 6 a 7 pacientes (capacidad reducida)
                score += 5
                print(f"DEBUG: Pacientes en Reanimador (Cap. Reducida) 6-7: +5. Score actual: {score}")
            elif reanimador_patients >= 4: # 4 a 5 pacientes
                score += 2
                print(f"DEBUG: Pacientes en Reanimador (Cap. Reducida) 4-5: +2. Score actual: {score}")
        elif scenario == "capacidad_completa":
            if reanimador_patients >= 10: # Nivel 2: 10 o más pacientes (capacidad completa)
                score += 7
                forced_red_key = True
                print(f"DEBUG: Pacientes en Reanimador (Cap. Completa) >=10: +7. Score actual: {score}. Clave Roja forzada.")
            elif reanimador_patients >= 8: # Nivel 1: 8 a 9 pacientes (capacidad completa)
                score += 5
                print(f"DEBUG: Pacientes en Reanimador (Cap. Completa) 8-9: +5. Score actual: {score}")
            elif reanimador_patients >= 6: # 6 a 7 pacientes
                score += 2
                print(f"DEBUG: Pacientes en Reanimador (Cap. Completa) 6-7: +2. Score actual: {score}")
    else:
        print("DEBUG: Pacientes en Reanimador no evaluado porque SAR está activo.")


    # Criterios para Protocolo paciente crítico
    if critical_patient_protocol == "amarilla":
        score += 1
        print(f"DEBUG: Protocolo Paciente Crítico (Amarilla): +1. Score actual: {score}")
    elif critical_patient_protocol == "roja":
        score += 2
        print(f"DEBUG: Protocolo Paciente Crítico (Roja): +2. Score actual: {score}")

    # Criterios para Número de pacientes en espera de cama hospitalaria por 72 o más horas
    if waiting_72_hours_patients >= 12:
        score += 2
        print(f"DEBUG: Espera 72+ horas (>=12): +2. Score actual: {score}")
    elif waiting_72_hours_patients >= 6:
        score += 1
        print(f"DEBUG: Espera 72+ horas (>=6): +1. Score actual: {score}")

    # Determinación del nivel de alerta
    alert_level = ""
    if forced_red_key:
        alert_level = "Roja"
        print(f"DEBUG: Clave Roja forzada por SAR Nivel 2.")
    elif score <= 1:
        alert_level = "Verde"
    elif score >= 2 and score <= 3:
        alert_level = "Amarilla"
    elif score >= 4 and score <= 6:
        alert_level = "Naranja"
    else:
        alert_level = "Roja"
    
    print(f"DEBUG: Cálculo finalizado. Score final: {score}, Nivel de Alerta: {alert_level}")

    return {"score": score, "alert_level": alert_level}

def calculate_paciente_critico_alert(
    ventilated_patients_outside_uci: int
) -> str:
    alert_level = "Verde"
    if ventilated_patients_outside_uci >= 6:
        alert_level = "Roja"
    elif ventilated_patients_outside_uci >= 4:
        alert_level = "Amarilla"
    return alert_level

def get_medico_quirurgico_measures(alert_level: str) -> list:
    measures = []

    # Medidas comunes o acumulativas
    if alert_level == "Verde":
        measures.append("Estado de funcionamiento habitual del hospital. Mantener vigilancia constante de indicadores de ocupación y flujo de pacientes.")
    
    if alert_level in ["Amarilla", "Naranja", "Roja"]:
        measures.extend([
            "Equipo UEA (Jefe de turno y Urgenciólogo Gestor) realiza búsqueda activa de egresos potenciales.",
            "Búsqueda activa de pacientes que cumplan criterios para derivación a camas en extrasistema, vía UGCC.",
            "En la Reunión de camas los representantes de los servicios clínicos deben contar con información clara y actualizada sobre los potenciales movimientos en sus respectivas unidades.",
            "Indiferenciación de camas básicas del Block Adulto, independiente de la especialidad a cargo (posibilidad pacientes ectópicos).",
            "Permitir traslado de pacientes básicos desde UEA a camas básicas del CR de la Mujer (Pensionado u Oncoginecología) según disponibilidad.",
            "Promover traslado de pacientes en proceso de alta a unidades hospitalarias alternativas para generar espacio asistencial (tiempo de ejecución: 2 horas).",
            "Notificación a Unidades de Apoyo para favorecer egreso oportuno de pacientes hospitalizados (priorización de recetas, imágenes, coordinación de ambulancia/traslado).",
        ])

    if alert_level == "Naranja":
        measures.extend([
            "Traslado a Recuperación Central de pacientes con patología quirúrgica en espera de pabellón. Máximo: 4 pacientes en Clave Naranja.",
            "Traslado a Recuperación Central de pacientes post procedimiento angiográfico/coronariografía derivados desde otros centros, que se encuentren estables y en espera de rescate a su centro de origen.",
            "Suspender recepción de traslados de pacientes a través de la Unidad de Gestión en aquellos casos cuya patología no requiera resolución tiempo dependiente.",
            "Ingreso a Hospitalización Domiciliaria de pacientes quirúrgicos básicos, estables y de larga estadía (>72h sin cirugía programada en las próximas 24 horas).",
            "Generación de cupos en unidades hospitalarias (al menos 10% de dotación total de camas para recepción de pacientes de UEA).",
        ])

    if alert_level == "Roja":
        measures.extend([
            "Traslado a Recuperación Central de pacientes con patología quirúrgica en espera de pabellón. Máximo: 6 pacientes en Clave Roja.",
            "Traslado a Recuperación Central de pacientes post procedimiento angiográfico/coronariografía derivados desde otros centros, que se encuentren estables y en espera de rescate a su centro de origen.",
            "Suspender recepción de traslados de pacientes a través de la Unidad de Gestión en aquellos casos cuya patología no requiera resolución tiempo dependiente.",
            "Ingreso a Hospitalización Domiciliaria de pacientes quirúrgicos básicos, estables y de larga estadía (>72h sin cirugía programada en las próximas 24 horas).",
            "Coordinación de ingreso de pacientes supernumerarios a distintos servicios clínicos (hasta 2 a Traumatología, 2 a Cirugía, 1 a Neurología, 1 a Medicina), con un tiempo máximo de 60 minutos para concretar el traslado.",
            
            "Generación de cupos en unidades hospitalarias (al menos 15% de dotación total de camas para recepción de pacientes de UEA).",
            "En caso de no lograr el objetivo de generación de cupos (15%), la Unidad de Gestión de Pacientes implementa búsqueda activa de egresos con Comité de Camas Multidisciplinario.",
            "Suspender cirugías electivas que no cuentan con cama asignada.",
            "Jefes de equipos quirúrgicos reorganizan programación, priorizando casos de pacientes hospitalizados en espera de cirugía.",
            "Suspensión transitoria de ingresos electivos a unidades de Medicina, Neurología, Psiquiatría y Unidad Coronaria para optimizar camas para pacientes desde la Unidad de Emergencia Adulto.",
            "Entrega virtual de pacientes básicos estables de UEA a unidades hospitalarias (vía planilla estandarizada o sistema electrónico) si la entrega telefónica no se concreta en 15 minutos.",
            
        ])
    
    # Medida específica de contingencia local
    if alert_level == "Amarilla":
        measures.append("Cada unidad clínica y de apoyo implementa sus medidas locales de contingencia en Clave Amarilla.")
    elif alert_level == "Naranja":
        measures.append("Cada unidad clínica y de apoyo implementa sus medidas locales de contingencia en Clave Naranja.")
    elif alert_level == "Roja":
        measures.append("Cada unidad clínica y de apoyo implementa sus medidas locales de contingencia en Clave Roja.")

    return measures

def get_medico_quirurgico_reevaluation_note(alert_level: str) -> Optional[str]:
    if alert_level == "Verde":
        return "La reevaluación de Clave Verde se realiza a las 08:00 y 20:00 horas. Solo se puede activar antes en caso de un evento de Sobresaturación Aguda del Reanimador."
    elif alert_level == "Amarilla":
        return "La reevaluación de Clave Amarilla se realiza a las 08:00 y 20:00 horas. Solo se puede activar antes en caso de un evento de Sobresaturación Aguda del Reanimador."
    elif alert_level == "Naranja":
        return "La reevaluación de Clave Naranja se realiza a las 4 horas desde su activación. Se determina si persiste la condición o si corresponde elevar la alerta a Clave Roja. Solo se puede activar antes en caso de un evento de Sobresaturación Aguda del Reanimador."
    elif alert_level == "Roja":
        return "La reevaluación de Clave Roja se realiza a las 4 horas desde su activación. Se determina si persiste la condición o si corresponde desescalar la alerta."
    return None