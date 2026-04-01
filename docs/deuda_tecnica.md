# Deuda Técnica

## Pendiente

### Agente: detectar "On Ground" y pararse automáticamente
- Gonzalo cae al suelo (prone) después de dormir o por nausea
- Speed baja a 0.3, no puede saltar, es vulnerable
- **Fix**: detectar "On Ground" en STATUS_BAR → mandar `s` para pararse antes de cualquier otra acción

### Agente: detectar waterskin vacío
- El agente elige waterskin para beber pero puede estar vacío ("You lick the porcupine leather waterskin")
- Ahora INVENTORY muestra `(empty)` en waterskins — falta que el código de comer/beber lo use

### Agente: fast travel desactivado
- `viajar` (Shift+T) está desactivado porque DF se cuelga durante fast travel con deshidratación
- El agente no sabe navegar el mapa de viaje
- **Para reactivar**: implementar detección de modo travel y navegación del mapa

### Agente: interacción con edificios
- BUILDINGS ahora se detectan en DFHack (Well, Door, etc.)
- Falta lógica para acercarse y usar (ej: llenar waterskin en Well)

### Agente: búsqueda de agua inteligente
- Depende de: inventario (waterskin vacío) + buildings (Well cercano)
- El agente debería: detectar sed → buscar Well → acercarse → interactuar

### Autosave: no funciona en Adventure Mode
- `AUTOSAVE:SEASONAL` en d_init.txt es solo para Fortress Mode
- No existe quicksave para Adventure Mode en DFHack 0.47
- **Estado actual**: save manual antes de cada rebuild/cambio mayor

### Ghost: configurar subdominio caminoalaruina.dialogo.studio
- Requiere: registro A en Netlify DNS + nginx reverse proxy con SSL en VPS
- Ghost actualmente accesible solo por IP directa

## Resuelto (2026-04-01)

### OpenAI quota agotada → migración a DeepSeek
- Causa: $10 USD gastados, API key sin créditos
- Fix: agregar DeepSeek como provider en llm.py, cambiar .env

### Filtro deity bloqueaba conversaciones
- Causa: `_encontrar_npc_en_menu` filtraba "deity", loop infinito cuando solo había deity
- Fix: quitar "deity" de la lista de exclusión

### Narrador inventaba personajes
- Causa: sin NPCs en los logs, el LLM fabricaba diálogos
- Fix: regla explícita en system prompt — solo usar NPCs de logs o biblia

### Agente no veía inventario ni hostiles
- Fix: extender dfhack_state.lua con INVENTORY, hostilidad (isDanger), GROUND items, BUILDINGS, dirección relativa

### Agente hablaba con nadie (d>3)
- Fix: bloquear hablar_npc si no hay NPC con nombre a d<=3, acercarse primero

### Agente no huía de hostiles
- Fix: escape automático en dirección opuesta cuando hostile a d<5

### Logs enormes para el narrador
- Fix: comprimir_log.py reduce 53K→1K líneas (98%), narrador usa .comprimido.md

### Modelo separado para narrador
- Fix: NARRADOR_LLM_PROVIDER/MODEL/API_KEY en .env, completar_narrador() en llm.py

### Cron en timezone incorrecto
- Fix: usar hora UTC (23:30 = 20:30 Chile) en vez de CRON_TZ

### Twitter/X configurado (2026-04-01)
- Cuenta creada, API keys generadas, variables en .env del VPS

### Ghost: título limpio + tag de maleta (2026-04-01)
- Título sin "Maleta 001 —", tag automático para agrupar por maleta

## Resuelto (anterior)

### Narrador repetía el mismo episodio cada día (2026-03-25)
### Context window overflow en logs grandes (2026-03-25)
### dia_vida y dia_mundo no se incrementaban (2026-03-26)
### LLM generaba listas disfrazadas de párrafo (2026-03-26)
### Gonzalo preguntaba como encuestador (2026-03-26)
### maleta_update se pegaba al episodio (2026-03-28)
### Agente comía en loop hasta nausea (2026-03-28)
### Stream switch on/off (2026-03-25)
### Stream overlay con ubicación (2026-03-25)
