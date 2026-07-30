"""Modo lote: genera varios videos a partir de una lista de temas.

Lee un archivo de texto donde cada linea es un video a producir. Formato:

    Cancion de los colores | es | 60
    Contar hasta cinco | es | 90
    Song about brushing teeth | en

Solo el tema es obligatorio; idioma y duracion son opcionales (por defecto
es / 90). Las lineas vacias o que empiezan por '#' se ignoran.

Cada video se genera en su propia subcarpeta dentro de la carpeta de salida.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .pipeline import ResultadoPipeline, ejecutar


@dataclass
class ItemLote:
    tema: str
    idioma: str = "es"
    duracion_seg: int = 90


@dataclass
class ResultadoItemLote:
    item: ItemLote
    carpeta: Path
    resultado: ResultadoPipeline | None = None
    error: str = ""


def _slug(texto: str, maxlen: int = 40) -> str:
    """Convierte un tema en un nombre de carpeta seguro."""
    s = texto.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:maxlen].rstrip("-")) or "video"


def parsear_linea(linea: str) -> ItemLote | None:
    """Convierte una linea del archivo en un ItemLote (o None si se ignora)."""
    linea = linea.strip()
    if not linea or linea.startswith("#"):
        return None
    partes = [p.strip() for p in linea.split("|")]
    tema = partes[0]
    if not tema:
        return None
    idioma = partes[1] if len(partes) > 1 and partes[1] else "es"
    duracion = 90
    if len(partes) > 2 and partes[2]:
        try:
            duracion = int(partes[2])
        except ValueError:
            duracion = 90
    return ItemLote(tema=tema, idioma=idioma, duracion_seg=duracion)


def cargar_items(archivo: Path | str) -> list[ItemLote]:
    ruta = Path(archivo)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo de lote: {ruta}")
    items: list[ItemLote] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        item = parsear_linea(linea)
        if item:
            items.append(item)
    if not items:
        raise ValueError(f"El archivo de lote no tiene temas validos: {ruta}")
    return items


def ejecutar_lote(
    archivo: Path | str,
    *,
    cfg: Config | None = None,
    generar_video: bool = False,
    montar: bool = False,
    narrar: bool = False,
    subtitular: bool = False,
    quemar_subtitulos: bool = False,
    musica: str | None = None,
    audio: str | None = None,
    miniatura: bool = False,
    subir: bool = False,
    privacidad: str | None = None,
) -> list[ResultadoItemLote]:
    """Ejecuta el pipeline para cada tema del archivo, en su propia subcarpeta."""
    cfg = cfg or Config.from_env()
    items = cargar_items(archivo)
    base = cfg.output_dir / "lote"
    resultados: list[ResultadoItemLote] = []

    for i, item in enumerate(items, start=1):
        carpeta = base / f"{i:02d}_{_slug(item.tema)}"
        cfg_item = dataclasses.replace(cfg, output_dir=carpeta)
        try:
            res = ejecutar(
                item.tema,
                cfg=cfg_item,
                idioma=item.idioma,
                duracion_seg=item.duracion_seg,
                generar_video=generar_video,
                montar=montar,
                narrar=narrar,
                subtitular=subtitular,
                quemar_subtitulos=quemar_subtitulos,
                musica=musica,
                audio=audio,
                miniatura=miniatura,
                subir=subir,
                privacidad=privacidad,
            )
            resultados.append(ResultadoItemLote(item=item, carpeta=carpeta, resultado=res))
        except Exception as exc:  # noqa: BLE001 - un item fallido no corta el lote
            resultados.append(
                ResultadoItemLote(item=item, carpeta=carpeta, error=str(exc))
            )
    return resultados
