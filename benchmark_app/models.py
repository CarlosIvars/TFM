from django.db import models

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class CasoUso(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    pasos_esperados = models.TextField(blank=True)  # JSON opcional

    def __str__(self):
        return f"{self.categoria.nombre}: {self.titulo}"

class Pregunta(models.Model):
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

class Agente(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    modelo_llm = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class MetricaEvaluacion(models.Model):
    caso_uso = models.ForeignKey(CasoUso, on_delete=models.CASCADE, null=True, blank=True)
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    exito = models.BooleanField()
    precision = models.FloatField(null=True, blank=True)
    robustez = models.BooleanField()
    tiempo_total_seg = models.FloatField()
    acciones_realizadas = models.IntegerField()
    cpu_usado = models.FloatField(null=True, blank=True)
    ram_usada_mb = models.FloatField(null=True, blank=True)
    calidad_log = models.IntegerField(null=True, blank=True)  # 1-5
    porcentaje_pasos_ok = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.caso_uso} - {self.agente} @ {self.fecha}"


class Resultado(models.Model):
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE)
    caso_uso = models.ForeignKey(CasoUso, on_delete=models.CASCADE, null=True, blank=True)
    respuesta = models.TextField()
    puntaje = models.FloatField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agente} - {self.caso_uso} ({self.puntaje})"
