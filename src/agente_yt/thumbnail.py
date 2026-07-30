"""Nodo 10: Miniatura / Thumbnail para YouTube.

Genera una miniatura 1280x720 (formato estandar de YouTube) a partir de una
imagen base (una escena generada por Higgsfield o un fotograma del video final)
con el TITULO superpuesto en grande.

Como el ffmpeg estatico no incluye `drawtext`, el texto se dibuja con libass
(filtro `ass`), que ya usamos para los subtitulos y toma una fuente del sistema
via fontconfig.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Config
from .montaje import MontajeError, resolver_ffmpeg

ANCHO, ALTO = 1280, 720


def _run(cmd: list[str], cwd: str | None = None) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        cola = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise MontajeError(f"ffmpeg fallo generando la miniatura:\n{cola}")


def _escapar_ass(texto: str) -> str:
    """Escapa caracteres conflictivos para un evento ASS."""
    return (
        texto.replace("\\", "\\\\")
        .replace("{", "(")
        .replace("}", ")")
        .replace("\n", " ")
        .strip()
    )


def _envolver(texto: str, max_chars: int = 16, max_lineas: int = 3) -> str:
    """Parte el titulo en varias lineas (separador ASS '\\N')."""
    palabras = texto.split()
    lineas: list[str] = []
    actual = ""
    for p in palabras:
        if actual and len(actual) + 1 + len(p) > max_chars:
            lineas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = lineas[-1] + "..."
    return "\\N".join(lineas)


def _construir_ass(titulo: str, font_size: int = 84) -> str:
    """Devuelve el contenido de un archivo ASS con el titulo estilizado."""
    texto = _envolver(_escapar_ass(titulo))
    # Colores ASS: &HAABBGGRR. Blanco con borde negro grueso y sombra.
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {ANCHO}\n"
        f"PlayResY: {ALTO}\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Titulo,Noto Sans,{font_size},&H00FFFFFF,&H000000FF,&H00000000,"
        "&H64000000,1,0,0,0,100,100,0,0,1,6,4,2,60,60,60,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:10.00,Titulo,,0,0,0,,{texto}\n"
    )


def frame_de_video(cfg: Config, video: Path | str, destino: Path) -> Path:
    """Extrae un fotograma del video (aprox. 1 s) como imagen base."""
    ff = resolver_ffmpeg(cfg)
    destino = Path(destino).with_suffix(".png")
    destino.parent.mkdir(parents=True, exist_ok=True)
    _run([ff, "-y", "-ss", "1", "-i", str(video), "-frames:v", "1", str(destino)])
    return destino


def generar_miniatura(
    imagen_base: Path | str,
    titulo: str,
    salida: Path,
    cfg: Config,
) -> Path:
    """Crea una miniatura 1280x720 con el titulo superpuesto."""
    ff = resolver_ffmpeg(cfg)
    base = Path(imagen_base)
    if not base.exists():
        raise MontajeError(f"No existe la imagen base de la miniatura: {base}")
    salida = Path(salida).with_suffix(".jpg")
    salida.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        ass = tmpdir / "titulo.ass"
        ass.write_text(_construir_ass(titulo), encoding="utf-8")
        # Rellena el encuadre (crop) y superpone el titulo.
        vf = (
            f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,"
            f"crop={ANCHO}:{ALTO},ass=titulo.ass"
        )
        # Copiamos la base al tmp para que el filtro (con cwd=tmp) la encuentre.
        base_local = tmpdir / f"base{base.suffix.lower() or '.png'}"
        shutil.copyfile(base, base_local)
        _run(
            [
                ff, "-y", "-i", base_local.name,
                "-vf", vf, "-frames:v", "1", "-q:v", "2",
                str(salida),
            ],
            cwd=str(tmpdir),
        )
    return salida


def generar_miniatura_auto(
    resultados,  # list[ResultadoEscena]
    ruta_video: Path | None,
    titulo: str,
    salida: Path,
    cfg: Config,
) -> Path:
    """Elige una imagen base automaticamente y genera la miniatura.

    Prioridad de la imagen base:
      1. La imagen (image_url) de la primera escena con medio, si es local.
      2. Un fotograma extraido del video final.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        base: Path | None = None

        for r in resultados or []:
            url = getattr(r, "image_url", "") or ""
            if not url:
                continue
            if url.startswith("http://") or url.startswith("https://"):
                from .montaje import _descargar

                base = _descargar(url, tmpdir / "base.png")
            elif Path(url).exists():
                base = Path(url)
            if base:
                break

        if base is None and ruta_video and Path(ruta_video).exists():
            base = frame_de_video(cfg, ruta_video, tmpdir / "frame.png")

        if base is None:
            raise MontajeError(
                "No hay imagen base para la miniatura (ni escenas con imagen ni "
                "video final)."
            )
        return generar_miniatura(base, titulo, salida, cfg)
