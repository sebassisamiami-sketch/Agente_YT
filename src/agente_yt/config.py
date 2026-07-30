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
            output_dir=output_dir,
            formula_path=ROOT_DIR / "config" / "formula_cocomelon.md",
        )
