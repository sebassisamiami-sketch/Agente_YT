"""Nodo 5: Herramienta de Generacion (Higgsfield) -- STUB.

FASE POSTERIOR. Segun el consejo de construir por fases, este nodo NO se conecta
hasta que el JSON del Nodo 3 quede perfecto. Aqui queda el contrato y un esqueleto
de integracion (HTTP/REST o MCP) listo para rellenar cuando tengas el endpoint y
la clave reales de Higgsfield.
"""

from __future__ import annotations

from .config import Config
from .schemas import PromptVisual, ResultadoEscena


def generar_video(prompt: PromptVisual, cfg: Config) -> ResultadoEscena:
    """Nodo 5 (stub): enviaria `prompt.prompt_en` a Higgsfield y esperaria la URL.

    Implementacion futura (pseudo-flujo):
        1. POST {HIGGSFIELD_API_URL}/generate con {"prompt": prompt.prompt_en}
           y cabecera Authorization: Bearer {HIGGSFIELD_API_KEY}.
        2. Sondear el estado del job hasta que este "listo".
        3. Devolver la URL del clip generado.

    Mientras no haya credenciales configuradas, devuelve un ResultadoEscena en
    estado 'pendiente' para que el pipeline 1->3 se pueda validar de punta a punta
    sin gastar creditos.
    """
    if not cfg.higgsfield_api_url or not cfg.higgsfield_api_key:
        return ResultadoEscena(
            escena=prompt.escena,
            texto_escena=prompt.texto_escena,
            prompt_en=prompt.prompt_en,
            video_url="",
            estado="pendiente",  # Higgsfield aun no configurado (fase posterior)
        )

    # --- Esqueleto de la llamada real (descomentar y completar en la fase 2) ---
    # import httpx
    # with httpx.Client(timeout=120) as http:
    #     r = http.post(
    #         f"{cfg.higgsfield_api_url.rstrip('/')}/generate",
    #         headers={"Authorization": f"Bearer {cfg.higgsfield_api_key}"},
    #         json={"prompt": prompt.prompt_en},
    #     )
    #     r.raise_for_status()
    #     video_url = r.json().get("video_url", "")
    # return ResultadoEscena(
    #     escena=prompt.escena, texto_escena=prompt.texto_escena,
    #     prompt_en=prompt.prompt_en, video_url=video_url, estado="listo",
    # )

    raise NotImplementedError(
        "Nodo 5 (Higgsfield) aun no implementado. Configura HIGGSFIELD_API_URL / "
        "HIGGSFIELD_API_KEY y completa la llamada real en la fase 2."
    )
