from django.db import models
import uuid 

#####################
# Modelos de prompts
#####################
class Categoria(models.Model):
    """
    Representa una categoría temática para agrupar casos de uso relacionados.
    Ejemplo: 'E-commerce', 'Administración Pública', etc.
    """
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class CasoUso(models.Model):
    """
    Define un escenario o contexto concreto de benchmarking, agrupado bajo una categoría.
    Cada caso de uso tiene una descripción y los pasos esperados para que la tarea sea considerada exitosa.
    """
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    pasos_esperados = models.TextField(blank=True)  # JSON opcional

    def __str__(self):
        return f"{self.categoria.nombre}: {self.titulo}"

class Pregunta(models.Model):
    """
    Representa una pregunta o reto concreto dentro de un caso de uso.
    Cada pregunta especifica el tipo de acción requerida (extracción, navegación, login, etc.) y su dificultad.
    """
    texto = models.TextField()
    tipo = models.CharField(max_length=50) 
    """
    tipo	Descripción
    "extraccion"	Indica que la tarea consiste en extraer información de una web.
    "navegacion"	La tarea requiere navegar varias páginas o usar botones/enlaces.
    "interaccion"	Implica interacción compleja, como formularios, drag & drop, etc.
    "login"	Involucra autenticación o creación de cuentas.
    "simulacion_compra"	Prueba el proceso completo de checkout o compra sin pago real.
    "visual"	Tareas donde la extracción de imágenes o elementos visuales es clave.
    """
    dificultad = models.CharField(max_length=20, choices=[
        ('facil', 'Fácil'),
        ('media', 'Media'),
        ('dificil', 'Difícil'),
    ])
    caso_uso = models.ForeignKey(CasoUso, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.texto[:50]}... ({self.dificultad})"

#####################
# Tipos de Agentes
#####################

class Agente(models.Model):
    """
    Define un agente de búsqueda o extracción (puede ser LLM, scraper tradicional, etc.).
    Incluye nombre, descripción y el modelo de LLM si aplica.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    modelo_llm = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

#####################
# Métricas de Evaluación
#####################


class Resultado(models.Model):
    """
    Almacena el resultado de una ejecución de un agente sobre una pregunta concreta.
    Incluye la respuesta, logs de la ejecución y métricas objetivas de rendimiento.
    El campo run_id permite distinguir ejecuciones repetidas del mismo agente sobre la misma pregunta.
    """
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name="resultados")
    # pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name="resultados")
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, null=True, blank=True, related_name="resultados")
    respuesta = models.TextField()
    logs = models.TextField(blank=True)
    # Métricas objetivas:
    tiempo_total_seg = models.FloatField(null=True, blank=True)
    acciones_realizadas = models.IntegerField(null=True, blank=True)
    cpu_usado = models.FloatField(null=True, blank=True)
    ram_usada_mb = models.FloatField(null=True, blank=True)
    porcentaje_pasos_ok = models.FloatField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    # Identificador único para cada ejecución (run)
    run_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"{self.agente} - {self.pregunta} (Run: {self.run_id})"

class PreguntaEvaluacion(models.Model):
    """
    Pregunta concreta del cuestionario de evaluación para un caso de uso.
    Estas preguntas serán respondidas por los evaluadores humanos o automáticos para valorar cada resultado.
    """
    caso_uso = models.ForeignKey(CasoUso, on_delete=models.CASCADE, related_name="preguntas_evaluacion")
    texto = models.CharField(max_length=255)   # Texto de la pregunta de evaluación
    orden = models.PositiveSmallIntegerField(default=0)  # Orden de la pregunta en la encuesta
    def __str__(self):
        return f"[{self.caso_uso.titulo}] {self.texto}"
    
class Evaluacion(models.Model):
    """
    Valoración de un resultado concreto, realizada por un humano o de forma automática (LLM).
    Cada evaluación puede incluir puntuación global, comentario, y está asociada a un evaluador (anónimo o identificado).
    Permite varias evaluaciones por resultado.
    """
    TIPO_EVALUACION = [
        ('humano', 'Humano'),
        ('llm', 'LLM'),
    ]
    resultado = models.ForeignKey(Resultado, on_delete=models.CASCADE, related_name="evaluaciones")
    tipo = models.CharField(max_length=10, choices=TIPO_EVALUACION)
    puntaje_global = models.FloatField(null=True, blank=True)
    comentario = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    evaluador = models.CharField(max_length=100, null=True, blank=True)  # Para saber quién evaluó (opcional)

    def __str__(self):
        return f"Evaluación {self.tipo} de Resultado #{self.resultado.id} por {self.evaluador or 'anónimo'}"
    

class RespuestaEvaluacion(models.Model):
    """
    Respuesta individual a cada pregunta de la encuesta de evaluación.
    Cada respuesta está ligada a una evaluación concreta y a la pregunta de evaluación correspondiente.
    Se asegura que solo hay una respuesta por pregunta-evaluación.
    """
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="respuestas")
    pregunta = models.ForeignKey(PreguntaEvaluacion, on_delete=models.CASCADE, related_name="respuestas")
    valor = models.TextField()  # Respuesta dada a la pregunta (puede ser texto libre o escala numérica)

    class Meta:
        # Cada evaluación debe tener solo una respuesta por pregunta de evaluación:contentReference[oaicite:1]{index=1}
        constraints = [
            models.UniqueConstraint(fields=['evaluacion', 'pregunta'], name='uniq_respuesta_por_pregunta')
        ]
