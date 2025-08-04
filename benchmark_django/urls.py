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
    # ---- Admin ----
    path('admin/', admin.site.urls),

    # ---- Páginas HTML (render templates) ----
    path('', home, name='home'),
    path('resultados/', resultados_list_view, name='resultados_list'),                
    path('resultados/<int:ejecucion_id>/', resultado_view, name='resultado_view'),    
    path('metricas/<int:agente_id>/', metricas_view, name='metricas_view'),
    path('evaluar_llm/<int:resultado_id>/', evaluar_llm_view, name='evaluar_llm_view'),

    # ---- Utilidades ----
    path('poblar_casos_uso_json/', poblar_casos_uso_desde_json),

    # ---- API (JSON) ----
    path('api/casos/', api_casos),
    path('api/agentes/', api_agentes),
    path('api/casos/<int:caso_id>/preguntas/', api_preguntas_por_caso),

    # ejecuciones (run)
    path('run/<int:pregunta_id>/<int:agente_id>/', run_agente, name='run_agente'),

    # evaluaciones
    path('api/evaluacion/', crear_evaluacion, name='crear_evaluacion'),
    path('api/pregunta/<int:pregunta_id>/resultados/', ver_resultados_pregunta, name='ver_resultados_pregunta'),
    path('api/resultado/<int:resultado_id>/evaluaciones/', ver_evaluaciones_resultado, name='ver_evaluaciones_resultado'),

    # resultados (API de list y detail)
    path('api/resultados/', api_resultados_list, name='api_resultados_list'),
    path('api/resultados/<int:resultado_id>/', api_resultado_detail, name='api_resultado_detail'),
]

