"""Nodo 1: Entrada / Trigger.

Recoge la idea base del video. Aqui es un disparador manual (CLI/funcion),
pero podria sustituirse por un formulario web, un webhook, etc. Su unica
responsabilidad es producir un `IdeaBase` validado.
"""

from __future__ import annotations

from .schemas import IdeaBase


def crear_idea(tema: str, idioma: str = "es", duracion_seg: int = 90) -> IdeaBase:
    """Nodo 1: construye y valida la idea base del video."""
    return IdeaBase(tema=tema, idioma=idioma, duracion_seg=duracion_seg)
