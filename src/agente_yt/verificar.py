"""Comando de diagnostico (\"doctor\") de Agente_YT.

Comprueba, sin gastar creditos ni publicar nada, que cada credencial y
herramienta este bien configurada:

  - ffmpeg (para montaje/miniatura/intro-outro)
  - LLM (nodos 2, 3 y 12): hace una llamada minima
  - Higgsfield (nodo 5): un GET de solo lectura (lista estilos) para validar auth
  - Voz/TTS (nodo 8)
  - YouTube (nodo 11): paquetes, client_secrets y token, sin abrir el navegador

Cada chequeo devuelve un estado: OK / AVISO / FALLO / OMITIDO.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config

OK = "OK"
AVISO = "AVISO"
FALLO = "FALLO"
OMITIDO = "OMITIDO"


@dataclass
class Chequeo:
    nombre: str
    estado: str
    detalle: str = ""


def _check_ffmpeg(cfg: Config) -> Chequeo:
    try:
        from .montaje import resolver_ffmpeg

        ruta = resolver_ffmpeg(cfg)
        return Chequeo("ffmpeg", OK, ruta)
    except Exception as exc:  # noqa: BLE001
        return Chequeo("ffmpeg", FALLO, str(exc))


def _check_llm(cfg: Config) -> Chequeo:
    if cfg.provider == "mock":
        return Chequeo("LLM", OMITIDO, "proveedor 'mock' (no requiere clave)")
    try:
        from .llm import _resolver_modelo, build_client

        client = build_client(cfg)
        if cfg.provider == "multi":
            activos = ", ".join(getattr(client, "nombres", []))
            txt = client.complete("Responde solo con: OK", "Di OK")
            muestra = (txt or "").strip().replace("\n", " ")[:40]
            return Chequeo("LLM", OK, f"multi [{activos}] -> '{muestra}'")
        txt = client.complete("Responde solo con: OK", "Di OK")
        modelo = _resolver_modelo(cfg)
        muestra = (txt or "").strip().replace("\n", " ")[:40]
        return Chequeo("LLM", OK, f"{cfg.provider}/{modelo} -> '{muestra}'")
    except Exception as exc:  # noqa: BLE001
        return Chequeo("LLM", FALLO, f"{cfg.provider}: {str(exc)[:120]}")


def _check_higgsfield(cfg: Config) -> Chequeo:
    if not cfg.higgsfield_configurado:
        return Chequeo(
            "Higgsfield", OMITIDO, "sin HIGGSFIELD_API_KEY/SECRET (no gasta creditos)"
        )
    try:
        from .higgsfield import HiggsfieldClient

        client = HiggsfieldClient(cfg)
        datos = client.listar_styles()  # GET de solo lectura, no consume creditos
        n = len(datos) if isinstance(datos, list) else "?"
        return Chequeo("Higgsfield", OK, f"auth valida (estilos disponibles: {n})")
    except Exception as exc:  # noqa: BLE001
        return Chequeo("Higgsfield", FALLO, str(exc)[:140])


def _check_tts(cfg: Config) -> Chequeo:
    p = cfg.tts_provider
    if p == "mock":
        return Chequeo("Voz/TTS", OMITIDO, "proveedor 'mock' (placeholder offline)")
    detalle = {
        "edge": "edge-tts (gratis, sin clave; requiere internet)",
        "gtts": "gTTS (gratis, sin clave; requiere internet)",
        "openai": "OpenAI TTS (requiere OPENAI_API_KEY)",
    }.get(p, p)
    # Verifica que el paquete este disponible.
    try:
        if p == "edge":
            import edge_tts  # noqa: F401
        elif p == "gtts":
            import gtts  # noqa: F401
        elif p == "openai":
            import openai  # noqa: F401
            if not cfg.openai_api_key:
                return Chequeo("Voz/TTS", AVISO, "openai sin OPENAI_API_KEY")
        return Chequeo("Voz/TTS", OK, detalle)
    except ImportError:
        return Chequeo("Voz/TTS", AVISO, f"{p}: falta el paquete (pip install)")


def _check_youtube(cfg: Config) -> Chequeo:
    # 1) Paquetes
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        return Chequeo(
            "YouTube", OMITIDO,
            "faltan paquetes (pip install google-api-python-client google-auth "
            "google-auth-oauthlib) - solo si vas a subir",
        )
    # 2) Token existente valido/renovable
    token_path = Path(cfg.yt_token) if cfg.yt_token else Path("youtube_token.json")
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path),
                ["https://www.googleapis.com/auth/youtube.upload"],
            )
            if creds and creds.valid:
                return Chequeo("YouTube", OK, "token valido")
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
                return Chequeo("YouTube", OK, "token renovado")
        except Exception as exc:  # noqa: BLE001
            return Chequeo("YouTube", AVISO, f"token invalido: {str(exc)[:80]}")
    # 3) Sin token: hace falta el consentimiento
    if cfg.yt_client_secrets and Path(cfg.yt_client_secrets).exists():
        return Chequeo(
            "YouTube", AVISO,
            "client_secrets OK, falta autorizar: ejecuta una subida (--subir) una vez",
        )
    return Chequeo(
        "YouTube", OMITIDO,
        "sin client_secrets (define AGENTE_YT_YT_CLIENT_SECRETS) - solo si vas a subir",
    )


def verificar(cfg: Config | None = None) -> list[Chequeo]:
    cfg = cfg or Config.from_env()
    return [
        _check_ffmpeg(cfg),
        _check_llm(cfg),
        _check_higgsfield(cfg),
        _check_tts(cfg),
        _check_youtube(cfg),
    ]
