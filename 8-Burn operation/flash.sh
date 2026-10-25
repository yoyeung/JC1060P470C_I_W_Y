#!/usr/bin/env bash
# Flash a firmware image from "Burn files/" (see flash.py for options).
#   ./flash.sh                       menu
#   ./flash.sh "Burn files/X.bin"    direct
#   ./flash.sh --erase -y "Burn files/X.bin"
#
# Linux:  runs in Docker, passing the serial port through with --device.
# macOS:  Docker Desktop cannot access USB serial devices, so it runs on the host
#         (esptool is installed into ./.venv on first use).
set -euo pipefail
cd "$(dirname "$0")"

find_port() {
  ls /dev/ttyACM* /dev/ttyUSB* /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* 2>/dev/null | head -1
}

if [ "$(uname)" = Linux ] && command -v docker >/dev/null && [ "${NO_DOCKER:-}" != 1 ]; then
  PORT=${PORT:-$(find_port)}
  [ -n "$PORT" ] || { echo "No board found; set PORT=/dev/ttyACM0"; exit 1; }
  docker build -q -t jc1060-flash . >/dev/null
  exec docker run --rm -it --device "$PORT" -e PORT="$PORT" \
    -v "$PWD/Burn files":"/burn/Burn files":ro jc1060-flash "$@"
fi

PY=python3
if ! $PY -c "import esptool" 2>/dev/null; then
  [ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q esptool pyserial; }
  PY=.venv/bin/python
fi
exec $PY flash.py "$@"
