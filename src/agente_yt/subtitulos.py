"""Nodo 9: Subtitulos automaticos.

Genera un archivo .srt a partir de las letras del guion (Nodo 3), usando el
rango de tiempo de cada escena. Si una escena no trae rango, los tiempos se
distribuyen secuencialmente usando una duracion por defecto.

El SRT puede usarse como pista externa o quemarse en el video en el montaje
(Nodo 7).
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import Config

_RANGO = re.compile(r"(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?")


def _a_segundos(txt: str) -> float | None:
    """Convierte 'm:ss' o 'm:ss.mmm' a segundos. None si no se puede."""
    m = _RANGO.search(txt or "")
    if not m:
        return None
    minutos, seg, mms = m.group(1), m.group(2), m.group(3) or "0"
    return int(minutos) * 60 + int(seg) + float(f"0.{mms}")


def _parsear_rango(rango: str) -> tuple[float, float] | None:
    """De '0:00-0:08' -> (0.0, 8.0). None si no hay dos tiempos validos."""
    if not rango or "-" not in rango:
        return None
    ini_txt, fin_txt = rango.split("-", 1)
    ini, fin = _a_segundos(ini_txt), _a_segundos(fin_txt)
    if ini is None or fin is None or fin <= ini:
        return None
    return ini, fin


def _fmt(t: float) -> str:
    """Segundos -> 'HH:MM:SS,mmm' (formato SRT)."""
    if t < 0:
        t = 0.0
    horas = int(t // 3600)
    minutos = int((t % 3600) // 60)
    seg = int(t % 60)
    mms = int(round((t - int(t)) * 1000))
    if mms == 1000:  # redondeo al segundo
        seg += 1
        mms = 0
    return f"{horas:02d}:{minutos:02d}:{seg:02d},{mms:03d}"


def construir_entradas(guion_visual, dur_defecto: float) -> list[tuple[float, float, str]]:
    """Devuelve [(inicio, fin, texto)] para cada escena con letra."""
    entradas: list[tuple[float, float, str]] = []
    reloj = 0.0
    for e in guion_visual.escenas:
        texto = (getattr(e, "texto_escena", "") or "").strip()
        if not texto:
            continue
        rango = _parsear_rango(getattr(e, "rango_tiempo", ""))
        if rango:
            ini, fin = rango
        else:
            ini, fin = reloj, reloj + dur_defecto
        entradas.append((ini, fin, texto))
        reloj = fin
    return entradas


def generar_srt(guion_visual, salida: Path, cfg: Config | None = None) -> Path:
    """Escribe un .srt con las letras del guion. Devuelve la ruta."""
    dur = cfg.img_duration if cfg else 5.0
    entradas = construir_entradas(guion_visual, dur)
    if not entradas:
        raise ValueError("El guion no tiene letras (texto_escena) para subtitular.")

    salida = Path(salida).with_suffix(".srt")
    salida.parent.mkdir(parents=True, exist_ok=True)
    bloques = []
    for i, (ini, fin, texto) in enumerate(entradas, start=1):
        bloques.append(f"{i}\n{_fmt(ini)} --> {_fmt(fin)}\n{texto}\n")
    salida.write_text("\n".join(bloques), encoding="utf-8")
    return salida
