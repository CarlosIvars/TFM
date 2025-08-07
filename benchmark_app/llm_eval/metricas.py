import json
from django.db.models import Avg
from ..models import Agente, CasoUso, Evaluacion, RespuestaEvaluacion, Resultado

def fix_none(obj):
    # Recursivo: convierte None en 0 o '' o [] según el tipo
    if isinstance(obj, dict):
        return {k: fix_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [fix_none(x) for x in obj]
    elif obj is None:
        return 0
    return obj

def calcular_metricas():
    satisfaccion_text = "Nivel de satisfacción global del agente (1-5)"
    agentes = list(Agente.objects.all())
    casos = list(CasoUso.objects.all())

    # 1. Mapear casos por categoría
    categoria_dict = {}
    for caso in casos:
        cat = str(caso.categoria)  # forzamos a string
        if cat not in categoria_dict:
            categoria_dict[cat] = []
        categoria_dict[cat].append(caso)

    # 2. Acumular éxito por caso y agente (humanos y LLM)
    success_counts_hum = {}
    success_counts_llm = {}

    respuestas_hum = RespuestaEvaluacion.objects.filter(
        evaluacion__tipo='humano'
    ).exclude(pregunta__texto=satisfaccion_text).select_related(
        'evaluacion__resultado__agente', 'pregunta__caso_uso'
    )
    respuestas_llm = RespuestaEvaluacion.objects.filter(
        evaluacion__tipo='llm'
    ).exclude(pregunta__texto=satisfaccion_text).select_related(
        'evaluacion__resultado__agente', 'pregunta__caso_uso'
    )

    for resp in respuestas_hum:
        agente_id = resp.evaluacion.resultado.agente_id
        caso_id = resp.pregunta.caso_uso_id
        key = (caso_id, agente_id)
        if key not in success_counts_hum:
            success_counts_hum[key] = {"si": 0, "total": 0}
        success_counts_hum[key]["total"] += 1
        if resp.valor.strip().lower() == "si":
            success_counts_hum[key]["si"] += 1

    for resp in respuestas_llm:
        agente_id = resp.evaluacion.resultado.agente_id
        caso_id = resp.pregunta.caso_uso_id
        key = (caso_id, agente_id)
        if key not in success_counts_llm:
            success_counts_llm[key] = {"si": 0, "total": 0}
        success_counts_llm[key]["total"] += 1
        if resp.valor.strip().lower() == "si":
            success_counts_llm[key]["si"] += 1

    # 3. Desempeño por categoría (promedio)
    cat_labels = []
    cat_hum_data = []
    cat_llm_data = []
    for cat, casos_cat in categoria_dict.items():
        hum_tot, hum_si = 0, 0
        llm_tot, llm_si = 0, 0
        for caso in casos_cat:
            for agente in agentes:
                key = (caso.id, agente.id)
                if key in success_counts_hum:
                    hum_tot += success_counts_hum[key]["total"]
                    hum_si += success_counts_hum[key]["si"]
                if key in success_counts_llm:
                    llm_tot += success_counts_llm[key]["total"]
                    llm_si += success_counts_llm[key]["si"]
        cat_labels.append(cat)
        cat_hum_data.append(round((hum_si/hum_tot)*100, 2) if hum_tot > 0 else 0.0)
        cat_llm_data.append(round((llm_si/llm_tot)*100, 2) if llm_tot > 0 else 0.0)

    categorias_data = {
        "labels_json": json.dumps(cat_labels, ensure_ascii=False),
        "hum_data_json": json.dumps(cat_hum_data),
        "llm_data_json": json.dumps(cat_llm_data),
        "categorias": cat_labels
    }

    # 4. Desempeño por agente y caso de uso, agrupado por categoría (para las gráficas grandes)
    performance_grouped_by_cat = {}
    for cat, casos_cat in categoria_dict.items():
        agent_labels = [str(a.nombre) for a in agentes]
        datasets = []
        colors = [
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 99, 132, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(100, 100, 100, 0.7)',
        ]
        color_idx = 0
        for caso in casos_cat:
            color = colors[color_idx % len(colors)]
            border_color = color.replace('0.7', '1')
            color_idx += 1

            # Datos por agente (humano/llm)
            data_hum = []
            data_llm = []
            for agente in agentes:
                key = (caso.id, agente.id)
                val_hum = val_llm = 0.0
                if key in success_counts_hum and success_counts_hum[key]['total'] > 0:
                    val_hum = (success_counts_hum[key]['si'] / success_counts_hum[key]['total']) * 100.0
                if key in success_counts_llm and success_counts_llm[key]['total'] > 0:
                    val_llm = (success_counts_llm[key]['si'] / success_counts_llm[key]['total']) * 100.0
                data_hum.append(round(val_hum, 2))
                data_llm.append(round(val_llm, 2))

            datasets.append({
                "label": str(caso.titulo),
                "data": data_hum,
                "backgroundColor": color,
                "borderColor": border_color,
                "borderWidth": 2,
                "barPercentage": 0.45,
                "categoryPercentage": 0.9,
                "order": color_idx*2,
            })
            datasets.append({
                "label": str(caso.titulo),
                "data": data_llm,
                "backgroundColor": "rgba(255,255,255,0)",
                "borderColor": border_color,
                "borderWidth": 3,
                "barPercentage": 0.45,
                "categoryPercentage": 0.9,
                "borderDash": [6, 5],
                "order": color_idx*2+1,
            })
        performance_grouped_by_cat[cat] = {
            "labels_json": json.dumps(agent_labels, ensure_ascii=False),
            "datasets_json": json.dumps(fix_none(datasets), ensure_ascii=False)
        }

    # 5. Satisfacción global por agente (usuarios/llm)
    satisfaccion_hum = {}
    satisfaccion_llm = {}
    evaluaciones_hum = Evaluacion.objects.filter(tipo='humano').select_related('resultado__agente')
    for ev in evaluaciones_hum:
        if ev.puntaje_global is None:
            continue
        agente_id = ev.resultado.agente_id
        if agente_id not in satisfaccion_hum:
            satisfaccion_hum[agente_id] = {"suma": 0.0, "count": 0}
        satisfaccion_hum[agente_id]["suma"] += float(ev.puntaje_global)
        satisfaccion_hum[agente_id]["count"] += 1

    respuestas_sat_llm = RespuestaEvaluacion.objects.filter(
        evaluacion__tipo='llm', pregunta__texto=satisfaccion_text
    ).select_related('evaluacion__resultado__agente')
    for resp in respuestas_sat_llm:
        agente_id = resp.evaluacion.resultado.agente_id
        try:
            valor = float(resp.valor)
        except:
            continue
        if agente_id not in satisfaccion_llm:
            satisfaccion_llm[agente_id] = {"suma": 0.0, "count": 0}
        satisfaccion_llm[agente_id]["suma"] += valor
        satisfaccion_llm[agente_id]["count"] += 1

    sat_labels = []
    sat_hum_vals = []
    sat_llm_vals = []
    for agente in agentes:
        avg_h = None
        avg_l = None
        if agente.id in satisfaccion_hum and satisfaccion_hum[agente.id]["count"] > 0:
            avg_h = satisfaccion_hum[agente.id]["suma"] / satisfaccion_hum[agente.id]["count"]
        if agente.id in satisfaccion_llm and satisfaccion_llm[agente.id]["count"] > 0:
            avg_l = satisfaccion_llm[agente.id]["suma"] / satisfaccion_llm[agente.id]["count"]
        sat_labels.append(str(agente.nombre))
        sat_hum_vals.append(round(avg_h, 2) if avg_h is not None else 0.0)
        sat_llm_vals.append(round(avg_l, 2) if avg_l is not None else 0.0)
    
    sat_llm_vals = fix_none(sat_llm_vals)
    sat_hum_vals = fix_none(sat_hum_vals)
    satisfaccion_data = {
            "labels_json": json.dumps(sat_labels, ensure_ascii=False),
            "hum_data_json": json.dumps(sat_hum_vals),
            "llm_data_json": json.dumps(sat_llm_vals)
        }


    # 6. Pros y contras
    pros_cons = {}
    agente_success_rate = {}
    for agente in agentes:
        total_si = 0
        total_resp = 0
        for (caso_id, ag_id), vals in success_counts_hum.items():
            if ag_id == agente.id:
                total_si += vals["si"]
                total_resp += vals["total"]
        if total_resp > 0:
            agente_success_rate[agente.id] = (total_si / total_resp) * 100.0
        else:
            agente_success_rate[agente.id] = None

    agente_sat_avg = {}
    for agente in agentes:
        if agente.id in satisfaccion_hum and satisfaccion_hum[agente.id]["count"] > 0:
            agente_sat_avg[agente.id] = satisfaccion_hum[agente.id]["suma"] / satisfaccion_hum[agente.id]["count"]
        else:
            agente_sat_avg[agente.id] = None

    agente_tiempo_avg = {}
    resultados = Resultado.objects.values('agente_id').annotate(avg_time=Avg('tiempo_total_seg'))
    avg_time_map = {r['agente_id']: r['avg_time'] for r in resultados}
    for agente in agentes:
        agente_tiempo_avg[agente.id] = avg_time_map.get(agente.id, None)

    success_values = [v for v in agente_success_rate.values() if v is not None]
    sat_values = [v for v in agente_sat_avg.values() if v is not None]
    time_values = [v for v in agente_tiempo_avg.values() if v is not None]
    best_success = max(success_values) if success_values else None
    worst_success = min(success_values) if success_values else None
    best_sat = max(sat_values) if sat_values else None
    worst_sat = min(sat_values) if sat_values else None
    fastest_time = min(time_values) if time_values else None
    slowest_time = max(time_values) if time_values else None

    for agente in agentes:
        pros = []
        cons = []
        sr = agente_success_rate.get(agente.id)
        sa = agente_sat_avg.get(agente.id)
        tm = agente_tiempo_avg.get(agente.id)
        nombre = str(agente.nombre)

        # Pros
        if sr is not None:
            if best_success is not None and abs(sr - best_success) < 1e-6:
                pros.append(f"Tasa de éxito más alta: ~{sr:.1f}% pasos completados")
            elif sr >= 80:
                pros.append(f"Alta tasa de éxito en las tareas (~{sr:.0f}% pasos completados)")
        if sa is not None:
            if best_sat is not None and abs(sa - best_sat) < 1e-6:
                pros.append(f"Mayor satisfacción de usuarios (promedio {sa:.1f} de 5)")
            elif sa >= 4:
                pros.append(f"Satisfacción de usuarios elevada (promedio {sa:.1f}/5)")
        if tm is not None:
            if fastest_time is not None and abs(tm - fastest_time) < 1e-6:
                pros.append(f"Tiempo de ejecución más rápido (~{tm:.1f} s en promedio)")
            elif tm <= 5:
                pros.append(f"Ejecuta las tareas muy rápido (~{tm:.1f} s de media)")

        # Contras
        if sr is not None:
            if worst_success is not None and abs(sr - worst_success) < 1e-6:
                cons.append(f"Tasa de éxito más baja (solo ~{sr:.1f}% de pasos)")
            elif sr <= 50:
                cons.append(f"Baja tasa de éxito en las tareas (~{sr:.0f}% pasos cumplidos)")
        if sa is not None:
            if worst_sat is not None and abs(sa - worst_sat) < 1e-6:
                cons.append(f"Menor satisfacción de usuarios (promedio {sa:.1f} de 5)")
            elif sa is not None and sa <= 2.5:
                cons.append(f"Satisfacción de usuarios reducida (promedio {sa:.1f}/5)")
        if tm is not None:
            if slowest_time is not None and abs(tm - slowest_time) < 1e-6:
                cons.append(f"Más lento en ejecución (~{tm:.1f} s de media)")
            elif tm >= 30:
                cons.append(f"Tiempos de ejecución algo lentos (~{tm:.0f} s en promedio)")

        if not pros:
            pros.append("Cumple su función básica en las pruebas")
        if not cons:
            cons.append("No se han detectado contras importantes")

        pros_cons[nombre] = {"pros": pros, "cons": cons}

    return {
        "categorias_data": categorias_data,
        "performance_grouped_by_cat": {},
        "satisfaccion_data": satisfaccion_data,
        "pros_cons": pros_cons
    }
