"""Cliente LLM con multiples proveedores.

Proveedores soportados:
  - "mock":      NO gasta dinero ni requiere clave. Genera texto plausible para
                 poder probar TODO el pipeline de extremo a extremo.
  - "anthropic": Claude (requiere paquete `anthropic` y ANTHROPIC_API_KEY).
  - "openai":    GPT (requiere paquete `openai` y OPENAI_API_KEY).

Cada nodo LLM solo llama a `client.complete(system, user)` y recibe texto.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from .config import Config


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


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                "El proveedor 'openai' requiere el paquete: pip install openai"
            ) from exc
        if not api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
        self._client = OpenAI(api_key=api_key)
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
        # El Nodo 3 es el unico que pide "STRICT JSON"; usamos ese marcador para
        # no confundirlo con el Nodo 2 (cuya formula menciona la palabra "JSON").
        pide_json = "strict json" in system.lower()
        if pide_json:
            return self._mock_json(user)
        return self._mock_guion(user)

    @staticmethod
    def _extraer_tema(user: str) -> str:
        m = re.search(r"IDEA BASE:\s*(.+)", user)
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
    if cfg.provider == "mock":
        return MockClient()
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg.anthropic_api_key, cfg.model)
    if cfg.provider == "openai":
        return OpenAIClient(cfg.openai_api_key, cfg.model)
    raise ValueError(
        f"Proveedor LLM desconocido: '{cfg.provider}'. "
        "Usa: mock | anthropic | openai"
    )
