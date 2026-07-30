"""Orquestador del pipeline: conecta los nodos en orden.

Fase 1 (ACTIVA y validada):   Nodo 1 -> Nodo 2 -> Nodo 3  (+ guardado)
Fase 2 (opcional, con claves): Nodo 4 -> Nodo 5 -> Nodo 6  (Higgsfield)
Fase 3 (opcional, ffmpeg):     Nodo 7  (montaje del video final)

`ejecutar` corre la fase 1 completa. Si `generar_video=True`, intenta la fase 2
(requiere credenciales de Higgsfield). Si ademas `montar=True`, ensambla el video
final con los medios generados (Nodo 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import (
    almacenamiento,
    entrada,
    guionista,
    higgsfield,
    iterador,
    montaje,
    prompts_visuales,
)
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
    ruta_video: Path | None = None
    montaje_nota: str = ""  # aviso legible si el montaje no se pudo hacer


def ejecutar(
    tema: str,
    *,
    cfg: Config | None = None,
    idioma: str = "es",
    duracion_seg: int = 90,
    generar_video: bool = False,
    montar: bool = False,
    audio: str | None = None,
) -> ResultadoPipeline:
    cfg = cfg or Config.from_env()
    client = build_client(cfg)

    # --- Fase 1: idea -> guion -> prompts JSON validado ---
    idea = entrada.crear_idea(tema, idioma=idioma, duracion_seg=duracion_seg)
    guion = guionista.escribir_guion(idea, client, cfg.formula_path)
    guion_visual = prompts_visuales.generar_prompts(guion, client)

    ruta_guion = almacenamiento.guardar_guion(guion, cfg.output_dir)
    ruta_prompts = almacenamiento.guardar_prompts(guion_visual, cfg.output_dir)

    resultado = ResultadoPipeline(
        guion=guion,
        guion_visual=guion_visual,
        ruta_guion=ruta_guion,
        ruta_prompts=ruta_prompts,
        resultados=[],
    )

    # --- Fase 2 (opcional): iterar -> Higgsfield -> tabla final ---
    if generar_video:
        for prompt in iterador.iterar_prompts(guion_visual):
            resultado.resultados.append(higgsfield.generar_video(prompt, cfg))
        resultado.ruta_tabla = almacenamiento.guardar_tabla(
            resultado.resultados, cfg.output_dir
        )

    # --- Fase 3 (opcional): montaje del video final (Nodo 7) ---
    if montar:
        resultado.ruta_video, resultado.montaje_nota = _intentar_montaje(
            resultado.resultados, cfg, audio
        )

    return resultado


def _intentar_montaje(
    resultados: list[ResultadoEscena], cfg: Config, audio: str | None
) -> tuple[Path | None, str]:
    """Monta el video final si hay medios; si no, devuelve un aviso claro."""
    if not resultados:
        return None, (
            "No se monto el video: no hay medios. Ejecuta con Higgsfield "
            "configurado (HIGGSFIELD_API_KEY/SECRET) para generar imagenes."
        )
    con_medios = [r for r in resultados if (r.video_url or r.image_url)]
    if not con_medios:
        return None, (
            "No se monto el video: ninguna escena tiene imagen/video (revisa las "
            "credenciales de Higgsfield y los creditos disponibles)."
        )
    salida = cfg.output_dir / "video_final.mp4"
    try:
        ruta = montaje.montar_desde_resultados(resultados, salida, cfg, audio=audio)
        return ruta, ""
    except montaje.MontajeError as exc:
        return None, f"No se pudo montar el video: {exc}"
