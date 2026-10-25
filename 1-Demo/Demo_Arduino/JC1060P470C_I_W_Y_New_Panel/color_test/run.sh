#!/usr/bin/env bash
# Build the colour test in Docker, flash it from the host, then show the serial test log.
#   ./run.sh                 build + flash + monitor (port auto-detected)
#   ./run.sh build           build only
#   PORT=/dev/cu.usbmodemXXXX ./run.sh
# Docker Desktop on macOS cannot pass USB serial into containers, so flashing uses the host's esptool.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=jc1060-colortest
docker build -t "$IMAGE" .
docker run --rm -v "$PWD":/work/color_test "$IMAGE"
[ "${1:-}" = build ] && exit 0

PORT=${PORT:-$(ls /dev/cu.usbmodem* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1)}
[ -n "$PORT" ] || { echo "No board found; set PORT=..."; exit 1; }

ESPTOOL=$(command -v esptool || command -v esptool.py) || { echo "Install esptool: pip install esptool"; exit 1; }
"$ESPTOOL" --chip esp32p4 --port "$PORT" --baud 921600 write-flash 0x0 build/color_test.ino.merged.bin

# The test log is printed on UART0 (CDC On Boot is disabled), which may be a different port
# from the USB-Serial/JTAG one used for flashing: set LOG_PORT to read it.
python3 -m serial.tools.miniterm "${LOG_PORT:-$PORT}" 115200 --raw
