"""Cliente LLM con multiples proveedores.

Proveedores soportados:
  - "mock":      NO gasta dinero ni requiere clave. Genera texto plausible para
                 poder probar TODO el pipeline de extremo a extremo.
  - "anthropic": Claude (requiere paquete `anthropic` y ANTHROPIC_API_KEY).
  - "openai":    GPT (requiere paquete `openai` y OPENAI_API_KEY).
  - "nvidia":    Modelos alojados por NVIDIA (build.nvidia.com) via su API
                 COMPATIBLE con OpenAI (requiere paquete `openai` y NVIDIA_API_KEY).
                 Util para estirar/abaratar tokens usando modelos abiertos
                 potentes (Llama, Nemotron, DeepSeek...) sin perder calidad.

Cada nodo LLM solo llama a `client.complete(system, user)` y recibe texto.

Si no se fija AGENTE_YT_LLM_MODEL, cada proveedor usa un modelo por defecto
razonable (ver `_MODELO_POR_DEFECTO`).
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from .config import Config

# Modelo por defecto de cada proveedor si no se fija AGENTE_YT_LLM_MODEL.
_MODELO_POR_DEFECTO = {
    "anthropic": "claude-3-5-sonnet-latest",
    "openai": "gpt-4o",
    # Modelo abierto potente y estable en build.nvidia.com; buen equilibrio
    # calidad/coste. El usuario puede cambiarlo con AGENTE_YT_LLM_MODEL.
    "nvidia": "meta/llama-3.3-70b-instruct",
}


def _resolver_modelo(cfg: Config) -> str:
    """Devuelve el modelo configurado o el por defecto del proveedor."""
    return cfg.model or _MODELO_POR_DEFECTO.get(cfg.provider, "")


class LLMClient(ABC):
    """Interfaz comun a todos los proveedores."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Devuelve la respuesta del modelo como texto plano."""
        raise NotImplementedError


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                "El proveedor 'anthropic' requiere el paquete: pip install anthropic"
            ) from exc
        if not api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )


class OpenAICompatibleClient(LLMClient):
    """Cliente para cualquier API compatible con OpenAI (OpenAI y NVIDIA).

    NVIDIA (build.nvidia.com) expone `/v1/chat/completions` con el mismo formato
    que OpenAI, asi que basta con cambiar `base_url` y la clave.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str | None = None,
        env_var: str = "OPENAI_API_KEY",
        paquete_hint: str = "openai",
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                f"Este proveedor requiere el paquete: pip install {paquete_hint}"
            ) from exc
        if not api_key:
            raise RuntimeError(f"Falta {env_var} en el entorno (.env).")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


class MockClient(LLMClient):
    """Proveedor de prueba: sin red, sin coste, deterministico.

    Detecta si se le pide un GUION o un JSON de PROMPTS y responde acorde,
    para que el pipeline completo se pueda validar sin claves.
    """

    def complete(self, system: str, user: str) -> str:
        s = system.lower()
        # El Nodo 12 pide "youtube metadata"; el Nodo 3 pide "strict json".
        if "youtube metadata" in s:
            return self._mock_metadatos(user)
        if "strict json" in s:
            return self._mock_json(user)
        return self._mock_guion(user)

    def _mock_metadatos(self, user: str) -> str:
        tema = self._extraer_tema(user) or "video infantil"
        return json.dumps(
            {
                "titulo": f"{tema} | Cancion infantil educativa",
                "descripcion": (
                    f"Cancion infantil sobre {tema}. Aprende y canta con nosotros. "
                    "Suscribete para mas videos educativos para ninos."
                ),
                "tags": [tema, "cancion infantil", "educativo", "ninos", "aprender"],
                "hashtags": ["#infantil", "#canciones", "#ninos"],
            },
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def _extraer_tema(user: str) -> str:
        m = re.search(r"(?:IDEA BASE|TOPIC):\s*(.+)", user)
        if m:
            return m.group(1).strip().splitlines()[0]
        return "tema infantil"

    def _mock_guion(self, user: str) -> str:
        tema = self._extraer_tema(user)
        return (
            f"TITULO: Cancion de {tema}\n\n"
            "Escena 1 (0:00-0:08)\n"
            f"LETRA: Vamos todos a aprender sobre {tema}, la la la.\n"
            "ACCION VISUAL: Un bebe sonriente de mejillas rosadas salta en un "
            "dormitorio colorido y soleado, colores pastel, plano frontal.\n\n"
            "Escena 2 (0:08-0:16)\n"
            f"LETRA: {tema.capitalize()} es divertido, hazlo bien, uno dos tres.\n"
            "ACCION VISUAL: La mama abraza al bebe junto a una ventana grande con "
            "luz calida, estilo 3D suave tipo dibujo animado.\n\n"
            "Escena 3 (0:16-0:24)\n"
            "LETRA: Aplaudimos y cantamos, que feliz es aprender.\n"
            "ACCION VISUAL: El bebe y un perrito de dibujos aplauden entre globos "
            "de colores, fondo brillante, camara ligeramente en picado.\n"
        )

    def _mock_json(self, user: str) -> str:
        # Genera un JSON valido a partir del guion recibido en `user`.
        escenas = []
        for i, bloque in enumerate(re.split(r"Escena\s+\d+", user)[1:], start=1):
            tiempo = ""
            mt = re.search(r"\(([\d:\-\s]+)\)", bloque)
            if mt:
                tiempo = mt.group(1).strip()
            texto = ""
            ml = re.search(r"LETRA:\s*(.+)", bloque)
            if ml:
                texto = ml.group(1).strip().splitlines()[0]
            escenas.append(
                {
                    "escena": i,
                    "rango_tiempo": tiempo,
                    "texto_escena": texto,
                    "prompt_en": (
                        f"Scene {i}: a cute smiling toddler with rosy cheeks in a "
                        "colorful sunny room, soft 3D cartoon style, pastel colors, "
                        "cheerful lighting, frontal shot"
                    ),
                }
            )
        if not escenas:
            escenas = [
                {
                    "escena": 1,
                    "rango_tiempo": "0:00-0:08",
                    "texto_escena": "",
                    "prompt_en": (
                        "a cute smiling toddler in a colorful room, soft 3D cartoon "
                        "style, pastel colors, cheerful lighting"
                    ),
                }
            ]
        return json.dumps({"escenas": escenas}, ensure_ascii=False, indent=2)


def build_client(cfg: Config) -> LLMClient:
    """Fabrica el cliente segun la configuracion."""
    modelo = _resolver_modelo(cfg)
    if cfg.provider == "mock":
        return MockClient()
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg.anthropic_api_key, modelo)
    if cfg.provider == "openai":
        return OpenAICompatibleClient(
            cfg.openai_api_key, modelo, env_var="OPENAI_API_KEY"
        )
    if cfg.provider == "nvidia":
        return OpenAICompatibleClient(
            cfg.nvidia_api_key,
            modelo,
            base_url=cfg.nvidia_base_url,
            env_var="NVIDIA_API_KEY",
        )
    raise ValueError(
        f"Proveedor LLM desconocido: '{cfg.provider}'. "
        "Usa: mock | anthropic | openai | nvidia"
    )
