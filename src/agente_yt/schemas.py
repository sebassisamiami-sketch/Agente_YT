"""Esquemas de datos del pipeline (validacion estricta con pydantic).

Estos modelos son el "contrato" que viaja entre nodos. Que el JSON de salida
sea PERFECTO es justo el punto que hay que blindar antes de conectar Higgsfield,
por eso todo pasa por validacion aqui.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class IdeaBase(BaseModel):
    """Salida del Nodo 1 (Entrada / Trigger)."""

    tema: str = Field(..., min_length=3, description="Tema/idea base del video.")
    idioma: str = Field(
        default="es",
        description="Idioma de la LETRA del guion (ISO: es, en, pt...).",
    )
    duracion_seg: int = Field(
        default=90,
        ge=15,
        le=600,
        description="Duracion objetivo del video en segundos.",
    )

    @field_validator("tema")
    @classmethod
    def _tema_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El tema no puede estar vacio.")
        return v


class Guion(BaseModel):
    """Salida del Nodo 2 (Agente Guionista).

    El guion humano completo se guarda en `texto`. La lista `escenas` es una
    troceada opcional; si el guionista no la separa, el Nodo 3 se encarga.
    """

    tema: str
    idioma: str
    texto: str = Field(..., min_length=1, description="Guion completo legible.")


class PromptVisual(BaseModel):
    """Un prompt visual listo para una IA de video (Nodo 3).

    Regla del pipeline: `prompt_en` SIEMPRE en ingles (las IA de video rinden
    mejor en ingles); `texto_escena` conserva la letra/dialogo original.
    """

    escena: int = Field(..., ge=1, description="Numero de escena (1-indexado).")
    rango_tiempo: str = Field(
        default="",
        description="Rango de tiempo aprox. de la escena, ej: '0:00-0:08'.",
    )
    texto_escena: str = Field(
        default="",
        description="Letra/dialogo de la escena, en el idioma original.",
    )
    prompt_en: str = Field(
        ...,
        min_length=1,
        description="Prompt visual EN INGLES para la IA de video/imagen.",
    )

    @field_validator("prompt_en")
    @classmethod
    def _prompt_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("prompt_en no puede estar vacio.")
        return v


class GuionVisual(BaseModel):
    """Coleccion validada de prompts visuales: la salida clave del Nodo 3.

    Este es el JSON que debe quedar 'perfecto' antes de conectar Higgsfield.
    """

    tema: str
    idioma: str
    escenas: list[PromptVisual] = Field(..., min_length=1)

    @field_validator("escenas")
    @classmethod
    def _numeracion_correlativa(cls, v: list[PromptVisual]) -> list[PromptVisual]:
        numeros = [e.escena for e in v]
        if numeros != list(range(1, len(v) + 1)):
            raise ValueError(
                f"Las escenas deben numerarse 1..N sin huecos ni repetidos; "
                f"se recibio: {numeros}"
            )
        return v


class ResultadoEscena(BaseModel):
    """Fila de la tabla final (Nodo 6): Escena | Texto | Link del video."""

    escena: int
    texto_escena: str = ""
    prompt_en: str = ""
    video_url: str = ""
    estado: str = "pendiente"  # pendiente | generando | listo | error
