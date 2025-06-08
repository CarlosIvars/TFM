"""
URL configuration for benchmark_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from benchmark_app.views import *

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', home, name='home'),  

    # Poblar desde JSON
    path('poblar_casos_uso_json/', poblar_casos_uso_desde_json),

    # API REST principales
    path('api/casos/', api_casos),                    # Lista de casos de uso
    path('api/agentes/', api_agentes),                # Lista de agentes
    path('api/casos/<int:caso_id>/preguntas/', api_preguntas_por_caso),  # Preguntas por caso

    # Nueva ejecución de agente (¡usa pregunta_id!)
    path('run/<int:pregunta_id>/<int:agente_id>/', run_agente, name='run_agente'),

    # Crear evaluación (POST)
    path('api/evaluacion/', crear_evaluacion, name='crear_evaluacion'),

    # Resultados y evaluaciones por API
    path('api/pregunta/<int:pregunta_id>/resultados/', ver_resultados_pregunta, name='ver_resultados_pregunta'),
    path('api/resultado/<int:resultado_id>/evaluaciones/', ver_evaluaciones_resultado, name='ver_evaluaciones_resultado'),

    # Vistas HTML auxiliares (personaliza según tu plantilla real)
    path('resultados/<int:ejecucion_id>/', resultado_view, name='resultado_view'),
    path('metricas/<int:agente_id>/', metricas_view, name='metricas_view'),
    
    # Evaluación LLM    
    path('evaluar_llm/<int:resultado_id>/', evaluar_llm_view, name='evaluar_llm_view'),

]

