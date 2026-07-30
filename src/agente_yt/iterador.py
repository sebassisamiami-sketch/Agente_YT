"""Nodo 4: Iterador / Bucle.

Toma el GuionVisual (N escenas) y entrega los prompts uno a uno al Nodo 5,
para no saturar la herramienta de video. Aqui ya esta implementado el bucle
(es trivial); lo que se conecta despues es el Nodo 5 dentro del bucle.
"""

from __future__ import annotations

from collections.abc import Iterator

from .schemas import GuionVisual, PromptVisual


def iterar_prompts(guion_visual: GuionVisual) -> Iterator[PromptVisual]:
    """Nodo 4: cede cada prompt visual en orden de escena."""
    for prompt in guion_visual.escenas:
        yield prompt
