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
    provider: str
    model: str
    anthropic_api_key: str
    openai_api_key: str
    higgsfield_api_url: str
    higgsfield_api_key: str
    output_dir: Path
    formula_path: Path

    @classmethod
    def from_env(cls) -> "Config":
        output = os.getenv("AGENTE_YT_OUTPUT_DIR", "salidas")
        output_dir = (ROOT_DIR / output) if not os.path.isabs(output) else Path(output)
        return cls(
            provider=os.getenv("AGENTE_YT_LLM_PROVIDER", "mock").strip().lower(),
            model=os.getenv("AGENTE_YT_LLM_MODEL", "claude-3-5-sonnet-latest").strip(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            higgsfield_api_url=os.getenv("HIGGSFIELD_API_URL", ""),
            higgsfield_api_key=os.getenv("HIGGSFIELD_API_KEY", ""),
            output_dir=output_dir,
            formula_path=ROOT_DIR / "config" / "formula_cocomelon.md",
        )
