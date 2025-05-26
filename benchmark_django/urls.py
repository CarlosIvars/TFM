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
    # path('crear_categorias/', crear_categorias),
    # path('crear_casos_uso/', crear_casos_uso),
    # path('poblar_bbdd/', poblar_bbdd),
    path('poblar_casos_uso_json/', poblar_casos_uso_desde_json),
    path('run/<int:caso_uso_id>/<int:agente_id>/', run_agente, name='run_agente'),
    path('', home, name='home'),  
    path('api/casos/', api_casos), # casos de uso
    path('api/agentes/', api_agentes), # agentes disponibles
    path('api/casos/<int:caso_id>/preguntas/', api_preguntas_por_caso), #preguntas



]
