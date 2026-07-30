"""Nodo 5: Herramienta de Generacion (Higgsfield).

Cliente de la API REST oficial de Higgsfield (https://platform.higgsfield.ai).

Flujo (Higgsfield es "image-first"):
  1. Texto -> Imagen con el modelo Soul  (POST /v1/text2image/soul)
  2. (Opcional) Imagen -> Video con DoP   (POST /v1/image2video/dop) usando un
     `motion_id`. Se activa solo si hay HIGGSFIELD_MOTION_ID configurado.
  3. Sondeo del job hasta que termina    (GET /v1/job-sets/{id})

Autenticacion por cabeceras: hf-api-key + hf-secret (claves KEY:SECRET desde
https://cloud.higgsfield.ai/api-keys).

IMPORTANTE: generar consume CREDITOS DE PAGO. Si no hay credenciales, este nodo
devuelve la escena en estado 'pendiente' para no bloquear el pipeline (fase 1).

Nota de honestidad: las rutas y el payload provienen de clientes MCP publicos de
la comunidad; la FORMA EXACTA de la respuesta de /v1/job-sets/{id} no esta
documentada oficialmente, por eso el parseo (`_buscar_url`, `_buscar_estado`) es
defensivo y busca las claves habituales de forma recursiva. Puede necesitar un
pequeno ajuste al probarlo contra trafico real.
"""

from __future__ import annotations

import time
from typing import Any

from .config import Config
from .schemas import PromptVisual, ResultadoEscena

# Estados terminales que devuelve la API en los job-sets.
_ESTADOS_OK = {"completed", "complete", "succeeded", "success", "done"}
_ESTADOS_FALLO = {"failed", "error", "nsfw", "canceled", "cancelled"}

# Claves donde suele venir una URL de resultado.
_CLAVES_URL = (
    "url",
    "min_url",
    "raw_url",
    "video_url",
    "image_url",
    "output_url",
    "result_url",
)


class HiggsfieldError(RuntimeError):
    """Error al hablar con la API de Higgsfield."""


class HiggsfieldClient:
    """Cliente sincrono minimo de la API de Higgsfield."""

    def __init__(self, cfg: Config) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise HiggsfieldError(
                "El nodo Higgsfield requiere el paquete: pip install httpx"
            ) from exc
        if not cfg.higgsfield_configurado:
            raise HiggsfieldError(
                "Faltan credenciales HIGGSFIELD_API_KEY / HIGGSFIELD_SECRET."
            )
        self._httpx = httpx
        self._base = cfg.higgsfield_base_url
        self._headers = {
            "hf-api-key": cfg.higgsfield_api_key,
            "hf-secret": cfg.higgsfield_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._cfg = cfg

    # ------------------------------------------------------------------ HTTP
    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        with self._httpx.Client(timeout=60.0) as http:
            r = http.post(f"{self._base}{path}", headers=self._headers, json=body)
            r.raise_for_status()
            return r.json()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        with self._httpx.Client(timeout=60.0) as http:
            r = http.get(f"{self._base}{path}", headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    # --------------------------------------------------------------- Metodos
    def generar_imagen(self, prompt_en: str) -> dict[str, Any]:
        """POST /v1/text2image/soul -> respuesta con el id del job set."""
        params: dict[str, Any] = {
            "prompt": prompt_en,
            "width_and_height": self._cfg.higgsfield_image_size,
            "enhance_prompt": False,
            "quality": self._cfg.higgsfield_quality,
            "batch_size": 1,
        }
        return self._post("/v1/text2image/soul", {"params": params})

    def animar_video(self, image_url: str, prompt_en: str) -> dict[str, Any]:
        """POST /v1/image2video/dop -> anima una imagen a video con un motion."""
        params = {
            "model": self._cfg.higgsfield_video_model,
            "prompt": prompt_en or "Cinematic video with natural motion",
            "input_images": [{"type": "image_url", "image_url": image_url}],
            "motions": [{"id": self._cfg.higgsfield_motion_id, "strength": 0.5}],
        }
        return self._post("/v1/image2video/dop", {"params": params})

    def estado_job(self, job_set_id: str) -> dict[str, Any]:
        """GET /v1/job-sets/{id}."""
        return self._get(f"/v1/job-sets/{job_set_id}")

    def listar_motions(self) -> Any:
        return self._get("/v1/motions")

    def listar_styles(self) -> Any:
        return self._get("/v1/text2image/soul-styles")

    # --------------------------------------------------------------- Sondeo
    def esperar_resultado(
        self, job_set_id: str, *, intervalo: float = 5.0, timeout: float = 300.0
    ) -> tuple[str, str]:
        """Sondea el job hasta un estado terminal. Devuelve (estado, url)."""
        limite = time.monotonic() + timeout
        while True:
            data = self.estado_job(job_set_id)
            estado = _buscar_estado(data)
            if estado in _ESTADOS_OK:
                return "listo", _buscar_url(data)
            if estado in _ESTADOS_FALLO:
                return (estado if estado == "nsfw" else "error"), ""
            if time.monotonic() >= limite:
                return "error", ""  # timeout
            time.sleep(intervalo)


# --------------------------------------------------------- Parseo defensivo
def _buscar_estado(data: Any) -> str:
    """Busca recursivamente un campo 'status' en la respuesta del job set.

    Si hay varios jobs, se considera terminal solo cuando TODOS lo son; si alguno
    fallo, prevalece el fallo.
    """
    estados: list[str] = []

    def _rec(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "status" and isinstance(v, str):
                    estados.append(v.lower())
                else:
                    _rec(v)
        elif isinstance(obj, list):
            for it in obj:
                _rec(it)

    _rec(data)
    if not estados:
        return "in_progress"
    if any(e in _ESTADOS_FALLO for e in estados):
        # Devuelve el fallo concreto (p.ej. nsfw) si lo hay.
        for e in estados:
            if e in _ESTADOS_FALLO:
                return e
    if all(e in _ESTADOS_OK for e in estados):
        return "completed"
    return "in_progress"


def _buscar_url(data: Any) -> str:
    """Busca recursivamente la primera URL http(s) en claves de resultado."""
    encontrada = ""

    def _rec(obj: Any) -> bool:
        nonlocal encontrada
        if isinstance(obj, dict):
            for k, v in obj.items():
                if (
                    k.lower() in _CLAVES_URL
                    and isinstance(v, str)
                    and v.startswith("http")
                ):
                    encontrada = v
                    return True
                if _rec(v):
                    return True
        elif isinstance(obj, list):
            for it in obj:
                if _rec(it):
                    return True
        return False

    _rec(data)
    return encontrada


def _extraer_job_set_id(data: Any) -> str:
    """Extrae el id del job set de la respuesta de creacion."""
    if isinstance(data, dict):
        for clave in ("id", "job_set_id", "jobSetId"):
            val = data.get(clave)
            if isinstance(val, str) and val:
                return val
        # A veces viene anidado bajo "job_set".
        for v in data.values():
            encontrado = _extraer_job_set_id(v)
            if encontrado:
                return encontrado
    return ""


# --------------------------------------------------------------- Orquestacion
def generar_video(prompt: PromptVisual, cfg: Config) -> ResultadoEscena:
    """Nodo 5: genera imagen (y opcionalmente video) para una escena.

    - Sin credenciales -> estado 'pendiente' (no gasta, permite validar fase 1).
    - Con credenciales  -> texto->imagen; si hay motion_id, imagen->video.
    """
    base = ResultadoEscena(
        escena=prompt.escena,
        texto_escena=prompt.texto_escena,
        prompt_en=prompt.prompt_en,
    )

    if not cfg.higgsfield_configurado:
        base.estado = "pendiente"  # Higgsfield no configurado (fase 1)
        return base

    try:
        client = HiggsfieldClient(cfg)

        # Etapa 1: texto -> imagen (Soul)
        resp_img = client.generar_imagen(prompt.prompt_en)
        job_img = _extraer_job_set_id(resp_img)
        base.job_set_id = job_img
        estado, image_url = client.esperar_resultado(job_img)
        base.estado = estado
        base.image_url = image_url

        if estado != "listo":
            base.error = f"Fallo en generacion de imagen (estado={estado})"
            return base

        # Etapa 2 (opcional): imagen -> video (DoP) si hay motion configurado
        if cfg.higgsfield_motion_id:
            resp_vid = client.animar_video(image_url, prompt.prompt_en)
            job_vid = _extraer_job_set_id(resp_vid)
            base.job_set_id = job_vid
            estado_v, video_url = client.esperar_resultado(job_vid)
            base.estado = estado_v
            base.video_url = video_url
            if estado_v != "listo":
                base.error = f"Fallo en animacion de video (estado={estado_v})"
        else:
            # Sin motion: el "entregable" es la imagen; se marca como listo.
            base.video_url = ""
        return base

    except Exception as exc:  # noqa: BLE001 - registrar y seguir con la escena
        base.estado = "error"
        base.error = str(exc)
        return base
