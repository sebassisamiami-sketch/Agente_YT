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
| 9. Subtítulos | `subtitulos.py` | Genera SRT desde las letras (opcionalmente quemado) | Activo y validado |
| 10. Miniatura | `thumbnail.py` | Thumbnail 1280x720 con el título (libass) | Activo y validado |
| 11. Subida YouTube | `youtube.py` | Publica el vídeo vía Data API v3 (OAuth) | Implementado (requiere OAuth) |
| 12. Metadatos SEO | `metadatos.py` | Título, descripción, tags y hashtags con el LLM | Activo y validado |
| 13. Intro / Outro | `intro_outro.py` | Portada y cierre animados (libass + fade) | Activo y validado |

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

## Comprobar la configuración (`--verificar`)

Antes de gastar créditos, comprueba qué está bien configurado (no genera nada ni
publica; solo hace lecturas):

```bash
python -m agente_yt --verificar
```

Muestra el estado de: **ffmpeg**, **LLM** (hace una llamada mínima), **Higgsfield**
(lectura de estilos para validar la clave), **Voz/TTS** y **YouTube** (paquetes,
`client_secrets` y token, sin abrir el navegador). Estados: `OK`, `AVISO`,
`FALLO`, `OMITIDO`. Úsalo tras poner cada clave para confirmar que funciona.

## Configurar las 3 claves (resumen)

1. **LLM** (elige uno): `NVIDIA_API_KEY` (build.nvidia.com, gratis/barato) o
   `ANTHROPIC_API_KEY` o `OPENAI_API_KEY`. Pon `AGENTE_YT_LLM_PROVIDER` acorde.
2. **Higgsfield**: `HIGGSFIELD_API_KEY` + `HIGGSFIELD_SECRET` desde
   https://cloud.higgsfield.ai/api-keys (genera imágenes/vídeo; consume créditos).
3. **YouTube** (solo para subir): OAuth de "App de escritorio" en Google Cloud con
   "YouTube Data API v3"; descarga el `client_secrets.json` y apunta
   `AGENTE_YT_YT_CLIENT_SECRETS`.

Tras cada paso: `python -m agente_yt --verificar`.

## Usar un LLM real (Claude, GPT o NVIDIA)

1. Copia `.env.example` a `.env`.
2. Elige proveedor y pon tu clave. Deja `AGENTE_YT_LLM_MODEL` vacío para usar el
   modelo por defecto de cada proveedor.
   ```ini
   # Claude
   AGENTE_YT_LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-...

   # o GPT
   AGENTE_YT_LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-...

   # o NVIDIA (modelos abiertos via API compatible con OpenAI)
   AGENTE_YT_LLM_PROVIDER=nvidia
   NVIDIA_API_KEY=nvapi-...
   # AGENTE_YT_LLM_MODEL=meta/llama-3.3-70b-instruct   # opcional
   ```
3. Instala el SDK: `pip install anthropic` (Claude) o `pip install openai`
   (GPT **y** NVIDIA, que comparten SDK).
4. Ejecuta el mismo comando de arriba.

### ¿Por qué NVIDIA?

La API de NVIDIA (build.nvidia.com) sirve modelos abiertos potentes (Llama 3.3,
Nemotron, DeepSeek, Qwen...) con un endpoint **compatible con OpenAI**. Es una
forma de **estirar/abaratar tus tokens sin sacrificar calidad**: el pipeline usa
exactamente el mismo código y contrato (incluido el JSON estricto del nodo 3),
solo cambia la `base_url` y la clave. Modelos por defecto por proveedor:

| Proveedor | Modelo por defecto |
|-----------|--------------------|
| `anthropic` | `claude-3-5-sonnet-latest` |
| `openai` | `gpt-4o` |
| `nvidia` | `meta/llama-3.3-70b-instruct` |

### Modo `multi`: repartir entre varios proveedores

Puedes usar **NVIDIA + Claude + OpenAI a la vez** para repartir la carga (y el
coste) y ganar robustez: si uno falla o tarda demasiado, salta al siguiente
automáticamente.

```ini
AGENTE_YT_LLM_PROVIDER=multi
AGENTE_YT_LLM_PROVIDERS=nvidia,anthropic,openai   # orden de rotacion
AGENTE_YT_LLM_TIMEOUT=60                           # segundos por llamada
# + las claves de los que quieras usar (NVIDIA_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY)
```

- **Rotación round-robin:** cada llamada usa el siguiente proveedor.
- **Fallback:** si un proveedor da error o supera el timeout, prueba el siguiente.
- Solo se usan los proveedores que tengan credenciales (los demás se omiten).
- `AGENTE_YT_LLM_TIMEOUT` evita que una respuesta lenta cuelgue el proceso (aplica
  a todos los modos, no solo `multi`).

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

## Subtítulos (nodo 9)

Genera un `.srt` a partir de las letras del guion, usando el rango de tiempo de
cada escena (si falta, se distribuye por duración):

```bash
python -m agente_yt "Cancion de los colores" --srt         # solo el archivo .srt
python -m agente_yt "Cancion de los colores" --subtitulos  # además los QUEMA en el vídeo
```

## Música de fondo

Se mezcla en bucle **por debajo de la voz** (volumen bajo por defecto):

```bash
python -m agente_yt "Cancion de los colores" --todo \
    --musica ./musica.mp3 --volumen-musica 0.15
```

## Modo lote (varios vídeos)

Genera un vídeo por cada línea de un archivo (`tema | idioma | duracion`; solo el
tema es obligatorio). Cada vídeo va a su propia subcarpeta en `salidas/lote/`:

```bash
# temas.txt:
#   Cancion de los colores | es | 60
#   Song about numbers | en
python -m agente_yt --lote temas.txt --todo
```

## Miniatura / thumbnail (nodo 10)

Genera una miniatura **1280x720** (estándar de YouTube) con el título superpuesto,
a partir de una imagen de escena o de un fotograma del vídeo final:

```bash
python -m agente_yt "Cancion de los colores" --todo --miniatura
```

## Subir a YouTube (nodo 11)

Publica el vídeo final con la API de YouTube. La subida usa **OAuth2** (no basta
una API key):

1. En Google Cloud: habilita "YouTube Data API v3" y crea credenciales OAuth de
   tipo "App de escritorio"; descarga el `client_secrets.json`.
2. Instala: `pip install google-api-python-client google-auth google-auth-oauthlib`.
3. Configura `.env`:
   ```ini
   AGENTE_YT_YT_CLIENT_SECRETS=/ruta/client_secrets.json
   AGENTE_YT_YT_PRIVACY=unlisted        # private | unlisted | public
   ```
4. Sube (la primera vez se abre el navegador para dar consentimiento):
   ```bash
   python -m agente_yt "Cancion de los colores" --todo --subir --privacidad unlisted
   ```

> La subida marca el vídeo como "hecho para niños" (COPPA) y fija la miniatura si
> se generó. Por seguridad, `--todo` **no** sube solo: subir siempre es explícito
> con `--subir`.

## Metadatos SEO (nodo 12)

Genera con el LLM un **título optimizado, descripción, tags y hashtags** a partir
del guion, y los usa al subir a YouTube (o los guarda en `salidas/metadatos.json`):

```bash
python -m agente_yt "Cancion de los colores" --metadatos
```

## Intro / outro animados (nodo 13)

Añade una **portada** (con el título) y un **cierre** (llamada a suscribirse) con
fundidos. Los subtítulos y la voz se re-sincronizan automáticamente con las
escenas (la voz se retrasa por la duración de la intro):

```bash
python -m agente_yt "Cancion de los colores" --todo --intro-outro
```
El texto del cierre y las duraciones se configuran con `AGENTE_YT_OUTRO_TEXTO`,
`AGENTE_YT_INTRO_DUR` y `AGENTE_YT_OUTRO_DUR`.

## Todo en uno

```bash
python -m agente_yt "Cancion de los colores para ninos" --todo
```

Encadena: guion → **metadatos SEO** → prompts → Higgsfield (imagen/vídeo) → voz
(TTS) → subtítulos → **intro/outro** → montaje final (subtítulos quemados) →
**miniatura**. Cada etapa informa su estado; si faltan credenciales de Higgsfield,
avisa y no gasta créditos. Añade `--subir` para publicar en YouTube con los
metadatos generados.

## Personalización

- Edita `config/formula_cocomelon.md` para ajustar el estilo, los tiempos o la
  estructura del guion sin tocar el código.
