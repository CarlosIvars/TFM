from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
import os
import json

# --- Carga segura del LLM de Azure OpenAI ---
def _create_azure_llm():
    missing = [k for k in ["AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_VERSION", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY"] if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno para Azure OpenAI: {', '.join(missing)}")
    return AzureChatOpenAI(
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        openai_api_key=os.environ["AZURE_OPENAI_KEY"],
        temperature=0
    )

try:
    _GLOBAL_LLM = _create_azure_llm()
except Exception as e:
    _GLOBAL_LLM = None  # Permitimos cargar el módulo sin romper, la vista lo controlará.


# --- Modelo del output del LLM ---
class PreguntaEvaluacionOutput(BaseModel):
    pregunta: str = Field(description="Texto de la pregunta evaluada")
    respuesta: str = Field(description="Respuesta del LLM (sí, no o puntuación)")

class EvaluacionLLMOutput(BaseModel):
    respuestas: List[PreguntaEvaluacionOutput] = Field(description="Respuestas para cada pregunta de evaluación")


# --- Prompt ---
def build_prompt(result, pasos, logs, preguntas_evaluacion):
    pasos = pasos or []
    preguntas_evaluacion = preguntas_evaluacion or []

    pasos_fmt = "\n".join([f"{i+1}. {p}" for i, p in enumerate(pasos)])
    preguntas_fmt = "\n".join([f"{i+1}. {p}" for i, p in enumerate(preguntas_evaluacion)])

    return f"""
Eres un evaluador automático de agentes web. Debes analizar la respuesta de un agente a una tarea, los logs de ejecución y los pasos esperados.
Para cada pregunta de evaluación, responde únicamente "sí", "no" o proporciona una puntuación si la pregunta lo indica.

Respuesta del agente:
\"\"\"{result or ""}\"\"\"

Logs de ejecución:
\"\"\"{logs or ""}\"\"\"

Pasos esperados:
{pasos_fmt}

Preguntas de evaluación:
{preguntas_fmt}

Devuelve la respuesta en el siguiente formato JSON:
{{
  "respuestas": [
    {{"pregunta": "PREGUNTA1", "respuesta": "sí/no/puntuación"}}
  ]
}}
Asegúrate de que el JSON sea válido.
""".strip()


# --- Evaluador LLM ---
def evaluar_resultado_llm(result, pasos, logs, preguntas_evaluacion, llm=None):
    """
    Evalúa con LLM y devuelve un dict {pregunta: respuesta}.
    """
    _llm = llm or _GLOBAL_LLM
    if _llm is None:
        raise ValueError("LLM no configurado. Revisa variables de entorno AZURE_OPENAI_* o inicializa 'llm' al llamar.")

    prompt_str = build_prompt(result, pasos, logs, preguntas_evaluacion)
    parser = PydanticOutputParser(pydantic_object=EvaluacionLLMOutput)

    # En LangChain con ChatOpenAI/AzureChatOpenAI, pasamos una lista de mensajes:
    # Cada mensaje es (role, content) o un objeto de mensaje.
    messages = [("human", prompt_str)]
    resp = _llm.invoke(messages)              # resp.content es el texto
    content = resp.content if hasattr(resp, "content") else str(resp)

    # Intenta parsear con el parser; si falla, intenta json.loads
    try:
        parsed = parser.parse(content)
        output_dict = {item.pregunta: item.respuesta for item in parsed.respuestas}
        return output_dict
    except Exception:
        # Fallback: intentar parseo JSON manual
        try:
            data = json.loads(content)
            respuestas = data.get("respuestas", [])
            return {item.get("pregunta", ""): item.get("respuesta", "") for item in respuestas if isinstance(item, dict)}
        except Exception as e:
            raise ValueError(f"No se pudo parsear la salida del LLM como JSON válido: {e}\nContenido:\n{content[:1000]}")
