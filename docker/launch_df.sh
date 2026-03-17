#!/usr/bin/env bash
set -euo pipefail

DF_DIR="${1:-/opt/df}"
DF_CMD="${2:-./dwarfort}"

cd "${DF_DIR}"

# Parse simple comando+args separado por espacios.
# shellcheck disable=SC2206
cmd_parts=(${DF_CMD})
cmd_bin="${cmd_parts[0]:-./dwarfort}"

if [[ "${cmd_bin}" == "./dfhack" || "${cmd_bin}" == "dfhack" ]]; then
  echo "[launch_df] DFHack compat mode: preload libdfhack.so (sin setarch)."
  export LD_PRELOAD="${LD_PRELOAD:+${LD_PRELOAD}:}./hack/libdfhack.so"
  exec ./dwarfort "${cmd_parts[@]:1}"
fi

if [[ -x "${cmd_bin}" ]]; then
  exec "${cmd_parts[@]}"
fi

echo "DF_CMD no ejecutable: ${DF_CMD}. Monta DF/DFHack en ${DF_DIR}."
exit 1
