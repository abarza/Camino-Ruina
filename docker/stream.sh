#!/usr/bin/env bash
# Stream de la terminal de DF a YouTube Live via RTMP.
# Usa Xvfb + xterm + ffmpeg. No interfiere con DF (que corre en tmux text mode).
set -euo pipefail

STREAM_DISPLAY="${STREAM_DISPLAY:-:1}"
STREAM_RES="${STREAM_RES:-1280x720}"
STREAM_FPS="${STREAM_FPS:-15}"
STREAM_BITRATE="${STREAM_BITRATE:-1500k}"
STREAM_URL="${STREAM_URL:-rtmp://a.rtmp.youtube.com/live2}"
STREAM_KEY="${STREAM_KEY:-}"
TMUX_SESSION="${TMUX_SESSION:-df}"
STREAM_FONT="${STREAM_FONT:-Fira Code}"
STREAM_FONT_SIZE="${STREAM_FONT_SIZE:-18}"

if [ -z "${STREAM_KEY}" ]; then
  echo "[stream] STREAM_KEY no configurada. Abortando."
  exit 1
fi

# Levantar Xvfb en display secundario (solo para renderizar el stream).
if ! pgrep -f "Xvfb ${STREAM_DISPLAY}" >/dev/null 2>&1; then
  Xvfb "${STREAM_DISPLAY}" -screen 0 "${STREAM_RES}x24" >/var/log/xvfb_stream.log 2>&1 &
  sleep 1
  echo "[stream] Xvfb en ${STREAM_DISPLAY} (${STREAM_RES})"
fi

# Lanzar xterm conectado a la sesión tmux de DF.
if ! pgrep -f "xterm.*${STREAM_DISPLAY}" >/dev/null 2>&1; then
  DISPLAY="${STREAM_DISPLAY}" xterm \
    -fa "${STREAM_FONT}" -fs "${STREAM_FONT_SIZE}" \
    -bg black -fg white \
    -fullscreen \
    -e tmux attach -t "${TMUX_SESSION}" \
    >/var/log/xterm_stream.log 2>&1 &
  sleep 2
  echo "[stream] xterm conectado a tmux:${TMUX_SESSION}"
fi

# ffmpeg: capturar display y empujar a RTMP.
echo "[stream] Iniciando ffmpeg → ${STREAM_URL}"
ffmpeg \
  -f x11grab -video_size "${STREAM_RES}" -framerate "${STREAM_FPS}" \
  -i "${STREAM_DISPLAY}" \
  -f lavfi -i anullsrc=r=44100:cl=stereo \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -b:v "${STREAM_BITRATE}" -maxrate "${STREAM_BITRATE}" -bufsize "$((${STREAM_BITRATE%k} * 2))k" \
  -pix_fmt yuv420p \
  -g $((STREAM_FPS * 2)) \
  -c:a aac -b:a 128k \
  -f flv "${STREAM_URL}/${STREAM_KEY}" \
  >> /var/log/stream.log 2>&1
