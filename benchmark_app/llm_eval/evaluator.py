from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict
from langchain_openai import AzureChatOpenAI


import os

llm = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    openai_api_version=os.environ["AZURE_OPENAI_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    openai_api_key=os.environ["AZURE_OPENAI_KEY"]
)


# --- Modelo del output del LLM ---
class PreguntaEvaluacionOutput(BaseModel):
    pregunta: str = Field(description="Texto de la pregunta evaluada")
    respuesta: str = Field(description="Respuesta del LLM (sí, no o puntuación)")

class EvaluacionLLMOutput(BaseModel):
    respuestas: List[PreguntaEvaluacionOutput] = Field(description="Respuestas para cada pregunta de evaluación")

# --- Prompt Template ---
def build_prompt(result, pasos, logs, preguntas_evaluacion):
    pasos_fmt = "\n".join([f"{i+1}. {p}" for i, p in enumerate(pasos)])
    preguntas_fmt = "\n".join([f"{i+1}. {p}" for i, p in enumerate(preguntas_evaluacion)])
    return f"""
Eres un evaluador automático de agentes web. Debes analizar la respuesta de un agente a una tarea, los logs de ejecución y los pasos esperados.
Para cada pregunta de evaluación, responde únicamente "sí", "no" o proporciona una puntuación si la pregunta lo indica.

Respuesta del agente:
\"\"\"{result}\"\"\"

Logs de ejecución:
\"\"\"{logs}\"\"\"

Pasos esperados:
{pasos_fmt}

Preguntas de evaluación:
{preguntas_fmt}

Devuelve la respuesta en el siguiente formato JSON (lista):
{{
  "respuestas": [
    {{"pregunta": "PREGUNTA1", "respuesta": "sí/no/puntuación"}},
    ...
  ]
}}
"""

# --- Evaluador LLM profesional ---
def evaluar_resultado_llm(result, pasos, logs, preguntas_evaluacion, llm=None):
    """
    Evalúa con LLM de forma profesional, devuelve dict {pregunta: respuesta}
    """
    response = llm.invoke("Dime una curiosidad sobre IA.")
    print(response.content)

    prompt_str = build_prompt(result, pasos, logs, preguntas_evaluacion)

    parser = PydanticOutputParser(pydantic_object=EvaluacionLLMOutput)

    chain = prompt_str | llm | parser

    output: EvaluacionLLMOutput = chain.invoke({})
    # Devuelve dict {pregunta: respuesta}
    return {item.pregunta: item.respuesta for item in output.respuestas}
