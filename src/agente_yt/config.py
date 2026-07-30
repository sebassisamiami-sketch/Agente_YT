"""Carga de configuracion desde variables de entorno (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv es opcional; si no esta, se usan las env vars tal cual
    pass


# Raiz del repositorio (…/Agente_YT), calculada desde este archivo.
ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    # --- LLM (nodos 2 y 3) ---
    provider: str
    model: str
    anthropic_api_key: str
    openai_api_key: str

    # --- Higgsfield (nodo 5) ---
    higgsfield_base_url: str
    higgsfield_api_key: str
    higgsfield_secret: str
    higgsfield_quality: str
    higgsfield_image_size: str
    higgsfield_motion_id: str
    higgsfield_video_model: str

    # --- Montaje (nodo 7) ---
    ffmpeg_bin: str
    video_size: str
    video_fps: int
    img_duration: float

    # --- Voz / TTS (nodo 8) ---
    tts_provider: str
    tts_voice: str
    tts_model: str

    # --- Musica de fondo / subtitulos (nodos 7 y 9) ---
    musica: str
    volumen_musica: float

    # --- Salida ---
    output_dir: Path
    formula_path: Path

    @property
    def higgsfield_configurado(self) -> bool:
        """True si hay credenciales para llamar a la API de Higgsfield."""
        return bool(self.higgsfield_api_key and self.higgsfield_secret)

    @classmethod
    def from_env(cls) -> "Config":
        output = os.getenv("AGENTE_YT_OUTPUT_DIR", "salidas")
        output_dir = (ROOT_DIR / output) if not os.path.isabs(output) else Path(output)
        return cls(
            provider=os.getenv("AGENTE_YT_LLM_PROVIDER", "mock").strip().lower(),
            model=os.getenv("AGENTE_YT_LLM_MODEL", "claude-3-5-sonnet-latest").strip(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            higgsfield_base_url=os.getenv(
                "HIGGSFIELD_BASE_URL", "https://platform.higgsfield.ai"
            ).rstrip("/"),
            higgsfield_api_key=os.getenv("HIGGSFIELD_API_KEY", ""),
            higgsfield_secret=os.getenv("HIGGSFIELD_SECRET", ""),
            higgsfield_quality=os.getenv("HIGGSFIELD_QUALITY", "1080p").strip(),
            higgsfield_image_size=os.getenv(
                "HIGGSFIELD_IMAGE_SIZE", "2048x1152"
            ).strip(),
            higgsfield_motion_id=os.getenv("HIGGSFIELD_MOTION_ID", "").strip(),
            higgsfield_video_model=os.getenv(
                "HIGGSFIELD_VIDEO_MODEL", "dop-turbo"
            ).strip(),
            ffmpeg_bin=os.getenv("AGENTE_YT_FFMPEG", "").strip(),
            video_size=os.getenv("AGENTE_YT_VIDEO_SIZE", "1920x1080").strip(),
            video_fps=int(os.getenv("AGENTE_YT_VIDEO_FPS", "30")),
            img_duration=float(os.getenv("AGENTE_YT_IMG_DURATION", "5")),
            tts_provider=os.getenv("AGENTE_YT_TTS_PROVIDER", "mock").strip().lower(),
            tts_voice=os.getenv("AGENTE_YT_TTS_VOICE", "").strip(),
            tts_model=os.getenv("AGENTE_YT_TTS_MODEL", "tts-1").strip(),
            musica=os.getenv("AGENTE_YT_MUSICA", "").strip(),
            volumen_musica=float(os.getenv("AGENTE_YT_VOLUMEN_MUSICA", "0.18")),
            output_dir=output_dir,
            formula_path=ROOT_DIR / "config" / "formula_cocomelon.md",
        )
