"""Interfaz de linea de comandos del pipeline Agente_YT.

Uso tipico (modo mock, sin claves ni coste):
    python -m agente_yt "Cancion sobre lavarse los dientes para ninos de 3 anos"

Opciones:
    --idioma es|en|pt      Idioma de la letra del guion (por defecto: es)
    --duracion 90          Duracion objetivo en segundos
    --generar-video        Ejecuta tambien la fase 2 (Nodo 5: Higgsfield)
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
    parser.add_argument("--idioma", default="es", help="Idioma de la letra (es/en/pt).")
    parser.add_argument(
        "--duracion", type=int, default=90, help="Duracion objetivo en segundos."
    )
    parser.add_argument(
        "--generar-video",
        action="store_true",
        help="Ejecuta la fase 2 (Higgsfield). Requiere credenciales.",
    )
    args = parser.parse_args(argv)

    cfg = Config.from_env()

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

    if not args.tema:
        parser.error("se requiere el argumento 'tema' (o usa --listar-motions/--listar-styles)")

    print(f"[Agente_YT] Proveedor LLM: {cfg.provider} | modelo: {cfg.model}")

    try:
        res = ejecutar(
            args.tema,
            cfg=cfg,
            idioma=args.idioma,
            duracion_seg=args.duracion,
            generar_video=args.generar_video,
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

    if args.generar_video:
        print("\n===== NODOS 4-6: GENERACION Y TABLA FINAL =====")
        for r in res.resultados:
            print(
                f"  Escena {r.escena}: estado={r.estado} "
                f"img={r.image_url or '-'} video={r.video_url or '-'}"
                + (f" error={r.error}" if r.error else "")
            )
        if res.ruta_tabla:
            print(f"\n[guardado] {res.ruta_tabla}")

    print("\n[Agente_YT] Pipeline (fase 1) completado con exito.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
