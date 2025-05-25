from django.contrib import admin
from .models import Categoria,Pregunta, CasoUso, Agente, Resultado, MetricaEvaluacion

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(CasoUso)
class CasoUsoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'categoria', 'descripcion', 'pasos_esperados')
    search_fields = ('titulo', 'descripcion')
    list_filter = ('categoria',)

@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'modelo_llm', 'descripcion')
    search_fields = ('nombre', 'modelo_llm')

@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'agente', 'caso_uso', 'puntaje', 'fecha')
    search_fields = ('respuesta',)
    list_filter = ('agente', 'caso_uso', 'fecha')

@admin.register(MetricaEvaluacion)
class MetricaEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'caso_uso', 'agente', 'fecha', 'exito', 'precision')
    search_fields = ('caso_uso__titulo', 'agente__nombre')
    list_filter = ('fecha', 'exito', 'robustez')

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('id', 'caso_uso', 'texto', 'tipo', 'dificultad')
    search_fields = ('texto',)
    list_filter = ('tipo', 'dificultad', 'caso_uso')
