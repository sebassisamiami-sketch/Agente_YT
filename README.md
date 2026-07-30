# Agente_YT

Pipeline por **nodos** para generar contenido infantil de YouTube (estilo Cocomelon):
de una idea base a un guion y a un JSON de prompts visuales listos para una IA de video.

No es un lienzo visual: es **código real** en Python, donde cada "nodo" de la
arquitectura es un módulo con una única responsabilidad. Así tienes control total,
sin límites de plataforma.

## Arquitectura (6 nodos)

| Nodo | Módulo | Rol | Estado |
|------|--------|-----|--------|
| 1. Entrada / Trigger | `entrada.py` | Recibe la idea base del video | Activo |
| 2. Agente Guionista | `guionista.py` | LLM + fórmula Cocomelon → guion | Activo |
| 3. Prompts Visuales | `prompts_visuales.py` | LLM → JSON estricto en inglés | Activo |
| 4. Iterador / Bucle | `iterador.py` | Recorre las escenas una a una | Activo |
| 5. Higgsfield (imagen/vídeo) | `higgsfield.py` | Texto→imagen (Soul) y opcional imagen→vídeo (DoP) | Implementado (requiere claves) |
| 6. Almacenamiento | `almacenamiento.py` | Guarda JSON y tabla final | Activo |
| 7. Montaje final | `montaje.py` | Une imágenes/clips + audio en un MP4 (ffmpeg) | Activo y validado |
| 8. Voz / Narración | `voz.py` | TTS de las letras del guion (edge/gTTS/openai/mock) | Activo y validado |

> Los **nodos 1→3** están completos y **validados** en modo mock. El **nodo 5
> (Higgsfield)** ya está implementado contra la API REST oficial, pero requiere
> tus claves y consumir créditos, por lo que **no se ha podido probar en vivo**
> desde el sandbox: su parseo de respuesta es defensivo y podría necesitar un
> ajuste menor con tráfico real (ver nota más abajo).

## Uso rápido (modo `mock`, sin claves ni coste)

El proveedor `mock` genera texto de prueba deterministico para validar TODO el
pipeline **sin gastar dinero ni necesitar claves de API**.

```bash
pip install -r requirements.txt          # pydantic, python-dotenv, httpx
export PYTHONPATH=src                     # o instala el paquete
python -m agente_yt "Cancion sobre lavarse los dientes para ninos de 3 anos" \
    --idioma es --duracion 60
```

Genera en `salidas/`:
- `guion.json` — el guion completo (nodo 2).
- `prompts.json` — el JSON validado de prompts visuales en inglés (nodo 3).

## Usar un LLM real (Claude o GPT)

1. Copia `.env.example` a `.env`.
2. Elige proveedor y pon tu clave:
   ```ini
   AGENTE_YT_LLM_PROVIDER=anthropic      # o: openai
   AGENTE_YT_LLM_MODEL=claude-3-5-sonnet-latest
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Instala el SDK correspondiente: `pip install anthropic` (o `pip install openai`).
4. Ejecuta el mismo comando de arriba.

## Fase 2: generar imágenes/vídeo con Higgsfield (nodo 5)

Higgsfield expone una **API REST oficial** en `platform.higgsfield.ai` (no una API
key simple, sino `KEY:SECRET`). Su flujo es **image-first**: de un prompt de texto
genera una **imagen** (modelo Soul) y, opcionalmente, anima esa imagen a un **vídeo**
(modelo DoP) usando un `motion_id`.

1. Consigue tus claves en https://cloud.higgsfield.ai/api-keys y ponlas en `.env`:
   ```ini
   HIGGSFIELD_API_KEY=...
   HIGGSFIELD_SECRET=...
   HIGGSFIELD_QUALITY=1080p
   ```
2. Instala el cliente HTTP: `pip install httpx` (ya está en `requirements.txt`).
3. (Opcional, para animar a vídeo) descubre los motions disponibles y fija uno:
   ```bash
   python -m agente_yt --listar-motions        # copia un "id"
   # en .env:  HIGGSFIELD_MOTION_ID=<ese-id>
   ```
4. Ejecuta con `--generar-video`. El pipeline recorre cada escena (nodo 4),
   genera imagen → (opcional) vídeo (nodo 5) y vuelca la tabla final
   `Escena | Texto | Imagen | Vídeo` en `salidas/tabla_final.csv` (nodo 6).

> Cada generación **consume créditos de pago** (imagen 1080p ~3 créditos; vídeo
> DoP turbo ~6.5). Sin credenciales, el nodo 5 devuelve las escenas en estado
> `pendiente` y no gasta nada, para que puedas validar la fase 1 tranquilo.

> Nota técnica honesta: las rutas y el payload de la API provienen de clientes
> MCP públicos de la comunidad. La forma exacta de la respuesta de
> `/v1/job-sets/{id}` no está documentada oficialmente, así que el parseo del
> estado/URL es **defensivo** (busca las claves habituales de forma recursiva) y
> podría necesitar un pequeño ajuste al probarlo contra tráfico real. No se puede
> probar en el sandbox (requiere credenciales y consumir créditos).

## Nota honesta

El "dinero fácil" que promete el video de origen no es la realidad de YouTube:
crear el contenido es solo una parte; el algoritmo, la constancia y la
monetización requieren mucho trabajo. Esta herramienta automatiza la parte
técnica (guion + prompts), pero el montaje final, la voz/música y la estrategia
de canal siguen siendo tuyos. Además, generar los clips en Higgsfield **consume
créditos de pago**.

## Paso final: montaje del vídeo (nodo 7)

El "Paso 5" que el vídeo de origen ni mostraba: ensamblar los clips/imágenes +
la voz o música en el vídeo final listo para subir. Usa **ffmpeg**.

Monta todos los medios de una carpeta (ordenados por nombre de archivo), con una
pista de audio opcional:

```bash
python -m agente_yt --montar-dir ./mis_clips \
    --audio ./cancion.mp3 \
    --salida ./salidas/video_final.mp4 \
    --duracion-imagen 5      # segundos por imagen fija
```

- Las **imágenes** fijas reciben un suave efecto Ken Burns (zoom lento); desactívalo
  con `--sin-zoom`.
- Todo se normaliza a `AGENTE_YT_VIDEO_SIZE` (1920x1080 por defecto) y
  `AGENTE_YT_VIDEO_FPS` (30), y se exporta como MP4 H.264 + AAC.
- ffmpeg se busca en `AGENTE_YT_FFMPEG`, luego en el PATH y, como último recurso,
  el que trae el paquete opcional `imageio-ffmpeg` (`pip install imageio-ffmpeg`).

Programáticamente también puedes montar directamente desde los resultados del
nodo 5 con `montaje.montar_desde_resultados(...)`.

## Voz / narración (nodo 8)

Narra automáticamente las **letras** del guion (no las indicaciones visuales) y
usa esa pista como audio del montaje. Proveedores de TTS:

- `mock` — offline, sin red ni clave (audio de placeholder para pruebas).
- `edge` — **Microsoft Edge TTS, gratis y sin clave** (voz neuronal; `pip install edge-tts`).
- `gtts` — Google Translate TTS, gratis y sin clave (`pip install gTTS`).
- `openai` — OpenAI TTS (requiere `OPENAI_API_KEY`).

```ini
# en .env
AGENTE_YT_TTS_PROVIDER=edge
AGENTE_YT_TTS_VOICE=es-ES-AlvaroNeural   # opcional
```

```bash
# genera la voz y móntala en el vídeo:
python -m agente_yt "Cancion de los colores" --narrar
```

Con `--todo`, la narración se genera y se usa como audio del montaje
automáticamente (salvo que pases un `--audio` explícito, que tiene prioridad).

## Todo en uno

```bash
python -m agente_yt "Cancion de los colores para ninos" --todo
```

Encadena: guion → prompts → Higgsfield (imagen/vídeo) → voz (TTS) → montaje final.
Cada etapa informa su estado; si faltan credenciales de Higgsfield, avisa y no
gasta créditos.

## Personalización

- Edita `config/formula_cocomelon.md` para ajustar el estilo, los tiempos o la
  estructura del guion sin tocar el código.
