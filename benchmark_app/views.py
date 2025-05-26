from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

import json
import os
import psutil
import tracemalloc
from .models import Categoria, CasoUso, Agente, CasoUso, Pregunta, Resultado, MetricaEvaluacion


def home(request):
    return render(request, 'benchmark_app/home.html')

def api_casos(request):
    data = list(CasoUso.objects.select_related('categoria').values('id', 'titulo', 'categoria__nombre'))
    return JsonResponse([
        {'id': d['id'], 'titulo': d['titulo'], 'categoria': d['categoria__nombre']} for d in data
    ], safe=False)


def api_agentes(request):
    data = list(Agente.objects.values('id', 'nombre'))
    return JsonResponse(data, safe=False)

def api_preguntas_por_caso(request, caso_id):
    preguntas = Pregunta.objects.filter(caso_uso_id=caso_id).values('id', 'texto')
    return JsonResponse(list(preguntas), safe=False)


def poblar_casos_uso_desde_json(request):
    # Ruta del archivo JSON (ajusta si lo pones en otro sitio)
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
        descripcion = caso["caso"]  # Usamos el mismo texto si no tienes un campo descripción separado.
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


@csrf_exempt
def run_agente(request, caso_uso_id, agente_id):
    if request.method != "POST":
        return JsonResponse({"error": "Sólo se permite POST"}, status=405)

    from benchmark_app.agents.browser_use_agent import BrowserUseAgent
    data = json.loads(request.body)
    prompt_manual = data.get("prompt_manual", "")
    pregunta_id = data.get("pregunta_id")

    caso_uso = get_object_or_404(CasoUso, id=caso_uso_id)
    agente = get_object_or_404(Agente, id=agente_id)

    if prompt_manual.strip():
        prompt = prompt_manual.strip()
        pregunta = None
    else:
        if not pregunta_id:
            return JsonResponse({"error": "No se proporcionó ni prompt manual ni pregunta_id."}, status=400)
        pregunta = get_object_or_404(Pregunta, id=pregunta_id)
        prompt = pregunta.texto


    agente_runner = BrowserUseAgent()
    resultado_dict = agente_runner.run_case(prompt)

    resultado = Resultado.objects.create(
        agente=agente,
        caso_uso=caso_uso,
        respuesta=resultado_dict['respuesta'] or "",
        puntaje=resultado_dict.get('puntaje'),
        logs=resultado_dict.get('logs', ''),
    )

    MetricaEvaluacion.objects.create(
        caso_uso=caso_uso,
        agente=agente,
        exito=resultado_dict.get("exito", False),
        precision=resultado_dict.get("precision"),
        robustez=resultado_dict.get("robustez", False),
        tiempo_total_seg=resultado_dict.get("tiempo_total_seg", 0.0),
        acciones_realizadas=resultado_dict.get("acciones_realizadas") or 0,
        cpu_usado=resultado_dict.get("cpu_usado", 0.0),
        ram_usada_mb=resultado_dict.get("ram_usada_mb", 0.0),
        calidad_log=resultado_dict.get("calidad_log"),
        porcentaje_pasos_ok=resultado_dict.get("porcentaje_pasos_ok"),
    )

    return JsonResponse({"message": "Ejecución completada", "resultado_id": resultado.id})


def ejecutar_benchmark(request):
    from benchmark_app.agents.browser_use_agent import BrowserUseAgent
    casos = CasoUso.objects.all()
    agentes = Agente.objects.all()
    resultado = None

    if request.method == 'POST':
        caso_id = request.POST['caso_uso']
        agente_id = request.POST['agente']
        prompt_id = request.POST.get('pregunta')
        prompt_manual = request.POST.get('custom_prompt')
        caso = get_object_or_404(CasoUso, id=caso_id)
        agente = get_object_or_404(Agente, id=agente_id)
        prompt = prompt_manual or Pregunta.objects.get(id=prompt_id).texto

        runner = BrowserUseAgent(llm_model=agente.modelo_llm)
        res_dict = runner.run_case(prompt)

        Resultado.objects.create(...)

        resultado = res_dict

    return render(request, 'benchmark_app/ejecutar.html', {
        'casos': casos,
        'agentes': agentes,
        'resultado': resultado
    })
