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

# Cargar .env y mostrar la API KEY
load_dotenv()

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser import BrowserProfile, BrowserSession

def limitar_prompt_tokens(prompt, model="gpt-4o", max_tokens=12000):
    if model == "gpt-4o":
        encoding = tiktoken.get_encoding("cl100k_base")  # Fallback explícito
    else:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")  # Backup general
    tokens = encoding.encode(prompt)
    if len(tokens) > max_tokens:
        prompt = encoding.decode(tokens[:max_tokens])
    return prompt

class BrowserUseAgent:
    def __init__(self, llm_model='gpt-4o', use_vision=True, use_azure=True):
        """
        llm_model: nombre del modelo (por ejemplo, 'gpt-4.1-nano-2025-04-14' para Azure o 'gpt-4o' para OpenAI)
        use_azure: True si quieres Azure OpenAI, False para OpenAI normal
        """
        print(f"DEBUG: __init__ llm_model={llm_model}, use_vision={use_vision}, use_azure={use_azure}")
        self.llm_model = llm_model
        self.use_vision = use_vision
        self.use_azure = use_azure
        self.llm = None

    def setup(self):
        print("DEBUG: Entrando en setup()")
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

        # Aquí la sesión del browser (esto parece OK)
        try:
            self.browser_session = BrowserSession(
                browser_profile=BrowserProfile(
                    viewport_expansion=-1,
                    highlight_elements=False,
                    user_data_dir=os.path.expanduser('~/.config/browseruse/profiles/default'),
                ),
            )
            print("DEBUG: BrowserSession inicializado correctamente")
        except Exception as e:
            print(f"EXCEPTION inicializando BrowserSession: {e}")
            raise

    async def async_run_task(self, task):
        print("DEBUG: Entrando en async_run_task()")
        agent = Agent(
            task=task,
            llm=self.llm,
            browser_session=self.browser_session,
            use_vision=self.use_vision,
        )
        print("DEBUG: Agent creado, lanzando run()")
        await agent.run()
        print("DEBUG: Agent.run() completado")
        return agent

    def run_case(self, prompt_text: str, pasos_esperados=None):
        print("DEBUG: Entrando en run_case()")
        self.setup()
        print("DEBUG: setup() OK, preprocesando prompt...")
        # aquí solo pasas el nombre del modelo, no el objeto
        task_prompt = limitar_prompt_tokens(prompt_text, model=self.llm_model, max_tokens=12000)
        print(f"DEBUG: Prompt final: {task_prompt[:60]}...")

        # ... resto de tu código idéntico ...
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        formatter = logging.Formatter('%(levelname)s [%(name)s] %(message)s')
        handler.setFormatter(formatter)

        for logger_name in ['browser_use', 'agent', 'controller', 'browser']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

        start = time.time()
        try:
            print("DEBUG: Lanzando asyncio.run(async_run_task())")
            asyncio.run(self.async_run_task(task_prompt))
            exito = True
            print("DEBUG: Ejecución exitosa")
        except Exception as e:
            exito = False
            print(f"EXCEPTION EN run_case: {e}")
            log_stream.write(f"\nEXCEPTION: {str(e)}\n")
        end = time.time()

        logs = log_stream.getvalue()
        print("DEBUG: LOGS CAPTURADOS:\n", logs[-500:])  # Últimas 500 chars

        for logger_name in ['browser_use', 'agent', 'controller', 'browser']:
            logging.getLogger(logger_name).removeHandler(handler)

        print("DEBUG: Fin run_case()")
        return {
            "exito": exito,
            "respuesta": None,
            "acciones_realizadas": None,
            "tiempo_total_seg": round(end - start, 2),
            "logs": logs or "Sin logs",
            "urls_visitadas": [],
            "cpu_usado": 0.0,
            "ram_usada_mb": 0.0,
            "fecha": time.strftime('%Y-%m-%dT%H:%M:%S'),
        }

if __name__ == "__main__":
    print("DEBUG: MAIN ejecutando ejemplo de uso")
    agent = BrowserUseAgent(
        llm_model='gpt-4.1-nano-2025-04-14',  # tu modelo de Azure OpenAI
        use_azure=True
    )
    prompt = "go to https://en.wikipedia.org/wiki/Banana and navigate to Quantum mechanics"
    res = agent.run_case(prompt)
    print("DEBUG: RESULTADO FINAL:", res)
