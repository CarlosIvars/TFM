import sys
import os
import asyncio
import tiktoken
import time
# Añadir el path al repo clonado de browser-use
BROWSER_USE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../agents_repos/browser-use')
)
if BROWSER_USE_PATH not in sys.path:
    sys.path.insert(0, BROWSER_USE_PATH)

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser import BrowserProfile, BrowserSession


def limitar_prompt_tokens(prompt, model="gpt-4o", max_tokens=12000):
    """Recorta el prompt para que no exceda el límite de tokens."""
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(prompt)
    if len(tokens) > max_tokens:
        # Recorta y decodifica los tokens
        prompt = encoding.decode(tokens[:max_tokens])
    return prompt

class BrowserUseAgent:
    def __init__(self, llm_model='gpt-4o', use_vision=False):
        self.llm_model = llm_model
        self.use_vision = use_vision

    def setup(self):
        # Inicializar LLM y sesión de navegador
        self.llm = ChatOpenAI(model=self.llm_model, temperature=0.0)
        self.browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                viewport_expansion=-1,
                highlight_elements=False,
                user_data_dir=os.path.expanduser('~/.config/browseruse/profiles/default'),
            ),
        )

    async def async_run_task(self, task):
        agent = Agent(
            task=task,
            llm=self.llm,
            browser_session=self.browser_session,
            use_vision=self.use_vision,
            
        )
        await agent.run()
        # Puedes obtener resultados/logs del agente si lo necesitas (adaptar aquí)

    def run_case(self, caso_uso, pasos_esperados=None):
        self.setup()
        task_prompt = limitar_prompt_tokens(caso_uso, model=self.llm_model, max_tokens=12000)
        try:
            asyncio.run(self.async_run_task(task_prompt))
            resultado = {"exito": True, "logs": f"Task '{caso_uso}' completada"}
        except Exception as e:
            resultado = {"exito": False, "logs": str(e)}
        time.sleep(3)  # Espera 3 segundos entre llamadas para evitar rate limit
        return resultado


    def teardown(self):
        pass

if __name__ == "__main__":
    agent = BrowserUseAgent()
    # Puedes pasar el caso y los pasos aquí
    res = agent.run_case("go to https://en.wikipedia.org/wiki/Banana and click on buttons to go as fast as possible from banana to Quantum mechanics")
    print(res)
