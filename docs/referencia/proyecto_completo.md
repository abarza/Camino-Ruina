# Camino a la Ruina — Documentación del Proyecto

## Qué es

Un motor narrativo automatizado 24/7 que juega Dwarf Fortress en modo Aventura como **Gonzalo**, un periodista gonzo (Hunter S. Thompson + Anthony Bourdain). Gonzalo viaja por el mundo con una pregunta central: **¿Por qué la gente construye cosas que sabe que va a perder?**

El sistema produce tres cosas automáticamente:
1. **Stream en vivo** — YouTube Live mostrando la terminal del juego + overlay con ubicación
2. **Crónicas diarias** — Episodios de 300-500 palabras publicados a Ghost (blog), Telegram, Twitter y newsletter por email
3. **Logs crudos** — Registro de cada acción del juego, uno por día (~5MB/día)

Todo corre en un VPS de Hetzner ($3.49/mes) dentro de un container Docker, sin intervención humana.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER CONTAINER (camino)                     │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐    │
│  │   tmux   │◄──►│  DF 0.47.05  │◄──►│  DFHack 0.47.05-r8 │    │
│  │ (sesión) │    │  (text mode) │    │  (estado del juego) │    │
│  └────┬─────┘    └──────────────┘    └──────────┬──────────┘    │
│       │                                          │               │
│       │ capture-pane / send-keys                 │ dfhack-run    │
│       ▼                                          ▼               │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              agente_jugador.py (24/7)                │        │
│  │  Lee estado → Decide acción → Envía teclas → Loguea │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │ append                                 │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │               mundo/ (filesystem bus)                │        │
│  │  logs/YYYY-MM-DD.md  maletas/  biblia/  diario.md   │        │
│  └──────────┬──────────────────────────────┬───────────┘        │
│             │ lee logs                      │                    │
│             ▼                               │                    │
│  ┌────────────────────┐                     │                    │
│  │ narrador_nocturno  │ cron 20:30          │                    │
│  │ (LLM → episodio)  │────────────────────►│                    │
│  └────────┬───────────┘  escribe maleta     │                    │
│           │                                  │                    │
│           ▼                                  │                    │
│  ┌────────────────────┐                     │                    │
│  │   distribuidor     │                     │                    │
│  │ Ghost·Telegram·X   │                     │                    │
│  └────────────────────┘                     │                    │
│                                              │                    │
│  ┌────────────────────┐    ┌───────────┐    │                    │
│  │ stream_overlay.py  │───►│ stream.sh │    │                    │
│  │ (ubicación c/30s)  │    │ ffmpeg→YT │    │                    │
│  └────────────────────┘    └───────────┘    │                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│   ghost (container)  │  Puerto 80 — Blog + Newsletter
└─────────────────────┘
```

### Principio clave: Filesystem como bus

No hay bases de datos, colas de mensajes ni memoria compartida. Todos los agentes se comunican a través de archivos en `mundo/`:

| Archivo | Escritor | Lectores |
|---------|----------|----------|
| `logs/YYYY-MM-DD.md` | agente_jugador | narrador |
| `maletas/maleta_001.md` | narrador | distribuidor |
| `diario.md` | narrador | narrador (siguiente día) |
| `biblia/personajes.md` | narrador | narrador |
| `.ultimo_log_procesado` | narrador | narrador |
| `.ultimo_episodio_hash` | distribuidor | distribuidor |

Un solo escritor por archivo. Sin colisiones.

---

## Componentes

### 1. Agente Jugador (`scripts/agente_jugador.py`)

Loop infinito que juega DF cada 10 segundos:
- **Lee** el estado del juego via DFHack (posición, HP, NPCs cercanos, sitio, región)
- **Captura** la pantalla de DF via tmux
- **Decide** qué hacer: 16 intenciones posibles (explorar, hablar, pelear, comer, huir, etc.)
- **Envía** teclas a DF via tmux
- **Loguea** todo en `mundo/logs/{fecha}.md`

Dos modos de decisión:
- **Mecánico** (default): secuencia fija de teclas configurada en `.env`
- **LLM** (`USE_LLM_INTENTIONS=1`): el LLM elige la intención según contexto

### 2. Narrador Nocturno (`scripts/narrador_nocturno.py`)

Cron a las 20:30 (hora Santiago). Toma los logs del día y genera la crónica:
- **Limpia** los logs: elimina duplicados, comprime info de NPCs cercanos, quita ruido
- **Trunca** inteligentemente: mantiene primeros 5 + últimos 10 turnos, prioriza combate y conversación
- **Llama al LLM** con: logs del día + resumen de la maleta + biblia de personajes + diario
- **Extrae** del LLM: episodio + actualización de maleta + diario + biblia
- **Escribe** todo a los archivos correspondientes
- **Marca** el log como procesado (no se repite mañana)

Protecciones:
- Si el contexto se pasa del límite → retry automático con 40% menos budget
- Si el LLM falla → escribe un stub (evidencia de fallo, no contamina la narrativa)
- Si el log ya fue procesado → no hace nada

### 3. Distribuidor (`scripts/distribuidor.py`)

Se ejecuta después del narrador. Publica el último episodio:
- **Ghost** → crea post en el blog (mobiledoc format)
- **Telegram** → envía al canal configurado
- **Twitter/X** → publica extracto con link
- **Newsletter** → Ghost lo maneja nativamente via Resend SMTP

Protecciones:
- Hash SHA-256 del episodio → no republica el mismo contenido
- Cada canal es independiente → si uno falla, los demás siguen
- `--dry-run` para ver qué publicaría sin publicar

### 4. Stream (`docker/stream.sh` + `scripts/stream_overlay.py`)

YouTube Live 24/7 de la terminal de DF:
- **Xvfb** → display virtual (sin GPU)
- **xterm** → terminal conectada a tmux donde corre DF
- **ffmpeg** → captura el display y lo envía por RTMP a YouTube
- **Overlay** → daemon Python que cada 30s consulta DFHack y escribe la ubicación actual

Control remoto sin reiniciar container:
```bash
docker compose exec camino stream_control.sh start   # prender
docker compose exec camino stream_control.sh stop    # apagar
docker compose exec camino stream_control.sh status  # ver estado
```

### 5. LLM (`scripts/llm.py`)

Interfaz unificada para OpenAI y Anthropic:
- Soporta: gpt-4o, gpt-4o-mini, gpt-4.1-mini, gpt-5.4-mini, gpt-5.2, Claude Sonnet/Haiku
- Cap configurable de tokens (`MAX_PROMPT_TOKENS`, default 120k)
- Retry automático en errores transitorios
- Temperature 0.9 para creatividad narrativa

### 6. Preview (`scripts/preview_narrador.py`)

Testing sin tocar estado real:
```bash
# Qué escribiría el narrador hoy
docker compose exec camino python3 -m scripts.preview_narrador

# Con una fecha específica
docker compose exec camino python3 -m scripts.preview_narrador 2026-03-24

# Qué publicaría el distribuidor
docker compose exec camino python3 -m scripts.distribuidor --dry-run
```

Guarda resultado en `mundo/preview/` sin tocar maleta ni diario.

---

## Stack Técnico

| Capa | Tecnología |
|------|-----------|
| Juego | Dwarf Fortress 0.47.05 (text mode, ncurses) |
| Modding | DFHack 0.47.05-r8 (Lua scripting para leer estado) |
| Terminal | tmux (multiplexor, I/O con DF) |
| Lenguaje | Python 3 + venv |
| LLM | OpenAI API (gpt-5.4-mini actualmente) |
| Blog | Ghost 5 (Alpine) con newsletter via Resend SMTP |
| Social | Telegram Bot API, Twitter/X API (tweepy) |
| Stream | Xvfb + xterm + ffmpeg → YouTube Live RTMP |
| Infra | Docker Compose, Ubuntu 24.04 |
| Hosting | Hetzner CX23, Helsinki, $3.49/mes |
| Repo | Git (todo versionado, incluyendo estado narrativo) |

Dependencias Python (7 paquetes):
```
python-dotenv, openai, anthropic, tweepy, PyJWT, requests
```

---

## Configuración (.env)

```env
# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
MAX_PROMPT_TOKENS=120000        # Cap para respetar TPM del tier

# Paths
MUNDO_DIR=/gonzalo/mundo
DF_DIR=/opt/df
APP_TZ=America/Santiago

# Agente
AGENT_AUTOSTART=1               # Arranca solo con el container
AGENT_TICK_SECONDS=10

# Stream
STREAM_ENABLED=1                # Arranca el stream al inicio
STREAM_KEY=...
STREAM_URL=rtmp://a.rtmp.youtube.com/live2
STREAM_RES=854x480
STREAM_FPS=5

# Publicación
GHOST_URL=http://...
GHOST_ADMIN_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=...
TWITTER_API_KEY=...
RESEND_API_KEY=...
```

---

## Gonzalo: La Voz

Gonzalo es un cronista que escribe sobre lo que ve, no lo que siente. Su estilo:

- **Prosa directa**, sin metáforas forzadas
- **Diálogos cortos** — la gente habla poco y dice mucho
- **Nunca explica** emociones — las muestra con acciones
- **Silencio > palabras** — lo que no se dice importa más
- **Sin listas**, sin bullets, sin resúmenes

Referencias de tono: Hunter S. Thompson (voz), Anthony Bourdain (lugares), The Wire (diálogos), This War of Mine (peso moral).

Cada "maleta" es una vida completa — desde el Día 1 hasta la muerte o pausa. Cuando Gonzalo muere, empieza una maleta nueva con un personaje nuevo, pero las maletas anteriores se heredan como contexto.

---

## Historia del Proyecto (commits clave)

| Fecha | Commit | Hito |
|-------|--------|------|
| Inicio | `be6cd40` | Repo limpio, sin secretos |
| | `de552c6` | CLAUDE.md para onboarding de IA |
| | `4b44fba` | 16 intenciones para Adventure Mode |
| | `ff0943b` | Narrador dinámico con estado |
| | `df01b3d` | Migración a DF 0.47.05 text mode (cambio arquitectural mayor) |
| | `8827a58` | Deploy en Hetzner VPS (Fase 6 completa) |
| | `122fcb2` | YouTube Live streaming |
| | `1a9aa1e` | Pipeline de distribución (Ghost+Telegram+Twitter) |
| | `cadfd85` | Ghost con Resend SMTP para newsletters |
| 2026-03-25 | `4c44f98` | Fix: narrador no repite episodios |
| | `9a944f2` | Fix: context overflow con auto-retry |
| | `b9fea79` | Fix: LLM no plagia de la maleta |
| | `fb16029` | Soporte GPT-5.4-mini y GPT-5.2 |
| | `b5ab072` | Stream on/off switch + overlay de ubicación |

### Problemas resueltos y cómo

**DF no corría en Docker** → Migración de DF 53.11 (SDL2, requería GPU) a DF 0.47.05 (text mode puro, ncurses). Cambio fundamental que habilitó todo.

**DFHack no arrancaba** → Necesita `seccomp:unconfined` y `setarch -R` para desactivar ASLR. Documentado en arquitectura.

**Narrador repetía el mismo post** → Triple fix: tracking de logs procesados, hash de episodios publicados, y resumir la maleta antes de enviarla al LLM.

**Context window overflow** → Budget dinámico que resta el tamaño real de maleta+biblia+diario, estimación conservadora (len/2.5), auto-retry con budget reducido, cap configurable de 120k.

**LLM copiaba de la maleta** → Se envía solo el resumen (header + último episodio marcado "NO repetir") + temperature 0.9.

**Rate limit de OpenAI** → Cap de tokens vía `MAX_PROMPT_TOKENS` para respetar el TPM del tier.

**Stream no se podía apagar** → Switch con archivo señal + watchdog que revisa antes de cada ciclo.

**Saves se perdían** → Autosave configurado: `AUTOSAVE:SEASONAL`, `AUTOBACKUP:YES`.

---

## Cómo empezar a contribuir

### Setup local

```bash
git clone <repo>
cd "Camino a la Ruina"
cp .env.example .env
# Editar .env con tus API keys

# Descargar DF 0.47.05 + DFHack 0.47.05-r8 en ./df/
# (pedir el tar.gz al equipo)

docker compose up --build -d
```

### Comandos útiles

```bash
# Ver el juego en vivo
docker compose exec camino tmux attach -t df
# (Ctrl+B, D para salir sin matar)

# Ver estado del agente
docker compose exec camino tail -f /var/log/agente.log

# Preview de la crónica de hoy
docker compose exec camino python3 -m scripts.preview_narrador

# Preview de qué se publicaría
docker compose exec camino python3 -m scripts.distribuidor --dry-run

# Control del stream
docker compose exec camino stream_control.sh start|stop|status

# Ver logs del narrador
docker compose exec camino tail -f /var/log/narrador_nocturno.log

# Ver logs del distribuidor
docker compose exec camino tail -f /var/log/distribuidor.log
```

### Estructura de archivos para nuevos agentes

Si quieres agregar un agente nuevo (ej: bot de Telegram, podcast):
1. Crear `scripts/mi_agente.py`
2. Leer de `mundo/` (logs, maletas, biblia, diario)
3. Escribir a su propio archivo en `mundo/`
4. Agregar al cron o al entrypoint si es daemon
5. Respetar el contrato: **un escritor por archivo**

### Deuda técnica pendiente

Ver `docs/deuda_tecnica.md` para items abiertos:
- Verificar que autosave de DF funciona sin save manual
- dia_vida/dia_mundo no se incrementan (el LLM no lo hace, hay que forzarlo en código)
- Ajustar MAX_PROMPT_TOKENS si se sube de tier en OpenAI

---

## Estructura de directorios

```
.
├── docker/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── launch_df.sh
│   ├── cron_narrador
│   ├── stream.sh
│   └── stream_control.sh
├── scripts/
│   ├── agente_jugador.py       # Juega DF 24/7
│   ├── narrador_nocturno.py    # Genera crónicas (cron 20:30)
│   ├── distribuidor.py         # Publica en Ghost/Telegram/X
│   ├── preview_narrador.py     # Testing sin estado
│   ├── llm.py                  # Interfaz OpenAI/Anthropic
│   ├── decisor_llm.py          # Decisiones del agente via LLM
│   ├── intenciones.py          # 16 acciones posibles
│   ├── tmux_io.py              # I/O con DF via tmux
│   ├── dfhack_io.py            # Estado del juego via DFHack
│   ├── dfhack_state.lua        # Extractor Lua de estado
│   └── stream_overlay.py       # Overlay de ubicación
├── mundo/
│   ├── logs/                   # Logs crudos (1 por día)
│   ├── maletas/                # Episodios narrativos
│   ├── biblia/                 # Personajes y mundo
│   ├── diario.md               # Estado narrativo
│   └── preview/                # Previews (gitignored)
├── docs/                       # Documentación completa
├── df/                         # DF + DFHack (no en repo)
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```
