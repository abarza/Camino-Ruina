#!/usr/bin/env bash
# Control del stream: start | stop | status
# Usa /tmp/stream.enabled como señal para stream.sh
set -euo pipefail

SIGNAL_FILE="/tmp/stream.enabled"

case "${1:-status}" in
  start)
    touch "${SIGNAL_FILE}"
    echo "[stream] Stream habilitado. El watchdog lo levantará en segundos."
    ;;
  stop)
    rm -f "${SIGNAL_FILE}"
    # Matar ffmpeg para que el watchdog detecte y pare.
    pkill -f "ffmpeg.*flv" 2>/dev/null || true
    echo "[stream] Stream detenido."
    ;;
  status)
    if [ -f "${SIGNAL_FILE}" ]; then
      if pgrep -f "ffmpeg.*flv" >/dev/null 2>&1; then
        echo "[stream] ACTIVO — ffmpeg corriendo."
      else
        echo "[stream] HABILITADO — esperando que el watchdog arranque ffmpeg."
      fi
    else
      echo "[stream] APAGADO."
    fi
    ;;
  *)
    echo "Uso: stream_control.sh {start|stop|status}"
    exit 1
    ;;
esac
