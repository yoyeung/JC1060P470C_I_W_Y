# Flashing firmware (command line, replaces Flash Download Tool)

```bash
./flash.sh                                                  # pick from a menu
./flash.sh "Burn files/JC1060P470C_I_W_Y-V3.7_New_Panel.bin"
./flash.sh --erase -y "Burn files/....bin"                  # full erase first, no prompt
PORT=/dev/ttyACM0 ./flash.sh ...                            # choose the port
```

Same as the vendor tool settings: whole image written at `0x0`, bin header unchanged (DoNotChgBin), hash verified.
Use the USB port marked for burning and a supply of at least 600 mA. Press RST afterwards if the screen stays blank.

**Safety check:** before writing, the script reads the board's chip and revision and compares them with the
image's bootloader header, and refuses a mismatch (`--force` overrides).

| Image | Chip | Chip revision |
|---|---|---|
| `JC1060P470C_I_W_Y-V3.7_New_Panel.bin` | ESP32-P4 | v1.x (new panel) |
| `JC1060P470C_I_W_Y-V2.7.bin` | ESP32-P4 | v1.x (old panel) |
| `JC1060P470C_I_W_Y_xiaozhi2.0.4.bin` | ESP32-P4 | v0.1–v1.x |
| `JC1060P470C_I_W_V3.8(P4V3x).bin` | ESP32-P4 | **v3.1+ only** |
| `JC-C6-slave_v2.3.2.bin` | ESP32-C6 | Wi-Fi co-processor, not the P4 |

## Docker

- **Linux:** `flash.sh` builds the `jc1060-flash` image (Python + esptool) and runs it with `--device <port>`.
- **macOS / Windows:** Docker Desktop can't access USB serial ports, so `flash.sh` runs `flash.py` on the host
  (installs esptool into `./.venv` if needed). Set `NO_DOCKER=1` to skip Docker on Linux too.
