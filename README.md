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
| 5. Higgsfield (video) | `higgsfield.py` | Envía cada prompt a la IA de video | **Stub (fase 2)** |
| 6. Almacenamiento | `almacenamiento.py` | Guarda JSON y tabla final | Activo |

> Siguiendo la recomendación de construir por fases, los **nodos 1→3** están
> completos y **validados**. El nodo 5 (Higgsfield) queda como stub con el
> contrato y el esqueleto de la llamada listos para conectar cuando el JSON del
> nodo 3 esté perfecto y tengas credenciales.

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

## Fase 2: conectar Higgsfield (nodo 5)

Cuando el JSON del nodo 3 te convenza:
1. Rellena `HIGGSFIELD_API_URL` y `HIGGSFIELD_API_KEY` en `.env`.
2. Completa la llamada real en `higgsfield.py` (el esqueleto `httpx` ya está ahí).
3. Ejecuta con `--generar-video` para recorrer las escenas y volcar la tabla
   final `Escena | Texto | Link` en `salidas/tabla_final.csv`.

## Nota honesta

El "dinero fácil" que promete el video de origen no es la realidad de YouTube:
crear el contenido es solo una parte; el algoritmo, la constancia y la
monetización requieren mucho trabajo. Esta herramienta automatiza la parte
técnica (guion + prompts), pero el montaje final, la voz/música y la estrategia
de canal siguen siendo tuyos. Además, generar los clips en Higgsfield **consume
créditos de pago**.

## Personalización

- Edita `config/formula_cocomelon.md` para ajustar el estilo, los tiempos o la
  estructura del guion sin tocar el código.
