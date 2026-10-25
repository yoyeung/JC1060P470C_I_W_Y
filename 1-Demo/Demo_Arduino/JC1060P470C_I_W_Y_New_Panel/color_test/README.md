# Colour / display test (new panel, JD9165 1024x600)

Auto-runs a standard display test sequence in a loop, backlight at 50%, 3 s per pattern
(`BACKLIGHT_PERCENT` / `PATTERN_MS` in `color_test.ino`):

full white, black, R, G, B, C, M, Y, grey 25/50/75% → colour bars 75% / 100% →
16-step grey scale → RGBW ramps → 8x8 and 1-px checkerboards → crosshatch → 1-px border → centre window

The panel is driven in RGB565, so ramps show 32 (R/B) or 64 (G) levels.

## Build in Docker and flash

```bash
./run.sh            # docker build + compile, flash with host esptool, open serial monitor
./run.sh build      # compile only → build/color_test.ino.merged.bin
```

Board settings (in `Dockerfile`): ESP32-P4, ChipVariant `prev3` (chip rev v1.x), QIO 80 MHz, 16 MB flash,
3MB APP/9.9MB FATFS, PSRAM enabled. Use `--build-arg CHIP_VARIANT=postv3` for v3.x silicon.

Docker Desktop on macOS can't pass USB into containers, so flashing runs on the host (`pip install esptool`).
The pattern log is on UART0 at 115200; set `LOG_PORT` if that's a different port from the flashing one.
