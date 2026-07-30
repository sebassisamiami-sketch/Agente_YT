"""Nodo 2: Agente Guionista (LLM).

Cerebro creativo. Toma la IdeaBase y, usando la "formula Cocomelon" como
System Prompt, escribe el guion completo con escenas detalladas.
"""

from __future__ import annotations

from pathlib import Path

from .llm import LLMClient
from .schemas import Guion, IdeaBase

_IDIOMAS = {
    "es": "espanol",
    "en": "ingles",
    "pt": "portugues",
    "fr": "frances",
}


def _cargar_formula(formula_path: Path) -> str:
    if formula_path.exists():
        return formula_path.read_text(encoding="utf-8")
    # Respaldo minimo por si falta el archivo de configuracion.
    return (
        "Eres un guionista de contenido infantil educativo estilo Cocomelon. "
        "Escribe un guion por escenas con LETRA y ACCION VISUAL, rimas simples, "
        "repeticion y un solo mensaje educativo."
    )


def escribir_guion(idea: IdeaBase, client: LLMClient, formula_path: Path) -> Guion:
    """Nodo 2: genera el guion a partir de la idea base."""
    system = _cargar_formula(formula_path)
    idioma_txt = _IDIOMAS.get(idea.idioma, idea.idioma)

    user = (
        f"IDEA BASE: {idea.tema}\n"
        f"IDIOMA DE LA LETRA: {idioma_txt}\n"
        f"DURACION OBJETIVO: {idea.duracion_seg} segundos\n\n"
        "Escribe el guion completo dividido en escenas numeradas. Para cada "
        "escena incluye su rango de tiempo, la LETRA/DIALOGO y la ACCION VISUAL "
        "detallada. Recuerda: descripciones visuales concretas y filmables."
    )

    texto = client.complete(system, user).strip()
    return Guion(tema=idea.tema, idioma=idea.idioma, texto=texto)
