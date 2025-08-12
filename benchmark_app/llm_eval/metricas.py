import json
from django.db.models import Avg
from ..models import Agente, CasoUso, PreguntaEvaluacion, Evaluacion, RespuestaEvaluacion, Resultado


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

    # 1) Mapear casos por categoría
    categoria_dict = {}
    for caso in casos:
        cat = str(caso.categoria)  # forzamos a string
        categoria_dict.setdefault(cat, []).append(caso)

    # 2) Respuestas (excluimos la de satisfacción)
    respuestas_hum = (
        RespuestaEvaluacion.objects
        .filter(evaluacion__tipo='humano')
        .exclude(pregunta__texto=satisfaccion_text)
        .select_related('evaluacion__resultado__agente', 'pregunta__caso_uso')
    )
    respuestas_llm = (
        RespuestaEvaluacion.objects
        .filter(evaluacion__tipo='llm')
        .exclude(pregunta__texto=satisfaccion_text)
        .select_related('evaluacion__resultado__agente', 'pregunta__caso_uso')
    )

    # 2.a) Conteos para desempeño por caso & agente (promedios por categoría)
    success_counts_hum = {}
    success_counts_llm = {}
    for resp in respuestas_hum:
        agente_id = resp.evaluacion.resultado.agente_id
        caso_id = resp.pregunta.caso_uso_id
        key = (caso_id, agente_id)
        bucket = success_counts_hum.setdefault(key, {"si": 0, "total": 0})
        bucket["total"] += 1
        if (resp.valor or "").strip().lower() == "si":
            bucket["si"] += 1
    for resp in respuestas_llm:
        agente_id = resp.evaluacion.resultado.agente_id
        caso_id = resp.pregunta.caso_uso_id
        key = (caso_id, agente_id)
        bucket = success_counts_llm.setdefault(key, {"si": 0, "total": 0})
        bucket["total"] += 1
        if (resp.valor or "").strip().lower() == "si":
            bucket["si"] += 1

    # 3) Desempeño por Categoría (promedio)
    cat_labels, cat_hum_data, cat_llm_data = [], [], []
    for cat, casos_cat in categoria_dict.items():
        hum_tot = hum_si = 0
        llm_tot = llm_si = 0
        for caso in casos_cat:
            for agente in agentes:
                key = (caso.id, agente.id)
                if key in success_counts_hum:
                    hum_tot += success_counts_hum[key]["total"]
                    hum_si  += success_counts_hum[key]["si"]
                if key in success_counts_llm:
                    llm_tot += success_counts_llm[key]["total"]
                    llm_si  += success_counts_llm[key]["si"]
        cat_labels.append(cat)
        cat_hum_data.append(round((hum_si / hum_tot) * 100, 2) if hum_tot else 0.0)
        cat_llm_data.append(round((llm_si / llm_tot) * 100, 2) if llm_tot else 0.0)

    categorias_data = {
        "labels_json": json.dumps(cat_labels, ensure_ascii=False),
        "hum_data_json": json.dumps(cat_hum_data),
        "llm_data_json": json.dumps(cat_llm_data),
        "categorias": cat_labels,
    }

    # 4) Desempeño por agente y caso de uso (por pasos esperados/preguntas)
    #    Para cada caso, agregamos todas las evaluaciones y calculamos % de "sí" por pregunta (Humano vs LLM)
    #    Estructura final: { "Categoria": [ {caso_id, caso_titulo, labels, hum, llm}, ... ] }
    preguntas_por_caso = {}
    for p in (
        PreguntaEvaluacion.objects
        .exclude(texto=satisfaccion_text)
        .select_related('caso_uso')
        .order_by('caso_uso_id', 'id')
    ):
        preguntas_por_caso.setdefault(p.caso_uso_id, []).append(p)

    # Conteos por (caso_id, pregunta_id)
    step_counts_hum = {}
    step_counts_llm = {}
    for resp in respuestas_hum:
        pid = resp.pregunta_id
        cid = resp.pregunta.caso_uso_id
        key = (cid, pid)
        bucket = step_counts_hum.setdefault(key, {"si": 0, "total": 0})
        bucket["total"] += 1
        if (resp.valor or "").strip().lower() == "si":
            bucket["si"] += 1
    for resp in respuestas_llm:
        pid = resp.pregunta_id
        cid = resp.pregunta.caso_uso_id
        key = (cid, pid)
        bucket = step_counts_llm.setdefault(key, {"si": 0, "total": 0})
        bucket["total"] += 1
        if (resp.valor or "").strip().lower() == "si":
            bucket["si"] += 1

    case_steps_by_cat = {}
    for cat, casos_cat in categoria_dict.items():
        case_entries = []
        for caso in casos_cat:
            qs = preguntas_por_caso.get(caso.id, [])
            if not qs:
                # No hay preguntas (pasos) para este caso (o sólo estaba la de satisfacción)
                continue
            labels = [q.texto for q in qs]
            hum_vals, llm_vals = [], []
            for q in qs:
                key = (caso.id, q.id)
                # Humano
                if key in step_counts_hum and step_counts_hum[key]["total"] > 0:
                    h = (step_counts_hum[key]["si"] / step_counts_hum[key]["total"]) * 100.0
                else:
                    h = 0.0
                # LLM
                if key in step_counts_llm and step_counts_llm[key]["total"] > 0:
                    l = (step_counts_llm[key]["si"] / step_counts_llm[key]["total"]) * 100.0
                else:
                    l = 0.0
                hum_vals.append(round(h, 2))
                llm_vals.append(round(l, 2))
            case_entries.append({
                "caso_id": caso.id,
                "caso_titulo": str(caso.titulo),
                "labels": labels,
                "hum": hum_vals,
                "llm": llm_vals,
            })
        case_steps_by_cat[cat] = case_entries

    case_steps_by_cat_json = json.dumps(case_steps_by_cat, ensure_ascii=False)

    # 5) Satisfacción global por agente (usuarios/llm)
    satisfaccion_hum = {}
    satisfaccion_llm = {}
    evaluaciones_hum = Evaluacion.objects.filter(tipo='humano').select_related('resultado__agente')
    for ev in evaluaciones_hum:
        if ev.puntaje_global is None:
            continue
        aid = ev.resultado.agente_id
        bucket = satisfaccion_hum.setdefault(aid, {"suma": 0.0, "count": 0})
        bucket["suma"] += float(ev.puntaje_global)
        bucket["count"] += 1

    respuestas_sat_llm = (
        RespuestaEvaluacion.objects
        .filter(evaluacion__tipo='llm', pregunta__texto=satisfaccion_text)
        .select_related('evaluacion__resultado__agente')
    )
    for resp in respuestas_sat_llm:
        aid = resp.evaluacion.resultado.agente_id
        try:
            valor = float(resp.valor)
        except Exception:
            continue
        bucket = satisfaccion_llm.setdefault(aid, {"suma": 0.0, "count": 0})
        bucket["suma"] += valor
        bucket["count"] += 1

    sat_labels, sat_hum_vals, sat_llm_vals = [], [], []
    for agente in agentes:
        avg_h = satisfaccion_hum.get(agente.id, {}).get("suma", 0.0)
        cnt_h = satisfaccion_hum.get(agente.id, {}).get("count", 0)
        avg_l = satisfaccion_llm.get(agente.id, {}).get("suma", 0.0)
        cnt_l = satisfaccion_llm.get(agente.id, {}).get("count", 0)
        sat_labels.append(str(agente.nombre))
        sat_hum_vals.append(round(avg_h / cnt_h, 2) if cnt_h else 0.0)
        sat_llm_vals.append(round(avg_l / cnt_l, 2) if cnt_l else 0.0)

    sat_llm_vals = fix_none(sat_llm_vals)
    sat_hum_vals = fix_none(sat_hum_vals)
    satisfaccion_data = {
        "labels_json": json.dumps(sat_labels, ensure_ascii=False),
        "hum_data_json": json.dumps(sat_hum_vals),
        "llm_data_json": json.dumps(sat_llm_vals),
    }

    # 6) Pros y Contras (como ya tenías)
    pros_cons = {}
    agente_success_rate = {}
    for agente in agentes:
        total_si = 0
        total_resp = 0
        for (caso_id, ag_id), vals in success_counts_hum.items():
            if ag_id == agente.id:
                total_si += vals["si"]
                total_resp += vals["total"]
        agente_success_rate[agente.id] = (total_si / total_resp) * 100.0 if total_resp else None

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
        pros, cons = [], []
        sr = agente_success_rate.get(agente.id)
        sa = agente_sat_avg.get(agente.id)
        tm = agente_tiempo_avg.get(agente.id)

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

        pros_cons[str(agente.nombre)] = {"pros": pros, "cons": cons}

    return {
        "categorias_data": categorias_data,
        # La gráfica antigua "performance_grouped_by_cat" ya no se usa:
        # "performance_grouped_by_cat": performance_grouped_by_cat,
        "case_steps_by_cat": case_steps_by_cat,
        "case_steps_by_cat_json": case_steps_by_cat_json,
        "satisfaccion_data": satisfaccion_data,
        "pros_cons": pros_cons,
    }
