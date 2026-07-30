"""Agente_YT: pipeline por nodos para generar contenido infantil de YouTube.

Arquitectura (cada nodo = un modulo con una unica responsabilidad):

    Nodo 1  entrada.py            -> Entrada / Trigger (idea base)
    Nodo 2  guionista.py          -> Agente Guionista (LLM, formula Cocomelon)
    Nodo 3  prompts_visuales.py   -> Agente de Prompts Visuales (LLM -> JSON)
    Nodo 4  iterador.py           -> Iterador / Bucle
    Nodo 5  higgsfield.py         -> Generacion de imagen/video (API Higgsfield)
    Nodo 6  almacenamiento.py     -> Salida / tabla final
    Nodo 7  montaje.py            -> Montaje final del video con ffmpeg

El orquestador (pipeline.py) conecta 1 -> 2 -> 3, que es lo que se valida
primero segun el consejo de construir por fases. El nodo 5 requiere credenciales
de Higgsfield y el nodo 7 usa ffmpeg como paso final del montaje.
"""

__version__ = "0.2.0"
