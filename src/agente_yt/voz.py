"""Nodo 8: Voz / Narracion (TTS).

Convierte el texto del guion en una pista de audio hablada que luego alimenta el
montaje (Nodo 7) como banda de voz.

Proveedores:
  - "mock":   offline, sin red ni clave. Genera un audio de placeholder (silencio)
              de duracion proporcional al texto, para validar el pipeline.
  - "edge":   Microsoft Edge TTS. GRATIS y sin clave (requiere internet y el
              paquete `edge-tts`). Buena calidad y muchas voces/idiomas.
  - "gtts":   Google Translate TTS. GRATIS y sin clave (requiere internet y
              `gTTS`). Mas robotico.
  - "openai": OpenAI TTS (requiere OPENAI_API_KEY y el paquete `openai`).

Todos exponen `sintetizar(texto, salida)` y devuelven la ruta del audio.
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from .config import Config

# Voces por defecto para edge-tts segun idioma.
_EDGE_VOCES = {
    "es": "es-ES-AlvaroNeural",
    "en": "en-US-AriaNeural",
    "pt": "pt-BR-AntonioNeural",
    "fr": "fr-FR-DeniseNeural",
}


class VozError(RuntimeError):
    """Error al generar la voz (TTS)."""


class TTSClient(ABC):
    @abstractmethod
    def sintetizar(self, texto: str, salida: Path) -> Path:
        raise NotImplementedError


class MockTTS(TTSClient):
    """Genera un audio de placeholder (silencio) con ffmpeg. Offline y sin clave."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg

    def sintetizar(self, texto: str, salida: Path) -> Path:
        from .montaje import resolver_ffmpeg  # reutiliza la deteccion de ffmpeg

        ff = resolver_ffmpeg(self._cfg)
        # Estima la duracion: ~2.5 palabras/segundo, minimo 2 s.
        palabras = max(1, len(texto.split()))
        dur = max(2.0, palabras / 2.5)
        salida = salida.with_suffix(".wav")
        salida.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                ff, "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=mono",
                "-t", f"{dur:.2f}", "-c:a", "pcm_s16le", str(salida),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            cola = "\n".join(proc.stderr.strip().splitlines()[-6:])
            raise VozError(f"ffmpeg fallo generando voz mock:\n{cola}")
        return salida


class EdgeTTS(TTSClient):
    """Microsoft Edge TTS (gratis, sin clave)."""

    def __init__(self, cfg: Config, idioma: str) -> None:
        self._voz = cfg.tts_voice or _EDGE_VOCES.get(idioma, _EDGE_VOCES["en"])

    def sintetizar(self, texto: str, salida: Path) -> Path:
        try:
            import asyncio

            import edge_tts
        except ImportError as exc:  # pragma: no cover
            raise VozError(
                "El proveedor 'edge' requiere: pip install edge-tts"
            ) from exc
        salida = salida.with_suffix(".mp3")
        salida.parent.mkdir(parents=True, exist_ok=True)

        async def _run() -> None:
            comm = edge_tts.Communicate(texto, self._voz)
            await comm.save(str(salida))

        try:
            asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001 - red, voz invalida, etc.
            raise VozError(f"Edge TTS fallo: {exc}") from exc
        return salida


class GTTS(TTSClient):
    """Google Translate TTS (gratis, sin clave)."""

    def __init__(self, idioma: str) -> None:
        self._idioma = idioma

    def sintetizar(self, texto: str, salida: Path) -> Path:
        try:
            from gtts import gTTS
        except ImportError as exc:  # pragma: no cover
            raise VozError("El proveedor 'gtts' requiere: pip install gTTS") from exc
        salida = salida.with_suffix(".mp3")
        salida.parent.mkdir(parents=True, exist_ok=True)
        try:
            gTTS(text=texto, lang=self._idioma).save(str(salida))
        except Exception as exc:  # noqa: BLE001
            raise VozError(f"gTTS fallo: {exc}") from exc
        return salida


class OpenAITTS(TTSClient):
    """OpenAI TTS (requiere clave)."""

    def __init__(self, cfg: Config) -> None:
        if not cfg.openai_api_key:
            raise VozError("Falta OPENAI_API_KEY para el proveedor de voz 'openai'.")
        self._key = cfg.openai_api_key
        self._model = cfg.tts_model or "tts-1"
        self._voz = cfg.tts_voice or "nova"

    def sintetizar(self, texto: str, salida: Path) -> Path:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise VozError("El proveedor 'openai' requiere: pip install openai") from exc
        salida = salida.with_suffix(".mp3")
        salida.parent.mkdir(parents=True, exist_ok=True)
        try:
            client = OpenAI(api_key=self._key)
            with client.audio.speech.with_streaming_response.create(
                model=self._model, voice=self._voz, input=texto
            ) as resp:
                resp.stream_to_file(str(salida))
        except Exception as exc:  # noqa: BLE001
            raise VozError(f"OpenAI TTS fallo: {exc}") from exc
        return salida


def build_tts(cfg: Config, idioma: str = "es") -> TTSClient:
    """Fabrica el cliente TTS segun la configuracion."""
    p = cfg.tts_provider
    if p == "mock":
        return MockTTS(cfg)
    if p == "edge":
        return EdgeTTS(cfg, idioma)
    if p == "gtts":
        return GTTS(idioma)
    if p == "openai":
        return OpenAITTS(cfg)
    raise VozError(f"Proveedor TTS desconocido: '{p}'. Usa: mock|edge|gtts|openai")


def generar_voz(
    texto: str, salida: Path, cfg: Config, idioma: str = "es"
) -> Path:
    """Sintetiza `texto` a audio con el proveedor configurado."""
    texto = (texto or "").strip()
    if not texto:
        raise VozError("No hay texto para narrar.")
    return build_tts(cfg, idioma).sintetizar(texto, Path(salida))


def texto_narracion_desde_guion(guion_visual) -> str:
    """Extrae solo la LETRA/DIALOGO (texto_escena) de cada escena, en orden.

    Se narra la letra de la cancion, NO las indicaciones visuales.
    """
    lineas = [
        e.texto_escena.strip()
        for e in guion_visual.escenas
        if getattr(e, "texto_escena", "").strip()
    ]
    return "\n".join(lineas)


def generar_voz_desde_guion(
    guion_visual, salida: Path, cfg: Config, idioma: str = "es"
) -> Path:
    """Narra la letra del guion (Nodo 3) y guarda la pista de voz."""
    texto = texto_narracion_desde_guion(guion_visual)
    if not texto:
        raise VozError(
            "El guion no tiene lineas de letra (texto_escena) para narrar."
        )
    return generar_voz(texto, Path(salida), cfg, idioma)
