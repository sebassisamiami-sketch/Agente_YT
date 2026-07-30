"""Nodo 13: Portada (intro) y cierre (outro) animados.

Genera clips de video cortos con texto centrado y un fundido de entrada/salida,
usando libass (el ffmpeg estatico no trae drawtext). Estos clips se anteponen y
anaden al montaje final (Nodo 7).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Config
from .montaje import MontajeError, resolver_ffmpeg


def _run(cmd: list[str], cwd: str | None = None) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        cola = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise MontajeError(f"ffmpeg fallo generando la tarjeta:\n{cola}")


def _dims(cfg: Config) -> tuple[int, int]:
    try:
        w, h = cfg.video_size.lower().split("x")
        return int(w), int(h)
    except Exception as exc:  # noqa: BLE001
        raise MontajeError(f"AGENTE_YT_VIDEO_SIZE invalido: {cfg.video_size}") from exc


def _escapar_ass(texto: str) -> str:
    return (
        texto.replace("\\", "\\\\").replace("{", "(").replace("}", ")").strip()
    )


def _envolver(texto: str, max_chars: int = 20, max_lineas: int = 3) -> str:
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
    return "\\N".join(lineas[:max_lineas])


def _ass(texto: str, w: int, h: int, font_size: int) -> str:
    txt = _envolver(_escapar_ass(texto))
    return (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: T,Noto Sans,{font_size},&H00FFFFFF,&H000000FF,&H00000000,"
        "&H64000000,1,0,0,0,100,100,0,0,1,5,3,5,40,40,40,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:01:00.00,T,,0,0,0,,{txt}\n"
    )


def generar_tarjeta(
    texto: str,
    salida: Path,
    cfg: Config,
    *,
    dur: float = 3.0,
    color: str = "0x101820",
    font_size: int = 90,
) -> Path:
    """Crea un clip de video con `texto` centrado y fundido de entrada/salida."""
    ff = resolver_ffmpeg(cfg)
    w, h = _dims(cfg)
    fps = cfg.video_fps
    salida = Path(salida).with_suffix(".mp4")
    salida.parent.mkdir(parents=True, exist_ok=True)
    fin_fade = max(0.1, dur - 0.5)
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "card.ass").write_text(_ass(texto, w, h, font_size), encoding="utf-8")
        vf = (
            f"ass=card.ass,fade=t=in:st=0:d=0.5,"
            f"fade=t=out:st={fin_fade:.2f}:d=0.5,format=yuv420p"
        )
        _run(
            [
                ff, "-y", "-f", "lavfi",
                "-i", f"color=c={color}:s={w}x{h}:d={dur:.2f}:r={fps}",
                "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
                str(salida),
            ],
            cwd=str(tmpdir),
        )
    return salida


def generar_intro(titulo: str, salida: Path, cfg: Config, dur: float = 3.0) -> Path:
    """Portada: el titulo del video sobre fondo oscuro."""
    return generar_tarjeta(titulo, salida, cfg, dur=dur, color="0x101820")


def generar_outro(texto: str, salida: Path, cfg: Config, dur: float = 3.0) -> Path:
    """Cierre: llamada a suscribirse (u otro texto)."""
    return generar_tarjeta(texto, salida, cfg, dur=dur, color="0x7A1B2E", font_size=80)
