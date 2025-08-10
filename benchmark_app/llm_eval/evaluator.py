# benchmark_app/llm_eval/evaluator.py
import os, json

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage


def _create_azure_llm():
    # Variables necesarias: AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_VERSION, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY
    return AzureChatOpenAI(
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        openai_api_key=os.environ["AZURE_OPENAI_KEY"],
        temperature=0,
        max_retries=6,
        request_timeout=90,
    )


def _extract_json_block(text: str):
    """
    Extrae el primer objeto JSON { ... } válido de 'text' sin regex recursivos.
    Si no hay, lanza ValueError.
    """
    text = text.strip()
    # 1) Intento directo
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) Quitar fences ```...``` si los hubiera
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except Exception:
            pass

    # 3) Buscar el primer bloque balanceado
    n = len(text)
    i = 0
    while i < n:
        start = text.find("{", i)
        if start == -1:
            break
        depth = 0
        in_str = False
        esc = False
        j = start
        while j < n:
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : j + 1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            break
            j += 1
        i = start + 1
    raise ValueError("No se encontró JSON válido en la salida.")


def _norm_yes(x: str) -> str:
    s = (x or "").strip().lower()
    return "si" if s in {"si", "sí", "yes", "y", "true", "1"} else "no"


def evaluar_llm_sobre_pasos_y_satisfaccion(*, respuesta_agente: str, logs: str, pasos: list[str]):
    """
    Devuelve (respuestas_pasos: List['si'|'no'], satisfaccion: int 1..5)
    SIEMPRE devuelve len(pasos) respuestas y una satisfacción válida.
    """
    llm = _create_azure_llm()

    k = len(pasos)
    pasos_fmt = "\n".join(f"{i+1}. {p}" for i, p in enumerate(pasos))

    prompt = f"""
Eres un evaluador automático. Lee la respuesta del agente, sus logs y los PASOS ESPERADOS.

Debes contestar:
1) Para CADA paso (hay exactamente {k}), responde solo "sí" o "no" según si el agente lo cumplió.
2) Da un NIVEL DE SATISFACCIÓN GLOBAL 1–5 (entero).

REGLAS:
- Si no hay información suficiente sobre un paso, responde "no".
- Si dudas en la satisfacción, responde 3.
- Devuelve **JSON VÁLIDO** sin texto extra, con este formato EXACTO:
{{
  "pasos": ["sí" | "no", ... {k} elementos ...],
  "satisfaccion": 1 | 2 | 3 | 4 | 5
}}

Respuesta del agente:
\"\"\"{respuesta_agente or ""}\"\"\"

Logs:
\"\"\"{logs or ""}\"\"\"

Pasos esperados:
{pasos_fmt}
""".strip()

    msg = HumanMessage(content=prompt)
    resp = llm.invoke([msg])
    content = getattr(resp, "content", str(resp))

    # Parse robusto
    try:
        data = _extract_json_block(content)
    except Exception:
        data = {}

    pasos_out = data.get("pasos", [])
    if not isinstance(pasos_out, list):
        pasos_out = []

    # Normaliza y garantiza longitud == k
    pasos_out = [ _norm_yes(v) for v in pasos_out ]
    if len(pasos_out) < k:
        pasos_out += ["no"] * (k - len(pasos_out))
    elif len(pasos_out) > k:
        pasos_out = pasos_out[:k]

    # Satisfacción
    satisfaccion = data.get("satisfaccion", 3)
    try:
        satisfaccion = int(satisfaccion)
    except Exception:
        satisfaccion = 3
    if satisfaccion < 1 or satisfaccion > 5:
        satisfaccion = 3

    return pasos_out, satisfaccion
