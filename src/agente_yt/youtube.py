"""Nodo 11: Subida a YouTube (Data API v3).

Sube el video final a YouTube y, opcionalmente, fija la miniatura.

IMPORTANTE sobre autenticacion: la subida de videos NO admite una simple API key;
requiere OAuth2 de usuario con el scope `youtube.upload`. Flujo:

  1. Crea un proyecto en Google Cloud, habilita "YouTube Data API v3" y crea
     credenciales OAuth de tipo "App de escritorio". Descarga el client_secrets.json.
  2. Apunta AGENTE_YT_YT_CLIENT_SECRETS a ese archivo.
  3. La PRIMERA vez se abre el navegador para dar consentimiento; el token
     resultante se guarda en AGENTE_YT_YT_TOKEN y se reutiliza/renueva despues.

Paquetes necesarios:
    pip install google-api-python-client google-auth google-auth-oauthlib

No se puede probar la subida real en un entorno headless (requiere el
consentimiento OAuth y un video real). El codigo esta listo para ejecutarse en
tu maquina.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_PRIVACIDADES = {"private", "unlisted", "public"}


class YouTubeError(RuntimeError):
    """Error al interactuar con la API de YouTube."""


def _importar():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise YouTubeError(
            "La subida a YouTube requiere: pip install google-api-python-client "
            "google-auth google-auth-oauthlib"
        ) from exc
    return Request, Credentials, InstalledAppFlow, build, MediaFileUpload


def _obtener_credenciales(cfg: Config):
    Request, Credentials, InstalledAppFlow, _, _ = _importar()
    token_path = Path(cfg.yt_token) if cfg.yt_token else Path("youtube_token.json")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    # Necesita consentimiento interactivo (primera vez, en tu maquina).
    if not cfg.yt_client_secrets or not Path(cfg.yt_client_secrets).exists():
        raise YouTubeError(
            "Falta el client_secrets de OAuth. Define AGENTE_YT_YT_CLIENT_SECRETS "
            "con la ruta al JSON descargado de Google Cloud (App de escritorio)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(cfg.yt_client_secrets, _SCOPES)
    creds = flow.run_local_server(port=0)  # abre el navegador
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def subir_a_youtube(
    video: Path | str,
    titulo: str,
    descripcion: str,
    cfg: Config,
    *,
    tags: list[str] | None = None,
    miniatura: Path | str | None = None,
    privacidad: str | None = None,
) -> str:
    """Sube el video y devuelve la URL de YouTube. Fija la miniatura si se da."""
    video = Path(video)
    if not video.exists():
        raise YouTubeError(f"No existe el video a subir: {video}")

    privacidad = (privacidad or cfg.yt_privacy or "unlisted").lower()
    if privacidad not in _PRIVACIDADES:
        raise YouTubeError(
            f"Privacidad invalida: {privacidad}. Usa: private|unlisted|public"
        )

    _, _, _, build, MediaFileUpload = _importar()
    creds = _obtener_credenciales(cfg)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": titulo[:100],  # YouTube limita el titulo a 100 chars
            "description": descripcion or "",
            "tags": tags or [],
            "categoryId": cfg.yt_category or "22",
        },
        "status": {
            "privacyStatus": privacidad,
            "selfDeclaredMadeForKids": True,  # contenido infantil (COPPA)
        },
    }
    media = MediaFileUpload(str(video), chunksize=-1, resumable=True)
    peticion = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    respuesta = None
    while respuesta is None:
        _, respuesta = peticion.next_chunk()
    video_id = respuesta.get("id", "")
    if not video_id:
        raise YouTubeError(f"Respuesta inesperada de YouTube: {respuesta}")

    # Miniatura (opcional).
    if miniatura and Path(miniatura).exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id, media_body=MediaFileUpload(str(miniatura))
            ).execute()
        except Exception as exc:  # noqa: BLE001 - la subida ya fue exitosa
            # No abortamos por un fallo de miniatura (p.ej. canal sin verificar).
            raise YouTubeError(
                f"Video subido (id={video_id}) pero fallo la miniatura: {exc}"
            ) from exc

    return f"https://www.youtube.com/watch?v={video_id}"
