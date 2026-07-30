"""Agente_YT: pipeline por nodos para generar contenido infantil de YouTube.

Arquitectura (cada nodo = un modulo con una unica responsabilidad):

    Nodo 1  entrada.py            -> Entrada / Trigger (idea base)
    Nodo 2  guionista.py          -> Agente Guionista (LLM, formula Cocomelon)
    Nodo 3  prompts_visuales.py   -> Agente de Prompts Visuales (LLM -> JSON)
    Nodo 4  iterador.py           -> Iterador / Bucle
    Nodo 5  higgsfield.py         -> Generacion de imagen/video (API Higgsfield)
    Nodo 6  almacenamiento.py     -> Salida / tabla final
    Nodo 7  montaje.py            -> Montaje final del video con ffmpeg
    Nodo 8  voz.py                -> Narracion de voz (TTS) de las letras
    Nodo 9  subtitulos.py         -> Subtitulos SRT (opcionalmente quemados)
    Nodo 10 thumbnail.py          -> Miniatura/thumbnail 1280x720 con titulo
    Nodo 11 youtube.py            -> Subida del video a YouTube (Data API v3)
    Nodo 12 metadatos.py          -> Metadatos SEO (titulo/descripcion/tags) con LLM
    Nodo 13 intro_outro.py        -> Portada (intro) y cierre (outro) animados

El orquestador (pipeline.py) conecta 1 -> 2 -> 3, que es lo que se valida
primero segun el consejo de construir por fases. El nodo 5 requiere credenciales
de Higgsfield, el nodo 7 usa ffmpeg (montaje, musica, quemado de subtitulos e
intro/outro), el nodo 8 sintetiza la voz, el 9 los subtitulos, el 10 la miniatura,
el 11 sube a YouTube (OAuth), el 12 genera metadatos SEO con el LLM y el 13 crea
la portada y el cierre. `--todo` encadena las fases; `--subir` publica en YouTube;
`--lote` (lote.py) produce varios videos desde un archivo de temas.
"""

__version__ = "0.6.0"
