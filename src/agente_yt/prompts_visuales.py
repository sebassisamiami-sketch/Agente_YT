"""Nodo 3: Agente de Prompts Visuales (LLM -> JSON).

Traductor tecnico. Lee el guion, extrae SOLO las descripciones visuales, las
traduce al INGLES y las devuelve en un JSON estricto. La salida se valida
contra el esquema `GuionVisual`; este es el JSON que debe quedar perfecto
antes de conectar Higgsfield.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from .llm import LLMClient
from .schemas import Guion, GuionVisual

SYSTEM_PROMPT = (
    "You are a technical assistant that converts a children's video script into "
    "visual generation prompts. Your job:\n"
    "1. Read the script and identify each scene.\n"
    "2. For each scene, extract ONLY the visual description (characters, setting, "
    "colors, lighting, camera angle, art style).\n"
    "3. Translate every visual prompt to ENGLISH (video/image AIs work best in "
    "English), regardless of the script's language.\n"
    "4. Keep the original scene lyrics/dialogue in 'texto_escena' untouched.\n"
    "5. CHARACTER CONSISTENCY: if the script includes a character bible or fixed "
    "character traits, repeat those exact traits (age, skin, hair, eyes, outfit, "
    "art style) inside EVERY 'prompt_en', so the video AI keeps the same "
    "character across scenes.\n\n"
    "Return STRICT JSON ONLY, no markdown, no commentary, with this shape:\n"
    '{\n  "escenas": [\n'
    '    {"escena": 1, "rango_tiempo": "0:00-0:08", "texto_escena": "...", '
    '"prompt_en": "..."}\n'
    "  ]\n}\n"
    "Rules: scenes numbered 1..N with no gaps; 'prompt_en' must be in English "
    "and non-empty; output must be valid JSON parseable as-is."
)


def _extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON del texto (tolera fences de markdown)."""
    # Quita fences ```json ... ``` si los hubiera.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if fence:
        texto = fence.group(1)
    # Recorta al primer bloque {...} equilibrado por si hay texto alrededor.
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ValueError("La respuesta del LLM no contiene un objeto JSON.")
    return json.loads(texto[inicio : fin + 1])


def generar_prompts(guion: Guion, client: LLMClient) -> GuionVisual:
    """Nodo 3: convierte el guion en un `GuionVisual` validado."""
    user = (
        f"SCRIPT LANGUAGE: {guion.idioma}\n"
        f"TOPIC: {guion.tema}\n\n"
        "SCRIPT:\n"
        f"{guion.texto}\n\n"
        "Now produce the strict JSON with the visual prompts in English."
    )

    raw = client.complete(SYSTEM_PROMPT, user)

    try:
        data = _extraer_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            "El Nodo 3 no pudo parsear un JSON valido de la respuesta del LLM.\n"
            f"Respuesta recibida:\n{raw[:800]}"
        ) from exc

    data.setdefault("tema", guion.tema)
    data.setdefault("idioma", guion.idioma)

    try:
        return GuionVisual.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            "El JSON del Nodo 3 no cumple el esquema GuionVisual.\n"
            f"Errores de validacion:\n{exc}"
        ) from exc
