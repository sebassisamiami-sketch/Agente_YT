"""Interfaz de linea de comandos del pipeline Agente_YT.

Uso tipico (modo mock, sin claves ni coste):
    python -m agente_yt "Cancion sobre lavarse los dientes para ninos de 3 anos"

Opciones:
    --idioma es|en|pt      Idioma de la letra del guion (por defecto: es)
    --duracion 90          Duracion objetivo en segundos
    --generar-video        Ejecuta tambien la fase 2 (Nodo 5: Higgsfield)
    --todo                 TODO EN UNO: guion -> Higgsfield -> montaje final
    --audio ARCHIVO        Pista de audio para el montaje (con --todo o --montar-dir)
"""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .pipeline import ejecutar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agente_yt",
        description="Pipeline por nodos para generar contenido infantil de YouTube.",
    )
    parser.add_argument(
        "tema",
        nargs="?",
        default=None,
        help="Idea base / tema del video.",
    )
    parser.add_argument(
        "--listar-motions",
        action="store_true",
        help="Lista los motion_id de Higgsfield (para animar a video) y sale.",
    )
    parser.add_argument(
        "--listar-styles",
        action="store_true",
        help="Lista los estilos Soul de Higgsfield y sale.",
    )
    # --- Nodo 7: montaje ---
    parser.add_argument(
        "--montar-dir",
        metavar="CARPETA",
        help="Nodo 7: monta los medios (imagenes/videos) de la carpeta en un MP4 y sale.",
    )
    parser.add_argument(
        "--audio", metavar="ARCHIVO", help="Pista de audio (voz/cancion) para el montaje."
    )
    parser.add_argument(
        "--salida",
        metavar="ARCHIVO",
        default=None,
        help="Ruta del video final (por defecto: salidas/video_final.mp4).",
    )
    parser.add_argument(
        "--duracion-imagen",
        type=float,
        default=None,
        help="Segundos por imagen fija en el montaje (por defecto AGENTE_YT_IMG_DURATION).",
    )
    parser.add_argument(
        "--sin-zoom",
        action="store_true",
        help="Desactiva el efecto Ken Burns (zoom) en las imagenes.",
    )
    parser.add_argument("--idioma", default="es", help="Idioma de la letra (es/en/pt).")
    parser.add_argument(
        "--duracion", type=int, default=90, help="Duracion objetivo en segundos."
    )
    parser.add_argument(
        "--generar-video",
        action="store_true",
        help="Ejecuta la fase 2 (Higgsfield). Requiere credenciales.",
    )
    parser.add_argument(
        "--todo",
        action="store_true",
        help="TODO EN UNO: guion -> prompts -> Higgsfield -> voz -> montaje final.",
    )
    parser.add_argument(
        "--narrar",
        action="store_true",
        help="Genera voz (TTS) desde las letras del guion y la usa como audio del montaje.",
    )
    parser.add_argument(
        "--subtitulos",
        action="store_true",
        help="Genera subtitulos (SRT) y los QUEMA en el video.",
    )
    parser.add_argument(
        "--srt",
        action="store_true",
        help="Genera solo el archivo de subtitulos (SRT), sin quemarlos.",
    )
    parser.add_argument(
        "--musica", metavar="ARCHIVO", help="Musica de fondo (se mezcla bajo la voz)."
    )
    parser.add_argument(
        "--volumen-musica",
        type=float,
        default=None,
        help="Volumen de la musica de fondo 0.0-1.0 (por defecto 0.18).",
    )
    parser.add_argument(
        "--lote",
        metavar="ARCHIVO",
        help="Modo lote: genera un video por cada linea del archivo de temas.",
    )
    args = parser.parse_args(argv)

    cfg = Config.from_env()
    if args.volumen_musica is not None:
        import dataclasses

        cfg = dataclasses.replace(cfg, volumen_musica=args.volumen_musica)

    # Utilidades de descubrimiento de Higgsfield (no gastan creditos).
    if args.listar_motions or args.listar_styles:
        from .higgsfield import HiggsfieldClient, HiggsfieldError

        try:
            client = HiggsfieldClient(cfg)
            datos = client.listar_motions() if args.listar_motions else client.listar_styles()
        except HiggsfieldError as exc:
            print(f"[Agente_YT] ERROR: {exc}", file=sys.stderr)
            return 1
        import json as _json

        print(_json.dumps(datos, indent=2, ensure_ascii=False))
        return 0

    # Nodo 7: montaje desde una carpeta de medios (no toca los LLM).
    if args.montar_dir:
        from .montaje import MontajeError, montar_directorio

        salida = args.salida or str(cfg.output_dir / "video_final.mp4")
        try:
            ruta = montar_directorio(
                args.montar_dir,
                salida,
                cfg,
                audio=args.audio,
                duracion_imagen=args.duracion_imagen,
                con_zoom=not args.sin_zoom,
                musica=args.musica or (cfg.musica or None),
                volumen_musica=cfg.volumen_musica,
            )
        except MontajeError as exc:
            print(f"[Agente_YT] ERROR de montaje: {exc}", file=sys.stderr)
            return 1
        print(f"[Agente_YT] Video final generado: {ruta}")
        return 0

    # Flags derivados (compartidos por modo normal y lote).
    generar_video = args.generar_video or args.todo
    montar = args.todo
    narrar = args.narrar or args.todo
    quemar_subtitulos = args.subtitulos or args.todo
    subtitular = quemar_subtitulos or args.srt

    # Modo lote: genera un video por cada tema del archivo.
    if args.lote:
        from .lote import ejecutar_lote

        try:
            items = ejecutar_lote(
                args.lote,
                cfg=cfg,
                generar_video=generar_video,
                montar=montar,
                narrar=narrar,
                subtitular=subtitular,
                quemar_subtitulos=quemar_subtitulos,
                musica=args.musica,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[Agente_YT] ERROR de lote: {exc}", file=sys.stderr)
            return 1
        print(f"\n===== MODO LOTE: {len(items)} video(s) =====")
        fallos = 0
        for it in items:
            if it.error:
                fallos += 1
                print(f"  [ERROR] {it.item.tema}: {it.error}")
            else:
                video = it.resultado.ruta_video if it.resultado else None
                print(f"  [OK] {it.item.tema} -> {it.carpeta}"
                      + (f" (video: {video})" if video else " (guion+prompts)"))
        print(f"\n[Agente_YT] Lote completado. Fallos: {fallos}/{len(items)}.")
        return 1 if fallos == len(items) else 0

    if not args.tema:
        parser.error(
            "se requiere el argumento 'tema' (o usa --listar-motions / "
            "--listar-styles / --montar-dir / --lote)"
        )

    from .llm import _resolver_modelo

    print(f"[Agente_YT] Proveedor LLM: {cfg.provider} | modelo: {_resolver_modelo(cfg)}")
    if args.todo:
        estado_hf = "SI" if cfg.higgsfield_configurado else "NO (faltan claves)"
        print(
            f"[Agente_YT] Modo TODO EN UNO | Higgsfield: {estado_hf} | "
            f"voz(TTS): {cfg.tts_provider}"
        )

    try:
        res = ejecutar(
            args.tema,
            cfg=cfg,
            idioma=args.idioma,
            duracion_seg=args.duracion,
            generar_video=generar_video,
            montar=montar,
            audio=args.audio,
            narrar=narrar,
            subtitular=subtitular,
            quemar_subtitulos=quemar_subtitulos,
            musica=args.musica,
        )
    except Exception as exc:  # noqa: BLE001 - queremos un mensaje claro en CLI
        print(f"[Agente_YT] ERROR: {exc}", file=sys.stderr)
        return 1

    print("\n===== NODO 2: GUION =====")
    print(res.guion.texto)
    print(f"\n[guardado] {res.ruta_guion}")

    print("\n===== NODO 3: PROMPTS VISUALES (JSON validado) =====")
    print(res.guion_visual.model_dump_json(indent=2))
    print(f"\n[guardado] {res.ruta_prompts}")

    if generar_video:
        print("\n===== NODOS 4-6: GENERACION Y TABLA FINAL =====")
        for r in res.resultados:
            print(
                f"  Escena {r.escena}: estado={r.estado} "
                f"img={r.image_url or '-'} video={r.video_url or '-'}"
                + (f" error={r.error}" if r.error else "")
            )
        if res.ruta_tabla:
            print(f"\n[guardado] {res.ruta_tabla}")

    if narrar:
        print("\n===== NODO 8: NARRACION DE VOZ (TTS) =====")
        if res.ruta_voz:
            print(f"[Agente_YT] Voz generada: {res.ruta_voz}")
        if res.voz_nota:
            print(f"[Agente_YT] {res.voz_nota}")

    if subtitular and res.ruta_srt:
        print("\n===== NODO 9: SUBTITULOS =====")
        print(f"[Agente_YT] SRT generado: {res.ruta_srt}"
              + (" (se quemaran en el video)" if quemar_subtitulos else ""))

    if montar:
        print("\n===== NODO 7: MONTAJE DEL VIDEO FINAL =====")
        if res.ruta_video:
            print(f"[Agente_YT] Video final generado: {res.ruta_video}")
        else:
            print(f"[Agente_YT] {res.montaje_nota}")

    print("\n[Agente_YT] Pipeline completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
