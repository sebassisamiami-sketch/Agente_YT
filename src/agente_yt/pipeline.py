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
    intro_outro,
    iterador,
    metadatos as metadatos_mod,
    montaje,
    prompts_visuales,
    subtitulos,
    thumbnail,
    voz,
    youtube,
)
from .config import Config
from .llm import build_client
from .schemas import Guion, GuionVisual, Metadatos, ResultadoEscena


@dataclass
class ResultadoPipeline:
    guion: Guion
    guion_visual: GuionVisual
    ruta_guion: Path
    ruta_prompts: Path
    resultados: list[ResultadoEscena]
    ruta_tabla: Path | None = None
    ruta_video: Path | None = None
    ruta_voz: Path | None = None
    ruta_srt: Path | None = None
    ruta_miniatura: Path | None = None
    ruta_intro: Path | None = None
    ruta_outro: Path | None = None
    metadatos: Metadatos | None = None
    youtube_url: str = ""
    montaje_nota: str = ""  # aviso legible si el montaje no se pudo hacer
    voz_nota: str = ""  # aviso legible si la narracion no se pudo generar
    miniatura_nota: str = ""
    metadatos_nota: str = ""
    youtube_nota: str = ""


def ejecutar(
    tema: str,
    *,
    cfg: Config | None = None,
    idioma: str = "es",
    duracion_seg: int = 90,
    generar_video: bool = False,
    montar: bool = False,
    audio: str | None = None,
    narrar: bool = False,
    subtitular: bool = False,
    quemar_subtitulos: bool = False,
    musica: str | None = None,
    miniatura: bool = False,
    subir: bool = False,
    privacidad: str | None = None,
    metadatos: bool = False,
    intro_outro_activo: bool = False,
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

    # --- Nodo 12 (opcional): metadatos SEO (titulo, descripcion, tags) ---
    if metadatos:
        try:
            resultado.metadatos = metadatos_mod.generar_metadatos(guion, client)
            almacenamiento.guardar_metadatos(resultado.metadatos, cfg.output_dir)
        except ValueError as exc:
            resultado.metadatos_nota = f"No se generaron metadatos: {exc}"

    # --- Fase 2 (opcional): iterar -> Higgsfield -> tabla final ---
    if generar_video:
        for prompt in iterador.iterar_prompts(guion_visual):
            resultado.resultados.append(higgsfield.generar_video(prompt, cfg))
        resultado.ruta_tabla = almacenamiento.guardar_tabla(
            resultado.resultados, cfg.output_dir
        )

    # --- Nodo 8 (opcional): narracion de voz desde las letras del guion ---
    audio_final = audio
    if narrar:
        if audio:
            # Si el usuario ya aporto un audio explicito, no lo pisamos.
            resultado.voz_nota = "Se uso el --audio proporcionado (no se narro)."
        else:
            try:
                resultado.ruta_voz = voz.generar_voz_desde_guion(
                    guion_visual, cfg.output_dir / "voz", cfg, idioma=idioma
                )
                audio_final = str(resultado.ruta_voz)
            except voz.VozError as exc:
                resultado.voz_nota = f"No se pudo generar la voz: {exc}"

    # --- Nodo 9 (opcional): subtitulos SRT desde las letras del guion ---
    srt_para_quemar: Path | None = None
    if subtitular or quemar_subtitulos:
        try:
            resultado.ruta_srt = subtitulos.generar_srt(
                guion_visual, cfg.output_dir / "subtitulos", cfg
            )
            if quemar_subtitulos:
                srt_para_quemar = resultado.ruta_srt
        except ValueError as exc:
            resultado.montaje_nota = f"No se generaron subtitulos: {exc}"

    # --- Nodo 13 (opcional): portada (intro) y cierre (outro) ---
    if intro_outro_activo and montar:
        try:
            titulo_intro = resultado.metadatos.titulo if resultado.metadatos else tema
            resultado.ruta_intro = intro_outro.generar_intro(
                titulo_intro, cfg.output_dir / "intro", cfg, dur=cfg.intro_dur
            )
            resultado.ruta_outro = intro_outro.generar_outro(
                cfg.outro_texto, cfg.output_dir / "outro", cfg, dur=cfg.outro_dur
            )
        except montaje.MontajeError as exc:
            resultado.montaje_nota = f"No se generaron intro/outro: {exc}"

    # --- Fase 3 (opcional): montaje del video final (Nodo 7) ---
    musica_final = musica if musica is not None else (cfg.musica or None)
    if montar:
        resultado.ruta_video, nota = _intentar_montaje(
            resultado.resultados,
            cfg,
            audio_final,
            musica=musica_final,
            subtitulos_srt=srt_para_quemar,
            intro=resultado.ruta_intro,
            outro=resultado.ruta_outro,
        )
        if nota:
            resultado.montaje_nota = nota

    # --- Nodo 10 (opcional): miniatura / thumbnail ---
    if miniatura:
        try:
            resultado.ruta_miniatura = thumbnail.generar_miniatura_auto(
                resultado.resultados,
                resultado.ruta_video,
                tema,
                cfg.output_dir / "miniatura",
                cfg,
            )
        except montaje.MontajeError as exc:
            resultado.miniatura_nota = f"No se genero la miniatura: {exc}"

    # --- Nodo 11 (opcional): subida a YouTube ---
    if subir:
        if not resultado.ruta_video:
            resultado.youtube_nota = (
                "No se subio a YouTube: no hay video final (falta Higgsfield/montaje)."
            )
        else:
            meta = resultado.metadatos
            if meta:
                titulo_yt = meta.titulo
                descripcion_yt = metadatos_mod.descripcion_para_youtube(meta)
                tags_yt = meta.tags
            else:
                titulo_yt, descripcion_yt, tags_yt = tema, guion.texto, None
            try:
                resultado.youtube_url = youtube.subir_a_youtube(
                    resultado.ruta_video,
                    titulo=titulo_yt,
                    descripcion=descripcion_yt,
                    cfg=cfg,
                    tags=tags_yt,
                    miniatura=resultado.ruta_miniatura,
                    privacidad=privacidad,
                )
            except youtube.YouTubeError as exc:
                resultado.youtube_nota = f"No se pudo subir a YouTube: {exc}"

    return resultado


def _intentar_montaje(
    resultados: list[ResultadoEscena],
    cfg: Config,
    audio: str | None,
    musica: str | None = None,
    subtitulos_srt: Path | None = None,
    intro: Path | None = None,
    outro: Path | None = None,
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
        ruta = montaje.montar_desde_resultados(
            resultados,
            salida,
            cfg,
            audio=audio,
            musica=musica,
            volumen_musica=cfg.volumen_musica,
            subtitulos_srt=subtitulos_srt,
            intro=intro,
            outro=outro,
        )
        return ruta, ""
    except montaje.MontajeError as exc:
        return None, f"No se pudo montar el video: {exc}"
