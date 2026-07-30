"""Nodo 6: Almacenamiento / Salida.

Guarda los artefactos del pipeline en disco (JSON) y, en fase posterior, podria
volcar la tabla final (Escena | Texto | Link) a Google Sheets / Notion / Airtable.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .schemas import Guion, GuionVisual, ResultadoEscena


def _asegurar_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def guardar_guion(guion: Guion, output_dir: Path) -> Path:
    _asegurar_dir(output_dir)
    ruta = output_dir / "guion.json"
    ruta.write_text(
        guion.model_dump_json(indent=2, exclude_none=True), encoding="utf-8"
    )
    return ruta


def guardar_prompts(guion_visual: GuionVisual, output_dir: Path) -> Path:
    """Guarda el JSON clave del Nodo 3 (el que debe quedar perfecto)."""
    _asegurar_dir(output_dir)
    ruta = output_dir / "prompts.json"
    ruta.write_text(
        guion_visual.model_dump_json(indent=2, exclude_none=True), encoding="utf-8"
    )
    return ruta


def guardar_tabla(resultados: list[ResultadoEscena], output_dir: Path) -> Path:
    """Tabla final Escena | Texto | Link (CSV local, sustituible por Sheets/Notion)."""
    _asegurar_dir(output_dir)
    ruta = output_dir / "tabla_final.csv"
    with ruta.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["escena", "texto_escena", "prompt_en", "video_url", "estado"])
        for r in resultados:
            writer.writerow(
                [r.escena, r.texto_escena, r.prompt_en, r.video_url, r.estado]
            )
    return ruta
