# Deuda Técnica

## Pendiente

### Verificar que autosave de DF funciona
- Se cambió `d_init.txt` a `AUTOSAVE:SEASONAL`, `AUTOBACKUP:YES`, `INITIAL_SAVE:YES`
- Pero DF necesita cargar la partida de nuevo para que tome efecto
- **Verificar**: que `world.sav` se actualice solo (sin save manual)
- **Cómo**: revisar fecha de `/opt/df/data/save/region1/world.sav` después de un cambio de estación in-game
- **Si no funciona**: reiniciar DF dentro del container para que relea d_init.txt

### dia_vida y dia_mundo no se incrementan en el diario
- El LLM devuelve siempre `dia_vida: 1` y `dia_mundo: 1` en el DIARIO_UPDATE
- Se reforzó la instrucción en el prompt pero no fue suficiente
- **Opción A**: incrementar dia_vida/dia_mundo en código (Python) en vez de depender del LLM
- **Opción B**: validar el JSON del LLM y forzar incremento si no lo hizo

### Rate limits de OpenAI según tier
- Tier actual limita a 200k TPM para gpt-5.4-mini (y 30k para gpt-4o)
- Se puso cap de 120k via `MAX_PROMPT_TOKENS` en llm.py
- **Si se sube de tier**: ajustar `MAX_PROMPT_TOKENS` en .env para aprovechar más contexto

## Resuelto

### Narrador repetía el mismo episodio cada día (2026-03-25)
- Causa: no había tracking de logs procesados + LLM copiaba de la maleta
- Fix: `.ultimo_log_procesado`, `.ultimo_episodio_hash`, `resumir_maleta()`, temperature 0.9

### Context window overflow en logs grandes (2026-03-25)
- Causa: budget no restaba maleta/biblia/diario + estimación len/3 muy optimista
- Fix: restar overhead real, estimación len/2.5, auto-retry con budget reducido, cap 120k
