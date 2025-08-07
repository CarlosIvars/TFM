from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils.timesince import timesince
from django.http import JsonResponse
from .models import (
    Categoria, CasoUso, Agente, Pregunta,
    Resultado, PreguntaEvaluacion, Evaluacion, RespuestaEvaluacion
)
from .llm_eval.evaluator import evaluar_resultado_llm
from .llm_eval import metricas
import json
import os

def home(request):
    return render(request, 'benchmark_app/home.html')

@api_view(["GET"])
def api_casos(request):
    data = list(CasoUso.objects.select_related('categoria').values('id', 'titulo', 'categoria__nombre'))
    return Response([
        {'id': d['id'], 'titulo': d['titulo'], 'categoria': d['categoria__nombre']} for d in data
    ])

@api_view(["GET"])
def api_agentes(request):
    data = list(Agente.objects.values('id', 'nombre'))
    return Response(data)


@api_view(["GET"])
def poblar_casos_uso_desde_json(request):
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'casos_uso.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    resumen = []
    for caso in data:
        nombre_categoria = caso["categoria"]
        try:
            categoria = Categoria.objects.get(nombre=nombre_categoria)
        except Categoria.DoesNotExist:
            resumen.append(f"Categoría NO encontrada: {nombre_categoria}")
            continue
        titulo = caso["caso"]
        descripcion = caso["caso"]
        pasos_esperados = json.dumps(caso["pasos"], ensure_ascii=False)
        obj, created = CasoUso.objects.get_or_create(
            categoria=categoria,
            titulo=titulo,
            defaults={
                "descripcion": descripcion,
                "pasos_esperados": pasos_esperados
            }
        )
        if created:
            resumen.append(f"Creado: {nombre_categoria} - {titulo}")
        else:
            resumen.append(f"Ya existía: {nombre_categoria} - {titulo}")
    return HttpResponse("<br>".join(resumen))

@api_view(["POST"])
def run_agente(request, pregunta_id, agente_id):
    from benchmark_app.agents.browser_use_agent import BrowserUseAgent
    data = request.data
    prompt_manual = data.get("prompt_manual", "")

    agente = get_object_or_404(Agente, id=agente_id)

    if int(pregunta_id) == 0:
        pregunta = None
        prompt = prompt_manual.strip()
        if not prompt:
            return Response({"error": "Prompt personalizado vacío"}, status=400)
    else:
        pregunta = get_object_or_404(Pregunta, id=pregunta_id)
        prompt = prompt_manual.strip() if prompt_manual.strip() else pregunta.texto

    agente_runner = BrowserUseAgent(llm_model=agente.modelo_llm)
    resultado_dict = agente_runner.run_case(prompt)
    print('Resultado del agente:', resultado_dict)
    acciones = resultado_dict.get("acciones_realizadas") or []
    resultado = Resultado.objects.create(
        agente=agente,
        pregunta=pregunta,
        respuesta=resultado_dict.get('respuesta') or '',
        logs=resultado_dict.get('logs', ''),
        tiempo_total_seg=resultado_dict.get("tiempo_total_seg"),
        acciones_realizadas=acciones,
        n_acciones_realizadas=len(acciones),
        cpu_usado=resultado_dict.get("cpu_usado"),
        ram_usada_mb=resultado_dict.get("ram_usada_mb"),
        porcentaje_pasos_ok=resultado_dict.get("porcentaje_pasos_ok"),
    )

    return Response({"message": "Ejecución completada", "resultado_id": resultado.id})

@api_view(["GET", "POST"])
def api_preguntas_por_caso(request, caso_id):
    if request.method == "POST":
        # Crear una nueva Pregunta asociada al caso de uso dado
        data = request.data or {}
        texto = data.get('texto')
        tipo = data.get('tipo')
        dificultad = data.get('dificultad')
        if not texto or not tipo or not dificultad:
            return Response({"error": "Faltan campos obligatorios."}, status=400)
        caso = get_object_or_404(CasoUso, id=caso_id)
        nueva_pregunta = Pregunta.objects.create(
            texto=texto, tipo=tipo, dificultad=dificultad, caso_uso=caso
        )
        # Devolver la nueva pregunta (id y texto) en la respuesta
        return Response({"id": nueva_pregunta.id, "texto": nueva_pregunta.texto}, status=201)
    else:
        # GET: listar preguntas del caso de uso
        preguntas = Pregunta.objects.filter(caso_uso_id=caso_id).values('id', 'texto')
        return Response(list(preguntas))

@api_view(["GET"])
def api_resultados_list(request):
    """
    Devuelve todas las ejecuciones (Resultado).
    """
    qs = Resultado.objects.select_related('agente', 'pregunta').order_by('-fecha')
    data = []
    for r in qs:
        data.append({
            "id": r.id,
            "estado": r.estado,
            "agente_id": r.agente_id,
            "agente_nombre": getattr(r.agente, 'nombre', str(r.agente)),
            "pregunta_id": r.pregunta_id,
            "pregunta_preview": (r.pregunta.texto[:60] + '...') if r.pregunta and r.pregunta.texto else None,
            "fecha": r.fecha.isoformat(),
            "fecha_human": timesince(r.fecha) + " atrás" if r.fecha else "",
            "run_id": str(r.run_id),
        })
    return Response(data)

def resultados_list_view(request):
    """
    Página HTML de 'Evaluar Agente' (lista vacía inicialmente).
    La columna izquierda se llena vía JS llamando a /api/resultados/.
    """
    context = {
        "ejecucion": None,        # sin selección
        "pasos_esperados": [],    # ajusta si necesitas
    }
    return render(request, "benchmark_app/resultados.html", context)


@api_view(["GET"])
def api_resultado_detail(request, resultado_id):
    """
    Devuelve el detalle mínimo de una ejecución, si necesitas usarlo por AJAX.
    """
    r = get_object_or_404(Resultado.objects.select_related('agente', 'pregunta'), id=resultado_id)
    return Response({
        "id": r.id,
        "estado": r.estado,
        "agente_id": r.agente_id,
        "agente_nombre": getattr(r.agente, 'nombre', str(r.agente)),
        "pregunta_id": r.pregunta_id,
        "pregunta_texto": r.pregunta.texto if r.pregunta else None,
        "respuesta": r.respuesta,
        "logs": r.logs,
        "fecha": r.fecha.isoformat(),
        "run_id": str(r.run_id),
    })

@api_view(["POST"])
def crear_evaluacion(request):
    """
    Crea una evaluación (humano o LLM) para un resultado, con respuestas.
    Espera:
      - resultado_id
      - tipo ('humano' o 'llm')
      - puntaje_global (opcional)
      - comentario (opcional)
      - evaluador (opcional)
      - respuestas: lista de {'pregunta_id', 'valor'}
    """
    data = request.data
    resultado = get_object_or_404(Resultado, id=data['resultado_id'])
    tipo = data['tipo']
    puntaje_global = data.get('puntaje_global')
    comentario = data.get('comentario', '')
    evaluador = data.get('evaluador', '')

    evaluacion = Evaluacion.objects.create(
        resultado=resultado,
        tipo=tipo,
        puntaje_global=puntaje_global,
        comentario=comentario,
        evaluador=evaluador
    )

    respuestas = data.get('respuestas', [])
    for r in respuestas:
        pregunta = get_object_or_404(PreguntaEvaluacion, id=r['pregunta_id'])
        RespuestaEvaluacion.objects.create(
            evaluacion=evaluacion,
            pregunta=pregunta,
            valor=r['valor']
        )

    return Response({"message": "Evaluación creada", "evaluacion_id": evaluacion.id})

@api_view(["GET"])
def ver_resultados_pregunta(request, pregunta_id):
    """
    Lista todos los resultados para una pregunta.
    """
    resultados = Resultado.objects.filter(pregunta_id=pregunta_id)
    data = []
    for r in resultados:
        data.append({
            "id": r.id,
            "agente": r.agente.nombre,
            "respuesta": r.respuesta,
            "fecha": r.fecha,
            "run_id": r.run_id,
            "tiempo_total_seg": r.tiempo_total_seg,
            "acciones_realizadas": r.acciones_realizadas,
            "cpu_usado": r.cpu_usado,
            "ram_usada_mb": r.ram_usada_mb,
            "porcentaje_pasos_ok": r.porcentaje_pasos_ok,
        })
    return Response(data)

@api_view(["GET"])
def ver_evaluaciones_resultado(request, resultado_id):
    """
    Devuelve todas las evaluaciones (humanas y LLM) de un resultado, con sus respuestas.
    """
    evaluaciones = Evaluacion.objects.filter(resultado_id=resultado_id)
    data = []
    for ev in evaluaciones:
        respuestas = [
            {"pregunta": resp.pregunta.texto, "valor": resp.valor}
            for resp in ev.respuestas.all()
        ]
        data.append({
            "id": ev.id,
            "tipo": ev.tipo,
            "puntaje_global": ev.puntaje_global,
            "comentario": ev.comentario,
            "fecha": ev.fecha,
            "evaluador": ev.evaluador,
            "respuestas": respuestas
        })
    return Response(data)

# Puedes añadir más views según necesites (por ejemplo, obtener preguntas de evaluación para un caso de uso, etc.)

@api_view(["GET", "POST"])
def resultado_view(request, ejecucion_id):
    resultado = get_object_or_404(Resultado, id=ejecucion_id)
    pregunta = resultado.pregunta
    caso_uso = pregunta.caso_uso
    pasos_esperados = []
    try:
        pasos_esperados = json.loads(caso_uso.pasos_esperados)
    except Exception:
        pasos_esperados = []

    mensaje_exito = None

    if request.method == "POST":
        # Recoge respuestas del formulario
        pasos_ok = [request.POST.get(f"paso_{i}", "no") == "si" for i in range(len(pasos_esperados))]
        nivel_satisfaccion = request.POST.get("nivel_satisfaccion")
        comentario = request.POST.get("comentario", "")

        # Crea la Evaluacion y RespuestaEvaluacion
        evaluacion = Evaluacion.objects.create(
            resultado=resultado,
            tipo='humano',
            puntaje_global=nivel_satisfaccion,
            comentario=comentario,
            evaluador=None  # Aquí puedes usar request.user.username si hay login
        )

        # Guarda una respuesta por cada paso esperado
        for i, paso in enumerate(pasos_esperados):
            valor = "si" if pasos_ok[i] else "no"
            # Para trazabilidad, creamos PreguntaEvaluacion "on-the-fly" si no existen (opcional)
            pe, _ = PreguntaEvaluacion.objects.get_or_create(
                caso_uso=caso_uso,
                texto=paso,
                defaults={'orden': i}
            )
            RespuestaEvaluacion.objects.create(
                evaluacion=evaluacion,
                pregunta=pe,
                valor=valor
            )

        # Pregunta de satisfacción (siempre al final)
        pregunta_sat, _ = PreguntaEvaluacion.objects.get_or_create(
            caso_uso=caso_uso,
            texto="Nivel de satisfacción global del agente (1-5)",
            defaults={'orden': len(pasos_esperados)}
        )
        RespuestaEvaluacion.objects.create(
            evaluacion=evaluacion,
            pregunta=pregunta_sat,
            valor=nivel_satisfaccion
        )

        mensaje_exito = "¡Evaluación enviada correctamente!"

    return render(request, 'benchmark_app/resultados.html', {
        'ejecucion': resultado,
        'pasos_esperados': pasos_esperados,
        'mensaje_exito': mensaje_exito
    })

@api_view(["GET"])
def metricas_view(request):
    # Calcula las métricas agregadas y prepara los datos para la plantilla
    print("Calculando métricas...")
    context = metricas.calcular_metricas()
    
    print("Métricas calculadas:", context)
    return render(request, 'benchmark_app/metricas.html', context)

@api_view(["GET"])
def evaluar_llm_view(request, resultado_id):
    resultado = get_object_or_404(Resultado, id=resultado_id)

    if resultado.pregunta is None:
        return JsonResponse({"error": "Este resultado no tiene 'pregunta' asociada."}, status=400)

    pregunta = resultado.pregunta
    caso_uso = pregunta.caso_uso

    try:
        pasos = json.loads(caso_uso.pasos_esperados or "[]")
    except Exception:
        pasos = []

    preguntas_evaluacion = list(
        caso_uso.preguntas_evaluacion.order_by('orden').values_list('texto', flat=True)
    )

    try:
        output_dict = evaluar_resultado_llm(
            result=resultado.respuesta or "",
            pasos=pasos,
            logs=resultado.logs or "",
            preguntas_evaluacion=preguntas_evaluacion
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Fallo evaluando con LLM: {e}"}, status=500)

    evaluacion = Evaluacion.objects.create(
        resultado=resultado,
        tipo='llm',
        puntaje_global=None,
        comentario="Evaluación automática LLM"
    )

    for pregunta_texto, valor in output_dict.items():
        try:
            pe = PreguntaEvaluacion.objects.get(caso_uso=caso_uso, texto=pregunta_texto)
            RespuestaEvaluacion.objects.create(
                evaluacion=evaluacion,
                pregunta=pe,
                valor=valor
            )
        except PreguntaEvaluacion.DoesNotExist:
            # opcional: crear la pregunta si no existe
            pass

    return JsonResponse({"ok": True, "respuestas": output_dict}, status=200)
