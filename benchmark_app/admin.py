from django.contrib import admin
from .models import (
    Categoria, CasoUso, Pregunta, Agente, Resultado,
    PreguntaEvaluacion, Evaluacion, RespuestaEvaluacion
)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(CasoUso)
class CasoUsoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'categoria', 'descripcion')
    search_fields = ('titulo', 'descripcion')
    list_filter = ('categoria',)

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('id', 'caso_uso', 'texto', 'tipo', 'dificultad')
    search_fields = ('texto',)
    list_filter = ('tipo', 'dificultad', 'caso_uso')

@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'modelo_llm', 'descripcion')
    search_fields = ('nombre', 'modelo_llm')

@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'agente','fecha', 'pregunta', 'respuesta', 'run_id',
        'tiempo_total_seg', 'acciones_realizadas', 'cpu_usado', 'ram_usada_mb'
    )
    search_fields = ('respuesta', 'logs')
    list_filter = ('agente', 'pregunta', 'fecha')

@admin.register(PreguntaEvaluacion)
class PreguntaEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'caso_uso', 'texto', 'orden')
    search_fields = ('texto',)
    list_filter = ('caso_uso',)

@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'resultado', 'tipo', 'puntaje_global', 'comentario', 'fecha', 'evaluador')
    search_fields = ('comentario', 'evaluador')
    list_filter = ('tipo', 'fecha', 'evaluador')

@admin.register(RespuestaEvaluacion)
class RespuestaEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'evaluacion', 'pregunta', 'valor')
    search_fields = ('valor',)
    list_filter = ('pregunta', 'evaluacion')
