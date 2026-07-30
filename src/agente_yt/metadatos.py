"""Nodo 12: Metadatos SEO para YouTube (LLM -> JSON).

A partir del guion, pide al LLM un titulo optimizado, una descripcion atractiva,
etiquetas (tags) y hashtags, en JSON estricto validado. Estos metadatos alimentan
la subida a YouTube (Nodo 11).
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from .llm import LLMClient
from .schemas import Guion, Metadatos

SYSTEM_PROMPT = (
    "You generate YOUTUBE METADATA for a children's educational video. "
    "Given the video script, produce SEO-friendly metadata in the SAME language "
    "as the script. Return STRICT JSON ONLY (no markdown, no commentary) with:\n"
    '{\n'
    '  "titulo": "catchy title, <= 100 chars",\n'
    '  "descripcion": "2-4 sentence description with a call to subscribe",\n'
    '  "tags": ["search", "keywords"],\n'
    '  "hashtags": ["#kids", "#songs"]\n'
    "}\n"
    "Rules: family-friendly; no clickbait lies; 5-12 tags; 3-6 hashtags; the JSON "
    "must be valid and parseable as-is."
)


def _extraer_json(texto: str) -> dict:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if fence:
        texto = fence.group(1)
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ValueError("La respuesta del LLM no contiene un objeto JSON.")
    return json.loads(texto[inicio : fin + 1])


def generar_metadatos(guion: Guion, client: LLMClient) -> Metadatos:
    """Nodo 12: genera los metadatos SEO validados a partir del guion."""
    user = (
        f"SCRIPT LANGUAGE: {guion.idioma}\n"
        f"TOPIC: {guion.tema}\n\n"
        f"SCRIPT:\n{guion.texto}\n\n"
        "Now produce the strict JSON with the YouTube metadata."
    )
    raw = client.complete(SYSTEM_PROMPT, user)
    try:
        data = _extraer_json(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            "El Nodo 12 no pudo parsear un JSON valido de la respuesta del LLM.\n"
            f"Respuesta recibida:\n{raw[:800]}"
        ) from exc
    data.setdefault("titulo", guion.tema)
    try:
        return Metadatos.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            f"El JSON del Nodo 12 no cumple el esquema Metadatos.\n{exc}"
        ) from exc


def descripcion_para_youtube(meta: Metadatos) -> str:
    """Compone la descripcion final (texto + hashtags al pie)."""
    partes = [meta.descripcion.strip()]
    if meta.hashtags:
        partes.append(" ".join(meta.hashtags))
    return "\n\n".join(p for p in partes if p)
