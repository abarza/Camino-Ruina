## Inbox (futuro bot)

Este directorio es el punto de entrada para mensajes externos (Twitch/Telegram, etc.).

Propuesta v0 (sin implementar bot todavía):

- `mundo/inbox/pendientes/` — mensajes entrantes (uno por archivo).
- `mundo/inbox/procesados/` — archivados.

El bot (cuando exista) escribe aquí. El sistema (cuando decida) puede leerlos y, si corresponde,
pasarlos al narrador o a una cola interna.

