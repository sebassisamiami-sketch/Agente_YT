"""Carga de configuracion desde variables de entorno (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Raiz del repositorio (…/Agente_YT), calculada desde este archivo.
ROOT_DIR = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv

    # Carga robusta del .env: primero el de la raiz del repo (independiente del
    # directorio actual) y ademas el del directorio de trabajo, por si acaso.
    # Asi funciona tanto si ejecutas desde la raiz como desde otra carpeta.
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv()
except ImportError:  # dotenv es opcional; si no esta, se usan las env vars tal cual
    pass


@dataclass(frozen=True)
class Config:
    # --- LLM (nodos 2 y 3) ---
    provider: str
    model: str
    anthropic_api_key: str
    openai_api_key: str
    nvidia_api_key: str
    nvidia_base_url: str

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

    # --- YouTube (nodo 11) ---
    yt_client_secrets: str
    yt_token: str
    yt_privacy: str
    yt_category: str

    # --- Intro / outro (nodo 13) ---
    outro_texto: str
    intro_dur: float
    outro_dur: float

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
            # Vacio = "auto": cada proveedor elige su modelo por defecto.
            model=os.getenv("AGENTE_YT_LLM_MODEL", "").strip(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
            nvidia_base_url=os.getenv(
                "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
            ).rstrip("/"),
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
            yt_client_secrets=os.getenv("AGENTE_YT_YT_CLIENT_SECRETS", "").strip(),
            yt_token=os.getenv("AGENTE_YT_YT_TOKEN", "youtube_token.json").strip(),
            yt_privacy=os.getenv("AGENTE_YT_YT_PRIVACY", "unlisted").strip().lower(),
            yt_category=os.getenv("AGENTE_YT_YT_CATEGORY", "22").strip(),
            outro_texto=os.getenv(
                "AGENTE_YT_OUTRO_TEXTO", "Gracias por ver. Suscribete!"
            ).strip(),
            intro_dur=float(os.getenv("AGENTE_YT_INTRO_DUR", "3")),
            outro_dur=float(os.getenv("AGENTE_YT_OUTRO_DUR", "3")),
            output_dir=output_dir,
            formula_path=ROOT_DIR / "config" / "formula_cocomelon.md",
        )
