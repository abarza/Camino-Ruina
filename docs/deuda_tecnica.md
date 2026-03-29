# Deuda Técnica

## Pendiente

### Agente: detectar "On Ground" y pararse automáticamente
- Gonzalo cae al suelo (prone) después de dormir o por nausea
- Speed baja a 0.3, no puede saltar, es vulnerable
- **Fix**: detectar "On Ground" en STATUS_BAR → mandar `s` para pararse antes de cualquier otra acción

### Agente: detectar waterskin vacío
- El agente elige waterskin para beber pero puede estar vacío ("You lick the porcupine leather waterskin")
- **Fix**: si la pantalla dice "lick" después de seleccionar → marcar item como vacío y no volver a elegirlo

### Agente: navegación de conversación con NPCs
- El código para seleccionar NPCs del menú "Who will you talk to?" está implementado (`_encontrar_npc_en_menu`)
- Pero falta: navegar los temas de conversación después de seleccionar un NPC
- **Pendiente probar**: que el agente seleccione un NPC real cuando hay compañeros cerca (d<=2)

### Agente: detectar hostiles (`!`) y priorizar alejarse
- Los `!` en pantalla son criaturas, posiblemente hostiles
- El agente no los detecta — DFHack muestra NEARBY con CRUNDLEs etc. pero no dice si son hostiles
- **Fix**: si NEARBY tiene criaturas no-humanas a d<5, priorizar movimiento de escape

### Agente: fast travel desactivado
- `viajar` (Shift+T) está desactivado porque DF se cuelga durante fast travel con deshidratación
- El agente no sabe navegar el mapa de viaje
- **Para reactivar**: implementar detección de modo travel y navegación del mapa

### Autosave: no funciona en Adventure Mode
- `AUTOSAVE:SEASONAL` en d_init.txt es solo para Fortress Mode
- No existe quicksave para Adventure Mode en DFHack 0.47
- El save manual (Retire) cierra la partida
- **Estado actual**: save manual antes de cada rebuild/cambio mayor

### Rate limits de OpenAI según tier
- Tier actual limita a 200k TPM para gpt-5.4-mini (y 30k para gpt-4o)
- Se puso cap de 120k via `MAX_PROMPT_TOKENS` en llm.py
- **Si se sube de tier**: ajustar `MAX_PROMPT_TOKENS` en .env

### Twitter/X: crear cuenta y API keys
- El código del distribuidor ya soporta Twitter (`publicar_twitter`)
- Falta crear cuenta dedicada (@CaminoALaRuina o similar)
- Falta generar API keys en developer.x.com
- Solo necesita agregar 4 variables al .env del VPS

## Resuelto

### Narrador repetía el mismo episodio cada día (2026-03-25)
- Causa: no había tracking de logs procesados + LLM copiaba de la maleta
- Fix: `.ultimo_log_procesado`, `.ultimo_episodio_hash`, `resumir_maleta()`, temperature 0.9

### Context window overflow en logs grandes (2026-03-25)
- Causa: budget no restaba maleta/biblia/diario + estimación len/3 muy optimista
- Fix: restar overhead real, estimación len/2.5, auto-retry con budget reducido, cap 120k

### dia_vida y dia_mundo no se incrementaban (2026-03-26)
- Causa: el LLM no incrementaba los contadores
- Fix: incremento forzado en código Python después de cada episodio

### LLM generaba listas disfrazadas de párrafo (2026-03-26)
- Causa: "Nombre hacía X. Nombre hacía Y. Nombre hacía Z."
- Fix: instrucción explícita en prompt + ejemplo MAL/BIEN

### Gonzalo preguntaba como encuestador (2026-03-26)
- Causa: diálogos tipo "dijo/pregunté/no respondió" en loop
- Fix: prompt estilo Callahan — observar, no interrogar

### maleta_update se pegaba al episodio (2026-03-28)
- Causa: "Se guardó la hoja..." era metadata colada en la crónica
- Fix: no escribir maleta_update en la maleta, solo el episodio

### Agente comía en loop hasta nausea (2026-03-28)
- Causa: LLM elegía comer_beber en cada tick, ignorando "really full"/"Nauseous"
- Fix: sacar comer/dormir del LLM, manejar en código con cooldown de 30 ticks

### Stream switch on/off (2026-03-25)
- Fix: `stream_control.sh start|stop|status` con archivo señal + watchdog

### Stream overlay con ubicación (2026-03-25)
- Fix: `stream_overlay.py` daemon + ffmpeg drawtext con reload=1
