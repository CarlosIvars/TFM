# scripts/run_browser_agent.py
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

# Path al repo browser-use
BROWSER_USE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../agents_repos/browser-use')
)
if BROWSER_USE_PATH not in sys.path:
    sys.path.insert(0, BROWSER_USE_PATH)

from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser import BrowserProfile, BrowserSession

load_dotenv()

def limitar_prompt_tokens(prompt, model="gpt-4o", max_tokens=12000):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(prompt)
    if len(tokens) > max_tokens:
        prompt = encoding.decode(tokens[:max_tokens])
    return prompt

class BrowserUseAgent:
    def __init__(self, llm_model='gpt-4o', use_vision=False):
        self.llm_model = llm_model
        self.use_vision = use_vision

    def setup(self):
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
        return agent

    def run_case(self, caso_uso, pasos_esperados=None):
        self.setup()
        task_prompt = limitar_prompt_tokens(caso_uso, model=self.llm_model, max_tokens=12000)

        import io
        import logging

        # Configurar capturador de logs
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        formatter = logging.Formatter('%(levelname)s [%(name)s] %(message)s')
        handler.setFormatter(formatter)

        # Apuntar a todos los loggers relevantes
        for logger_name in ['browser_use', 'agent', 'controller', 'browser']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

        start = time.time()
        try:
            asyncio.run(self.async_run_task(task_prompt))
            exito = True
        except Exception as e:
            exito = False
            log_stream.write(f"\nEXCEPTION: {str(e)}\n")
        end = time.time()

        # Extraer contenido capturado
        logs = log_stream.getvalue()

        # Detach handlers
        for logger_name in ['browser_use', 'agent', 'controller', 'browser']:
            logging.getLogger(logger_name).removeHandler(handler)

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
    agent = BrowserUseAgent()
    prompt = "go to https://en.wikipedia.org/wiki/Banana and navigate to Quantum mechanics"
    res = agent.run_case(prompt)
    print(res)
