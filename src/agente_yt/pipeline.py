"""Orquestador del pipeline: conecta los nodos en orden.

Fase 1 (ACTIVA y validada):   Nodo 1 -> Nodo 2 -> Nodo 3  (+ guardado)
Fase 2 (stub, opcional):      Nodo 4 -> Nodo 5 -> Nodo 6  (Higgsfield)

`ejecutar` corre la fase 1 completa. Si `generar_video=True`, intenta tambien
la fase 2 (requiere credenciales de Higgsfield).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import almacenamiento, entrada, guionista, higgsfield, iterador, prompts_visuales
from .config import Config
from .llm import build_client
from .schemas import Guion, GuionVisual, ResultadoEscena


@dataclass
class ResultadoPipeline:
    guion: Guion
    guion_visual: GuionVisual
    ruta_guion: Path
    ruta_prompts: Path
    resultados: list[ResultadoEscena]
    ruta_tabla: Path | None = None


def ejecutar(
    tema: str,
    *,
    cfg: Config | None = None,
    idioma: str = "es",
    duracion_seg: int = 90,
    generar_video: bool = False,
) -> ResultadoPipeline:
    cfg = cfg or Config.from_env()
    client = build_client(cfg)

    # --- Fase 1: idea -> guion -> prompts JSON validado ---
    idea = entrada.crear_idea(tema, idioma=idioma, duracion_seg=duracion_seg)
    guion = guionista.escribir_guion(idea, client, cfg.formula_path)
    guion_visual = prompts_visuales.generar_prompts(guion, client)

    ruta_guion = almacenamiento.guardar_guion(guion, cfg.output_dir)
    ruta_prompts = almacenamiento.guardar_prompts(guion_visual, cfg.output_dir)

    # --- Fase 2 (opcional): iterar -> Higgsfield -> tabla final ---
    resultados: list[ResultadoEscena] = []
    ruta_tabla: Path | None = None
    if generar_video:
        for prompt in iterador.iterar_prompts(guion_visual):
            resultados.append(higgsfield.generar_video(prompt, cfg))
        ruta_tabla = almacenamiento.guardar_tabla(resultados, cfg.output_dir)

    return ResultadoPipeline(
        guion=guion,
        guion_visual=guion_visual,
        ruta_guion=ruta_guion,
        ruta_prompts=ruta_prompts,
        resultados=resultados,
        ruta_tabla=ruta_tabla,
    )
