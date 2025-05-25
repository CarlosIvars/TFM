from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from .models import Categoria, CasoUso
import json
import os

def crear_categorias(request):
    CATEGORIAS = [
        "Comercio electrónico",
        "Noticias y blogs dinámicos",
        "Redes sociales",
        "Webs corporativas",
        "Portales de empleo",
        "Webs administrativas",
        "Acciones complejas",
        "Compras online completas",
        "Creación de perfiles",
    ]
    creadas = []
    for nombre in CATEGORIAS:
        obj, created = Categoria.objects.get_or_create(nombre=nombre)
        if created:
            creadas.append(f"Creada: {nombre}")
        else:
            creadas.append(f"Ya existía: {nombre}")
    return HttpResponse("<br>".join(creadas))



def crear_casos_uso(request):
    # Diccionario: {nombre_categoria: [(titulo, descripcion), ...]}
    CASOS_DE_USO = {
        "Comercio electrónico": [
            ("Buscar producto en Amazon", "Buscar un producto específico en Amazon y extraer precio, reseñas y descripción."),
            ("Listar productos por categoría", "Extraer listado completo de productos de una categoría específica (ejemplo: libros más vendidos)."),
            ("Extraer precios dinámicos en eBay", "Extraer precios que cambian según usuario o sesión para productos específicos en eBay."),
        ],
        "Noticias y blogs dinámicos": [
            ("Titulares y fechas en periódico online", "Extraer titulares principales y fechas de publicación de un periódico online dinámico (El País)."),
            ("Extraer de varias páginas de resultados", "Navegar automáticamente entre páginas de resultados de búsqueda y extraer contenido relevante."),
            ("Artículos con scroll infinito", "Obtener el texto completo de artículos con carga dinámica (Medium, scroll infinito)."),
        ],
        "Redes sociales": [
            ("Últimas publicaciones de Twitter (X)", "Extraer últimas publicaciones de un perfil público de Twitter (X)."),
            ("Información básica de LinkedIn", "Obtener información básica de un perfil público en LinkedIn (cargo actual, empresa, ubicación)."),
            ("Contenido visual reciente de Instagram", "Extraer contenido visual reciente (fotos) de un perfil público de Instagram (con interacción necesaria)."),
        ],
        "Webs corporativas": [
            ("Eventos en calendario interactivo", "Extraer eventos futuros (fechas y detalles) desde un calendario interactivo (tipo calendario JS)."),
            ("Noticias recientes en empresa", "Obtener noticias recientes de sección dinámica de empresa (carga tras clic o scroll)."),
            ("Oficinas/sucursales con mapas dinámicos", "Extraer listado de oficinas o sucursales con mapas dinámicos (Google Maps embebidos)."),
        ],
        "Portales de empleo": [
            ("Buscar ofertas avanzadas en LinkedIn Jobs", "Buscar ofertas de trabajo específicas por criterios avanzados en LinkedIn Jobs."),
            ("Detalles de empleos en Indeed", "Extraer detalles de empleos desde Indeed (descripción, ubicación, salario)."),
            ("Información de empresas en Glassdoor", "Obtener información dinámica sobre empresas empleadoras (perfiles completos desde Glassdoor)."),
        ],
        "Webs administrativas": [
            ("Datos desde el BOE", "Extraer información estructurada desde el BOE o similar (licitaciones recientes)."),
            ("Navegar formularios administrativos", "Navegar formularios administrativos para obtener información específica (cita previa médico)."),
            ("Tablas HTML dinámicas de INE", "Descargar y parsear información desde tablas HTML dinámicas de estadísticas públicas (INE)."),
        ],
        "Acciones complejas": [
            ("Completar formulario dependiente", "Completar formulario dinámico con pasos dependientes (selección múltiple)."),
            ("Navegar mediante drag & drop", "Navegar mediante drag&drop (selección interactiva tipo listas ordenables)."),
            ("Scroll infinito en Pinterest", "Manejar scroll infinito para cargar múltiples páginas de resultados en Pinterest o similar."),
        ],
        "Compras online completas": [
            ("Simular compra en tienda pequeña", "Simular un proceso completo en una tienda online pequeña (añadir al carrito, rellenar dirección y método de pago, sin realizar pago real)."),
            ("Checkout múltiple en tienda grande", "Añadir múltiples artículos al carrito y simular proceso de checkout en tienda grande (Zara online)."),
            ("Popups y descuentos automáticos", "Interactuar dinámicamente con popups promocionales y descuentos automáticos al hacer compras (tienda online tipo PCComponentes)."),
        ],
        "Creación de perfiles": [
            ("Registro en web sencilla", "Completar registro de usuario nuevo en web sencilla (WordPress estándar)."),
            ("Registro complejo con validaciones", "Completar registro complejo con validaciones y captura dinámica de campos (Airbnb o Booking)."),
            ("Login con verificación en dos pasos", "Automatizar login con verificación en dos pasos dinámica (correo electrónico)."),
            ("Modificar perfil tras login", "Modificar dinámicamente información del perfil creado tras login."),
        ]
    }

    resumen = []
    for nombre_categoria, casos in CASOS_DE_USO.items():
        try:
            categoria = Categoria.objects.get(nombre=nombre_categoria)
        except Categoria.DoesNotExist:
            resumen.append(f"Categoría NO encontrada: {nombre_categoria}")
            continue
        for caso in casos:
            titulo, descripcion = caso
            obj, created = CasoUso.objects.get_or_create(
                categoria=categoria, titulo=titulo,
                defaults={"descripcion": descripcion, "pasos_esperados": ""}
            )
            if created:
                resumen.append(f"Creado: {categoria} - {titulo}")
            else:
                resumen.append(f"Ya existía: {categoria} - {titulo}")
    return HttpResponse("<br>".join(resumen))



from django.http import HttpResponse
from .models import Categoria, CasoUso, Agente

def poblar_bbdd(request):
    # 1. Categorías
    CATEGORIAS = [
        "Comercio electrónico",
        "Noticias y blogs dinámicos",
        "Redes sociales",
        "Webs corporativas",
        "Portales de empleo",
        "Webs administrativas",
        "Acciones complejas",
        "Compras online completas",
        "Creación de perfiles",
    ]

    # 2. Casos de uso y pasos esperados (JSON como string)
    CASOS_DE_USO = {
        "Comercio electrónico": [
            {
                "titulo": "Buscar producto en Amazon",
                "descripcion": "Buscar un producto específico en Amazon y extraer precio, reseñas y descripción.",
                "pasos": [
                    "Entrar a amazon.es",
                    "Buscar el producto por nombre",
                    "Seleccionar el primer resultado",
                    "Extraer precio",
                    "Extraer reseñas",
                    "Extraer descripción"
                ]
            },
            {
                "titulo": "Listar productos por categoría",
                "descripcion": "Extraer listado completo de productos de una categoría específica (ejemplo: libros más vendidos).",
                "pasos": [
                    "Entrar en la categoría",
                    "Paginación de resultados",
                    "Extraer título y precio de cada producto",
                    "Extraer información adicional (valoración, envío)"
                ]
            },
            {
                "titulo": "Extraer precios dinámicos en eBay",
                "descripcion": "Extraer precios que cambian según usuario o sesión para productos específicos en eBay.",
                "pasos": [
                    "Entrar en ebay.es",
                    "Buscar producto específico",
                    "Navegar a la ficha de producto",
                    "Capturar precio mostrado",
                    "Verificar si cambia tras recargar o navegar de incógnito"
                ]
            },
        ],
        "Noticias y blogs dinámicos": [
            {
                "titulo": "Titulares y fechas en periódico online",
                "descripcion": "Extraer titulares principales y fechas de publicación de un periódico online dinámico (El País).",
                "pasos": [
                    "Entrar a elpais.com",
                    "Extraer titulares de la portada",
                    "Extraer fechas de publicación asociadas",
                    "Guardar resultados"
                ]
            },
            {
                "titulo": "Extraer de varias páginas de resultados",
                "descripcion": "Navegar automáticamente entre páginas de resultados de búsqueda y extraer contenido relevante.",
                "pasos": [
                    "Buscar término concreto",
                    "Ir a la sección de resultados",
                    "Extraer titulares y links",
                    "Navegar página siguiente",
                    "Repetir proceso varias páginas"
                ]
            },
            {
                "titulo": "Artículos con scroll infinito",
                "descripcion": "Obtener el texto completo de artículos con carga dinámica (Medium, scroll infinito).",
                "pasos": [
                    "Entrar en artículo de Medium",
                    "Hacer scroll hasta el final",
                    "Detectar carga dinámica",
                    "Extraer texto completo"
                ]
            },
        ],
        "Redes sociales": [
            {
                "titulo": "Últimas publicaciones de Twitter (X)",
                "descripcion": "Extraer últimas publicaciones de un perfil público de Twitter (X).",
                "pasos": [
                    "Entrar en twitter.com/usuario",
                    "Extraer publicaciones recientes (texto y fecha)",
                    "Extraer enlaces y menciones"
                ]
            },
            {
                "titulo": "Información básica de LinkedIn",
                "descripcion": "Obtener información básica de un perfil público en LinkedIn (cargo actual, empresa, ubicación).",
                "pasos": [
                    "Entrar en perfil público",
                    "Extraer nombre y cargo actual",
                    "Extraer empresa",
                    "Extraer ubicación"
                ]
            },
            {
                "titulo": "Contenido visual reciente de Instagram",
                "descripcion": "Extraer contenido visual reciente (fotos) de un perfil público de Instagram (con interacción necesaria).",
                "pasos": [
                    "Entrar en instagram.com/usuario",
                    "Aceptar cookies/popups",
                    "Extraer URLs de las últimas fotos",
                    "Descargar miniaturas"
                ]
            },
        ],
        "Webs corporativas": [
            {
                "titulo": "Eventos en calendario interactivo",
                "descripcion": "Extraer eventos futuros (fechas y detalles) desde un calendario interactivo (tipo calendario JS).",
                "pasos": [
                    "Entrar a la web de la empresa",
                    "Navegar al calendario",
                    "Interactuar con los elementos para ver eventos",
                    "Extraer fecha y descripción"
                ]
            },
            {
                "titulo": "Noticias recientes en empresa",
                "descripcion": "Obtener noticias recientes de sección dinámica de empresa (carga tras clic o scroll).",
                "pasos": [
                    "Entrar a sección de noticias",
                    "Hacer scroll o clic para cargar más",
                    "Extraer titular y resumen",
                    "Extraer fecha"
                ]
            },
            {
                "titulo": "Oficinas/sucursales con mapas dinámicos",
                "descripcion": "Extraer listado de oficinas o sucursales con mapas dinámicos (Google Maps embebidos).",
                "pasos": [
                    "Entrar en página de oficinas",
                    "Identificar mapa embebido",
                    "Extraer listado de direcciones",
                    "Extraer coordenadas (si es posible)"
                ]
            },
        ],
        "Portales de empleo": [
            {
                "titulo": "Buscar ofertas avanzadas en LinkedIn Jobs",
                "descripcion": "Buscar ofertas de trabajo específicas por criterios avanzados en LinkedIn Jobs.",
                "pasos": [
                    "Acceder a LinkedIn Jobs",
                    "Definir filtros avanzados",
                    "Extraer resultados (título, empresa, localización)",
                    "Guardar enlace de cada oferta"
                ]
            },
            {
                "titulo": "Detalles de empleos en Indeed",
                "descripcion": "Extraer detalles de empleos desde Indeed (descripción, ubicación, salario).",
                "pasos": [
                    "Buscar puesto en Indeed",
                    "Extraer descripción de la oferta",
                    "Extraer ubicación",
                    "Extraer salario (si aparece)"
                ]
            },
            {
                "titulo": "Información de empresas en Glassdoor",
                "descripcion": "Obtener información dinámica sobre empresas empleadoras (perfiles completos desde Glassdoor).",
                "pasos": [
                    "Buscar empresa en Glassdoor",
                    "Extraer perfil completo",
                    "Extraer valoraciones",
                    "Extraer comentarios"
                ]
            },
        ],
        "Webs administrativas": [
            {
                "titulo": "Datos desde el BOE",
                "descripcion": "Extraer información estructurada desde el BOE o similar (licitaciones recientes).",
                "pasos": [
                    "Entrar en boe.es",
                    "Buscar boletín del día",
                    "Localizar sección de licitaciones",
                    "Extraer datos tabulares"
                ]
            },
            {
                "titulo": "Navegar formularios administrativos",
                "descripcion": "Navegar formularios administrativos para obtener información específica (cita previa médico).",
                "pasos": [
                    "Entrar en portal de salud",
                    "Navegar al formulario de cita previa",
                    "Completar campos requeridos",
                    "Extraer resultado de la cita"
                ]
            },
            {
                "titulo": "Tablas HTML dinámicas de INE",
                "descripcion": "Descargar y parsear información desde tablas HTML dinámicas de estadísticas públicas (INE).",
                "pasos": [
                    "Entrar en ine.es",
                    "Seleccionar tabla de estadísticas",
                    "Detectar carga dinámica de la tabla",
                    "Extraer datos estructurados"
                ]
            },
        ],
        "Acciones complejas": [
            {
                "titulo": "Completar formulario dependiente",
                "descripcion": "Completar formulario dinámico con pasos dependientes (selección múltiple).",
                "pasos": [
                    "Entrar en formulario",
                    "Seleccionar opciones en primer paso",
                    "Esperar carga dinámica",
                    "Completar pasos siguientes según selección",
                    "Enviar formulario"
                ]
            },
            {
                "titulo": "Navegar mediante drag & drop",
                "descripcion": "Navegar mediante drag&drop (selección interactiva tipo listas ordenables).",
                "pasos": [
                    "Entrar en web con listas ordenables",
                    "Arrastrar elementos según requerimiento",
                    "Verificar el orden final"
                ]
            },
            {
                "titulo": "Scroll infinito en Pinterest",
                "descripcion": "Manejar scroll infinito para cargar múltiples páginas de resultados en Pinterest o similar.",
                "pasos": [
                    "Entrar en pinterest.com",
                    "Buscar tema concreto",
                    "Hacer scroll varias veces",
                    "Extraer imágenes y enlaces de resultados"
                ]
            },
        ],
        "Compras online completas": [
            {
                "titulo": "Simular compra en tienda pequeña",
                "descripcion": "Simular un proceso completo en una tienda online pequeña (añadir al carrito, rellenar dirección y método de pago, sin realizar pago real).",
                "pasos": [
                    "Buscar producto",
                    "Añadir al carrito",
                    "Ir a checkout",
                    "Rellenar dirección y método de pago",
                    "Finalizar simulación sin pagar"
                ]
            },
            {
                "titulo": "Checkout múltiple en tienda grande",
                "descripcion": "Añadir múltiples artículos al carrito y simular proceso de checkout en tienda grande (Zara online).",
                "pasos": [
                    "Seleccionar varios productos",
                    "Añadir todos al carrito",
                    "Navegar al proceso de compra",
                    "Completar pasos hasta pago"
                ]
            },
            {
                "titulo": "Popups y descuentos automáticos",
                "descripcion": "Interactuar dinámicamente con popups promocionales y descuentos automáticos al hacer compras (tienda online tipo PCComponentes).",
                "pasos": [
                    "Acceder a tienda online",
                    "Detectar y cerrar popup promocional",
                    "Añadir producto con descuento al carrito",
                    "Verificar aplicación del descuento"
                ]
            },
        ],
        "Creación de perfiles": [
            {
                "titulo": "Registro en web sencilla",
                "descripcion": "Completar registro de usuario nuevo en web sencilla (WordPress estándar).",
                "pasos": [
                    "Entrar en página de registro",
                    "Completar campos básicos",
                    "Enviar formulario",
                    "Verificar creación de usuario"
                ]
            },
            {
                "titulo": "Registro complejo con validaciones",
                "descripcion": "Completar registro complejo con validaciones y captura dinámica de campos (Airbnb o Booking).",
                "pasos": [
                    "Ir a página de registro",
                    "Completar email y contraseña",
                    "Rellenar campos dinámicos requeridos",
                    "Verificar mensaje de confirmación"
                ]
            },
            {
                "titulo": "Login con verificación en dos pasos",
                "descripcion": "Automatizar login con verificación en dos pasos dinámica (correo electrónico).",
                "pasos": [
                    "Ir a login",
                    "Completar usuario y contraseña",
                    "Esperar código de verificación",
                    "Introducir código y acceder"
                ]
            },
            {
                "titulo": "Modificar perfil tras login",
                "descripcion": "Modificar dinámicamente información del perfil creado tras login.",
                "pasos": [
                    "Iniciar sesión en cuenta",
                    "Navegar a perfil",
                    "Modificar datos (nombre, email...)",
                    "Guardar cambios",
                    "Verificar que se han aplicado"
                ]
            },
        ],
    }

    # 3. Agentes
    AGENTES = [
        {"nombre": "browser-use", "descripcion": "Agente de navegación autónoma basado en comandos LLM.", "modelo_llm": "openai/gpt-4o"},
        {"nombre": "LangGraph + Playwright", "descripcion": "Framework de agentes LLM para tareas web complejas.", "modelo_llm": "openai/gpt-4"},
        {"nombre": "WebRover", "descripcion": "Agente de exploración web autónoma multi-modal.", "modelo_llm": "gemini-1.5-pro"},
        {"nombre": "Omniparser", "descripcion": "Extractor de datos universal orientado a documentos web.", "modelo_llm": "openai/gpt-3.5"},
    ]

    resumen = []

    # 1. Crear Categorías
    cat_objs = {}
    for nombre in CATEGORIAS:
        cat, _ = Categoria.objects.get_or_create(nombre=nombre)
        cat_objs[nombre] = cat
        resumen.append(f"Categoría OK: {nombre}")

    # 2. Crear Casos de Uso
    for nombre_categoria, casos in CASOS_DE_USO.items():
        categoria = cat_objs[nombre_categoria]
        for caso in casos:
            obj, created = CasoUso.objects.get_or_create(
                categoria=categoria,
                titulo=caso["titulo"],
                defaults={
                    "descripcion": caso["descripcion"],
                    "pasos_esperados": str(caso["pasos"])
                }
            )
            if created:
                resumen.append(f"Creado CasoUso: {nombre_categoria} - {caso['titulo']}")
            else:
                resumen.append(f"Ya existía CasoUso: {nombre_categoria} - {caso['titulo']}")

    # 3. Crear Agentes
    for agente in AGENTES:
        obj, created = Agente.objects.get_or_create(
            nombre=agente["nombre"],
            defaults={
                "descripcion": agente["descripcion"],
                "modelo_llm": agente["modelo_llm"]
            }
        )
        if created:
            resumen.append(f"Agente creado: {agente['nombre']}")
        else:
            resumen.append(f"Agente ya existía: {agente['nombre']}")

    return HttpResponse("<br>".join(resumen))



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