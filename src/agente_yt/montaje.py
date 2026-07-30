"""Nodo 7: Montaje final (ffmpeg).

Este es el "Paso 5" que el video de origen ni mostraba: ensamblar los clips /
imagenes generados en un video final listo para subir a YouTube.

Que hace:
  - Toma una lista ordenada de medios (imagenes y/o videos), locales o por URL.
  - Normaliza todo a la misma resolucion/fps (por defecto 1920x1080 @ 30 fps).
  - A las IMAGENES fijas les aplica un suave efecto Ken Burns (zoom lento) para
    dar movimiento (opcional).
  - Concatena los segmentos y, si se pasa un audio (voz o cancion), lo mezcla.
  - Exporta un MP4 (H.264 + AAC) apto para YouTube.

No depende de una version concreta de ffmpeg instalada: busca el binario en
AGENTE_YT_FFMPEG, luego en el PATH, y como ultimo recurso el que trae el paquete
opcional "imageio-ffmpeg".
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import Config

_EXT_VIDEO = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class MontajeError(RuntimeError):
    """Error durante el montaje con ffmpeg."""


@dataclass
class Clip:
    """Un medio de entrada para el montaje."""

    ruta: str  # ruta local o URL http(s)
    duracion: float = 5.0  # segundos (solo se usa para imagenes fijas)
    con_zoom: bool = True  # efecto Ken Burns en imagenes


# ------------------------------------------------------------------ ffmpeg
def resolver_ffmpeg(cfg: Config) -> str:
    """Localiza el binario de ffmpeg."""
    if cfg.ffmpeg_bin:
        return cfg.ffmpeg_bin
    en_path = shutil.which("ffmpeg")
    if en_path:
        return en_path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        raise MontajeError(
            "No se encontro ffmpeg. Instalalo, define AGENTE_YT_FFMPEG con su "
            "ruta, o instala el paquete opcional: pip install imageio-ffmpeg"
        ) from exc


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Ultimas lineas del log de ffmpeg para diagnosticar.
        cola = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise MontajeError(f"ffmpeg fallo (codigo {proc.returncode}):\n{cola}")


# --------------------------------------------------------------- utilidades
def _es_url(ruta: str) -> bool:
    return ruta.startswith("http://") or ruta.startswith("https://")


def _es_video(ruta: str) -> bool:
    return Path(ruta).suffix.lower() in _EXT_VIDEO


def _descargar(url: str, destino: Path) -> Path:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover
        raise MontajeError("Descargar URLs requiere: pip install httpx") from exc
    with httpx.Client(timeout=120.0, follow_redirects=True) as http:
        r = http.get(url)
        r.raise_for_status()
        destino.write_bytes(r.content)
    return destino


def _dims(cfg: Config) -> tuple[int, int]:
    try:
        w, h = cfg.video_size.lower().split("x")
        return int(w), int(h)
    except Exception as exc:  # noqa: BLE001
        raise MontajeError(f"AGENTE_YT_VIDEO_SIZE invalido: {cfg.video_size}") from exc


def _filtro_encajar(w: int, h: int) -> str:
    """Escala manteniendo aspecto y rellena con negro hasta WxH (let/pillarbox)."""
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
    )


def _segmento_desde_imagen(
    ff: str, img: Path, salida: Path, cfg: Config, dur: float, con_zoom: bool
) -> None:
    w, h = _dims(cfg)
    fps = cfg.video_fps
    frames = max(1, round(dur * fps))
    if con_zoom:
        # Ken Burns: sobre-escalar para reducir "jitter" y zoom lento.
        vf = (
            f"scale={w * 4}:{h * 4}:force_original_aspect_ratio=decrease,"
            f"pad={w * 4}:{h * 4}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"zoompan=z='min(zoom+0.0012,1.2)':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
            f"setsar=1,format=yuv420p"
        )
    else:
        vf = f"{_filtro_encajar(w, h)},format=yuv420p"
    _run([
        ff, "-y", "-loop", "1", "-i", str(img),
        "-t", f"{dur:.3f}", "-vf", vf, "-r", str(fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(salida),
    ])


def _segmento_desde_video(ff: str, vid: Path, salida: Path, cfg: Config) -> None:
    w, h = _dims(cfg)
    vf = f"{_filtro_encajar(w, h)},format=yuv420p"
    _run([
        ff, "-y", "-i", str(vid),
        "-vf", vf, "-r", str(cfg.video_fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(salida),
    ])


# --------------------------------------------------------------- API montaje
def montar(
    clips: list[Clip],
    salida: Path,
    cfg: Config,
    audio: Path | str | None = None,
) -> Path:
    """Ensambla los clips (y el audio opcional) en un MP4 final."""
    if not clips:
        raise MontajeError("No hay clips para montar.")
    ff = resolver_ffmpeg(cfg)
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        segmentos: list[Path] = []

        for i, clip in enumerate(clips):
            origen = clip.ruta
            # Descargar si es URL.
            if _es_url(origen):
                ext = ".mp4" if _es_video(origen) else ".png"
                local = _descargar(origen, tmpdir / f"src_{i}{ext}")
            else:
                local = Path(origen)
                if not local.exists():
                    raise MontajeError(f"No existe el medio: {local}")

            seg = tmpdir / f"seg_{i:03d}.mp4"
            if _es_video(str(local)):
                _segmento_desde_video(ff, local, seg, cfg)
            else:
                _segmento_desde_imagen(
                    ff, local, seg, cfg, clip.duracion, clip.con_zoom
                )
            segmentos.append(seg)

        # Concatenar (demuxer). Todos los segmentos comparten codec/params.
        lista = tmpdir / "lista.txt"
        lista.write_text(
            "".join(f"file '{s.as_posix()}'\n" for s in segmentos), encoding="utf-8"
        )
        video_mudo = tmpdir / "video_mudo.mp4"
        _run([
            ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(cfg.video_fps),
            str(video_mudo),
        ])

        # Mezclar audio si se aporta; si no, exportar el video sin sonido.
        if audio:
            audio_path = Path(audio)
            if not audio_path.exists():
                raise MontajeError(f"No existe el audio: {audio_path}")
            _run([
                ff, "-y", "-i", str(video_mudo), "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(salida),
            ])
        else:
            shutil.copyfile(video_mudo, salida)

    return salida


def montar_directorio(
    directorio: Path | str,
    salida: Path,
    cfg: Config,
    audio: Path | str | None = None,
    duracion_imagen: float | None = None,
    con_zoom: bool = True,
) -> Path:
    """Monta todos los medios de una carpeta, ordenados por nombre de archivo."""
    directorio = Path(directorio)
    if not directorio.is_dir():
        raise MontajeError(f"No es una carpeta: {directorio}")
    dur = duracion_imagen if duracion_imagen is not None else cfg.img_duration
    medios = sorted(
        p for p in directorio.iterdir()
        if p.is_file() and p.suffix.lower() in (_EXT_VIDEO | {
            ".png", ".jpg", ".jpeg", ".webp", ".bmp"
        })
    )
    if not medios:
        raise MontajeError(f"La carpeta no contiene imagenes/videos: {directorio}")
    clips = [Clip(ruta=str(p), duracion=dur, con_zoom=con_zoom) for p in medios]
    return montar(clips, salida, cfg, audio=audio)


def montar_desde_resultados(
    resultados,  # list[ResultadoEscena]
    salida: Path,
    cfg: Config,
    audio: Path | str | None = None,
    duracion_imagen: float | None = None,
) -> Path:
    """Monta a partir de los ResultadoEscena del Nodo 5 (usa video o imagen)."""
    dur = duracion_imagen if duracion_imagen is not None else cfg.img_duration
    clips: list[Clip] = []
    for r in resultados:
        medio = r.video_url or r.image_url
        if not medio:
            continue
        clips.append(Clip(ruta=medio, duracion=dur, con_zoom=not bool(r.video_url)))
    if not clips:
        raise MontajeError(
            "Ningun ResultadoEscena tiene image_url/video_url para montar."
        )
    return montar(clips, salida, cfg, audio=audio)
