import sys
import os
import asyncio
import tiktoken
import time
import psutil
import tracemalloc
from dotenv import load_dotenv
from datetime import datetime
import logging
import io

print("=== INICIANDO SCRIPT run_browser_agent.py ===")

# Path al repo browser-use
BROWSER_USE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../agents_repos/browser-use')
)
print(f"DEBUG: BROWSER_USE_PATH = {BROWSER_USE_PATH}")
if BROWSER_USE_PATH not in sys.path:
    sys.path.insert(0, BROWSER_USE_PATH)
    print(f"DEBUG: Añadido {BROWSER_USE_PATH} a sys.path")

print("DEBUG: sys.path[0:3] =", sys.path[0:3])
print("DEBUG: CWD =", os.getcwd())

# Cargar .env
load_dotenv()

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from browser_use import Agent
from browser_use.browser import BrowserProfile, BrowserSession

# =========================
# Stealth init script
# =========================
STEALTH_JS = r"""
// Quitar webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
// chrome runtime stub
window.chrome = { runtime: {} };
// Idiomas coherentes
Object.defineProperty(navigator, 'languages', { get: () => ['es-ES','es'] });
Object.defineProperty(navigator, 'language',  { get: () => 'es-ES' });
// Plataforma típica desktop
Object.defineProperty(navigator, 'platform',  { get: () => 'Win32' });

// WebGL vendor/renderer plausibles
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
  if (parameter === 37445) return 'Intel Inc.';               // UNMASKED_VENDOR_WEBGL
  if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
  return getParameter.call(this, parameter);
};

// permissions.query normalizado para notifications
const origQuery = navigator.permissions && navigator.permissions.query ?
  navigator.permissions.query.bind(navigator.permissions) : null;
if (origQuery) {
  navigator.permissions.query = (p) =>
    p && p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : origQuery(p);
}
"""

def limitar_prompt_tokens(prompt, model="gpt-4o", max_tokens=12000):
    if model == "gpt-4o":
        encoding = tiktoken.get_encoding("cl100k_base")
    else:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(prompt)
    if len(tokens) > max_tokens:
        prompt = encoding.decode(tokens[:max_tokens])
    return prompt


class BrowserUseAgent:
    def __init__(self, llm_model='gpt-4o', use_vision=False, use_azure=True):
        """
        llm_model: nombre del modelo ('gpt-4o' o despliegue Azure)
        use_azure: True para Azure OpenAI, False para OpenAI directo
        """
        print(f"DEBUG: __init__ llm_model={llm_model}, use_vision={use_vision}, use_azure={use_azure}")
        self.llm_model = llm_model
        self.use_vision = use_vision
        self.use_azure = use_azure
        self.llm = None
        self.browser_session = None

    def _build_profile(self) -> BrowserProfile:
        """Perfil de navegador más 'humano' y coherente para prod."""
        headless = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
        # Si tienes Google Chrome instalado en el server, usa 'chrome'; si no, deja 'chromium'
        channel = os.getenv("BROWSER_CHANNEL", "chromium")
        # Proxy residencial opcional por env (HTTP_PROXY o HTTPS_PROXY)
        proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None

        ua = os.getenv("BROWSER_UA") or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        profile = BrowserProfile(
            # Render/headless
            headless=headless,
            channel=channel,

            # Viewport & ventana
            window_size={'width': 1920, 'height': 1080},
            device_scale_factor=1.0,
            no_viewport=None,           # auto según headless

            # Idioma / zona horaria
            locale=os.getenv("LOCALE", "es-ES"),
            timezone_id=os.getenv("TZ", "Europe/Madrid"),
            permissions=['clipboard-read','clipboard-write','notifications'],

            # Headers/UA coherentes
            user_agent=ua,
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9"
            },

            # Perfil persistente
            user_data_dir=os.path.expanduser('~/.config/browseruse/profiles/default'),

            # Evita navegar como un clic-bot (más pausa entre acciones)
            wait_between_actions=1.0,

            # Quita solo flags cantosas (mantén el resto por estabilidad)
            ignore_default_args=[
                '--enable-automation',
                '--disable-extensions',
                '--disable-blink-features=AutomationControlled',
            ],

            # UI del agente
            highlight_elements=False,
            viewport_expansion=-1,
        )

        if proxy_url:
            # playwright ProxySettings: {"server": "http://host:port", "username": "...", "password": "..."}
            profile.proxy = {"server": proxy_url}

        return profile

    def setup(self):
        print("DEBUG: Entrando en setup()")
        # LLM
        if self.use_azure:
            print("DEBUG: Usando AzureChatOpenAI")
            self.llm = AzureChatOpenAI(
                azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                openai_api_version=os.environ["AZURE_OPENAI_VERSION"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                openai_api_key=os.environ["AZURE_OPENAI_KEY"],
                temperature=0.0
            )
        else:
            print("DEBUG: Usando OpenAI directo")
            self.llm = ChatOpenAI(
                model=self.llm_model,
                temperature=0.0
            )
        print("DEBUG: LLM inicializado correctamente")

        # Browser session con perfil endurecido
        try:
            profile = self._build_profile()
            self.browser_session = BrowserSession(
                browser_profile=profile,
            )
            print("DEBUG: BrowserSession inicializado correctamente")
        except Exception as e:
            print(f"EXCEPTION inicializando BrowserSession: {e}")
            raise

    def _extract_run_data(self, agent):
        h = agent.state.history
        final_result = h.final_result()

        steps = []
        for i, item in enumerate(h.history):
            actions = []
            if item.model_output and item.model_output.action:
                actions = [a.model_dump(exclude_unset=True) for a in item.model_output.action]
            results = []
            if item.result:
                results = [r.model_dump(exclude_none=True) for r in item.result]

            steps.append({
                "step": i + 1,
                "url": getattr(item.state, "url", None),
                "title": getattr(item.state, "title", None),
                "actions": actions,
                "results": results,
            })

        return {
            "task": agent.task,
            "model": getattr(agent, "model_name", None),
            "success": h.is_successful(),
            "errors": h.errors(),
            "urls_visited": h.urls(),
            "total_input_tokens": h.total_input_tokens(),
            "total_duration_seconds": h.total_duration_seconds(),
            "steps": steps,
            "final_result": final_result,
        }

    async def _on_step_start_stealth(self, agent_obj: Agent):
        """Hook: se ejecuta antes de cada step. Inyecta stealth 1 sola vez."""
        try:
            if not getattr(agent_obj, "_stealth_injected", False):
                ctx = agent_obj.browser_session.browser_context
                if ctx is not None:
                    await ctx.add_init_script(STEALTH_JS)
                    agent_obj._stealth_injected = True
                    logging.getLogger("browser").info("🔒 Stealth init script inyectado en el contexto.")
        except Exception as e:
            logging.getLogger("browser").warning(f"No se pudo inyectar stealth: {e}")

    async def async_run_task(self, task):
        print("DEBUG: Entrando en async_run_task()")

        # Ajustes de agente: usa_vision=False (evita subir imágenes) y
        # puedes desactivar memoria/planner si quieres minimizar contexto.
        agent = Agent(
            task=task,
            llm=self.llm,
            browser_session=self.browser_session,
            use_vision=self.use_vision,     # por defecto False aquí
            # enable_memory=False,
            # planner_llm=None,
            # max_input_tokens=110_000,
            # max_actions_per_step=6,
        )

        print("DEBUG: Agent creado, lanzando run()")
        await agent.run(
            on_step_start=self._on_step_start_stealth,  # stealth antes del primer step
        )

        run_data = self._extract_run_data(agent)
        print("DEBUG: Agent.run() completado")
        print(run_data)
        return run_data

    def run_case(self, prompt_text: str, pasos_esperados=None):
        print("DEBUG: Entrando en run_case()")
        self.setup()
        print("DEBUG: setup() OK, preprocesando prompt...")
        task_prompt = limitar_prompt_tokens(prompt_text, model=self.llm_model, max_tokens=12000)
        print(f"DEBUG: Prompt final: {task_prompt[:60]}...")

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        formatter = logging.Formatter('%(levelname)s [%(name)s] %(message)s')
        handler.setFormatter(formatter)

        for logger_name in ['browser_use', 'agent', 'controller', 'browser']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

        try:
            print("DEBUG: Lanzando asyncio.run(async_run_task())")
            run_data = asyncio.run(self.async_run_task(task_prompt))
            exito = run_data["success"]
            print("DEBUG: Ejecución exitosa")
        except Exception as e:
            exito = False
            run_data = {}
            print(f"EXCEPTION EN run_case: {e}")
            log_stream.write(f"\nEXCEPTION: {str(e)}\n")

        logs = log_stream.getvalue()
        print("DEBUG: LOGS CAPTURADOS:\n", logs[-500:])

        for logger_name in ['browser_use', 'agent', 'controller', 'browser']:
            logging.getLogger(logger_name).removeHandler(handler)

        print("DEBUG: Fin run_case()")
        return {
            "exito": exito,
            "respuesta": run_data.get("final_result"),
            "acciones_realizadas": run_data.get("steps"),
            "tiempo_total_seg": run_data.get("total_duration_seconds"),
            "logs": logs or "Sin logs",
            "urls_visitadas": run_data.get("urls_visited"),
            "cpu_usado": run_data.get("cpu_usado", 0.0),
            "ram_usada_mb": run_data.get("ram_usada_mb", 0.0),
            "fecha": time.strftime('%Y-%m-%dT%H:%M:%S'),
        }


if __name__ == "__main__":
    print("DEBUG: MAIN ejecutando ejemplo de uso")
    agent = BrowserUseAgent(
        llm_model='gpt-4.1-nano-2025-04-14',
        use_azure=True,
        use_vision=False
    )
    prompt = "go to https://en.wikipedia.org/wiki/Banana and navigate to Quantum mechanics"
    res = agent.run_case(prompt)
    print("DEBUG: RESULTADO FINAL:", res)
