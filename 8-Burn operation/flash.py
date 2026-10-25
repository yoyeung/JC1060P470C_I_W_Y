#!/usr/bin/env python3
"""Flash a JC1060P470C firmware image (from "Burn files/") with esptool.

Same settings as the vendor's Flash Download Tool: whole image at 0x0, bin header kept as is.
Before writing, the chip type and revision of the connected board are checked against the
image's bootloader header, so e.g. a P4 v3.x image is never written to a v1.x chip.

  ./flash.py                      pick an image from a menu, auto-detect the port
  ./flash.py "Burn files/X.bin"   flash that image
  ./flash.py --erase ...          erase the whole flash first
  ./flash.py --port /dev/ttyACM0 --baud 460800 ...
"""
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(HERE, "Burn files")
CHIP_NAMES = {0: "ESP32", 2: "ESP32-S2", 5: "ESP32-C3", 9: "ESP32-S3", 12: "ESP32-C2",
              13: "ESP32-C6", 16: "ESP32-H2", 18: "ESP32-P4", 23: "ESP32-C5"}

# ANSI colours, off when output is not a terminal or NO_COLOR is set
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
BOLD, DIM, RED, GREEN, YELLOW, CYAN = "1", "2", "31", "32", "33", "36"


def c(text, *codes):
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m" if USE_COLOR and codes else str(text)


def fail(msg):
    sys.exit(c(f"✗ {msg}", RED, BOLD))


def esptool(*args, capture=False):
    if capture:
        r = subprocess.run([sys.executable, "-m", "esptool", *args], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr
    # Run in-process with a logger that keeps the progress bar on a single, updating line
    import esptool as et
    from esptool.logger import log
    log.set_logger(one_line_logger())
    try:
        et.main(list(args))
        return 0, ""
    except SystemExit as e:
        return (e.code or 0), ""
    except Exception as e:
        print(c(f"\nERROR: {e}", RED, BOLD))
        return 1, ""


def one_line_logger():
    from esptool.logger import TemplateLogger

    class OneLineLogger(TemplateLogger):
        in_bar = False

        def _end_bar(self):
            if self.in_bar:
                sys.stdout.write("\n")
                self.in_bar = False

        def print(self, *args, **kwargs):
            self._end_bar()
            print(*args, sep=kwargs.get("sep", " "), end=kwargs.get("end", "\n"), flush=True)

        def note(self, message):
            self.print(f"Note: {message}")

        def warning(self, message):
            self.print(c(f"Warning: {message}", YELLOW))

        def error(self, message):
            self.print(c(message, RED, BOLD))

        def stage(self, finish=False):
            pass

        def progress_bar(self, cur_iter, total_iters, prefix="", suffix="", bar_length=30):
            # The line must fit the terminal width: a wrapped line can't be redrawn with \r
            frac = cur_iter / total_iters if total_iters else 1
            head, tail = prefix.strip(), f"{frac * 100:5.1f}% {suffix.strip()}"
            cols = shutil.get_terminal_size((80, 24)).columns - 1
            bar_length = min(bar_length, cols - len(head) - len(tail) - 4)
            if bar_length >= 5:
                filled = int(bar_length * frac)
                bar = f" [{c('█' * filled, GREEN)}{c('░' * (bar_length - filled), DIM)}]"
            else:
                bar, head = "", head[:max(0, cols - len(tail) - 1)]
            pct, rest = tail.split("%", 1)
            sys.stdout.write(f"\r{c(head, CYAN)}{bar} {c(pct.strip() + '%', BOLD)}{rest}\x1b[K")
            sys.stdout.flush()
            self.in_bar = cur_iter < total_iters
            if not self.in_bar:
                sys.stdout.write("\n")

        def set_verbosity(self, verbosity):
            pass

    return OneLineLogger()


def image_info(path):
    """Return (chip name, min rev, max rev) from the image's bootloader header (at 0x0 or 0x2000 for P4)."""
    with open(path, "rb") as f:
        data = f.read(0x2000 + 24)
    for off in (0x0, 0x2000):
        hdr = data[off:off + 24]
        if len(hdr) == 24 and hdr[0] == 0xE9:
            chip_id, _, min_rev, max_rev = struct.unpack_from("<HBHH", hdr, 12)
            return CHIP_NAMES.get(chip_id, f"chip id {chip_id}"), min_rev, max_rev
    return None


def detect_port():
    ports = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
                   + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wchusbserial*"))
    if not ports:
        fail("No board found. Plug it into the USB port used for burning, or pass --port.")
    if len(ports) > 1:
        print(c("Several serial ports found, using the first one: " + ", ".join(ports), YELLOW))
    return ports[0]


def read_chip(port):
    print(c(f"Reading chip on {port} ...", DIM))
    rc, out = esptool("--port", port, "chip-id", capture=True)
    m = re.search(r"Chip (?:type|is):\s*(ESP32-\w+)\s*\(revision v(\d+)\.(\d+)\)", out)
    if rc != 0 or not m:
        print(out)
        fail("Could not talk to the board. Check the cable/port, or hold BOOT and press RST to enter download mode.")
    return m.group(1), int(m.group(2)) * 100 + int(m.group(3))


def problems(info, chip, chip_rev):
    if not info:
        return ["no ESP bootloader header at 0x0 or 0x2000 - not a full flash image"]
    img_chip, img_min, img_max = info
    found = []
    if chip != img_chip:
        found.append(f"image is for {img_chip}, board is {chip}")
    if not img_min <= chip_rev <= img_max:
        found.append(f"needs chip revision {rev(img_min)}-{rev(img_max)}, board is {rev(chip_rev)}")
    return found


def describe(info):
    return f"{info[0]} {rev(info[1])}-{rev(info[2])}" if info else "unknown"


def choose_bin(chip, chip_rev):
    bins = sorted(glob.glob(os.path.join(BIN_DIR, "*.bin")))
    if not bins:
        fail(f"No .bin files in {BIN_DIR}")
    print(c("\nFirmware images", BOLD) + c(f"  (✓ = fits this {chip} {rev(chip_rev)})", DIM))
    for i, b in enumerate(bins, 1):
        info = image_info(b)
        name = os.path.basename(b)
        if problems(info, chip, chip_rev):
            print(f"  {c(f'{i})', DIM)} {c('✗', RED)} {c(name, DIM)}  {c(describe(info), DIM)}")
        else:
            print(f"  {c(f'{i})', CYAN, BOLD)} {c('✓', GREEN)} {c(name, BOLD)}  {c(describe(info), DIM)}")
    choice = input(c("\nSelect image number: ", YELLOW, BOLD)).strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(bins):
        fail("Invalid choice")
    return bins[int(choice) - 1]


def rev(v):
    return f"v{v // 100}.{v % 100}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bin", nargs="?", help="image to flash (default: choose from 'Burn files/')")
    ap.add_argument("--port", default=os.environ.get("PORT"))
    ap.add_argument("--baud", default=os.environ.get("BAUD", "921600"))
    ap.add_argument("--erase", action="store_true", help="erase the whole flash before writing")
    ap.add_argument("--force", action="store_true", help="flash even if chip type/revision does not match")
    ap.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    a = ap.parse_args()

    print(c("━━ JC1060P470C firmware flasher ━━", CYAN, BOLD))
    port = a.port or detect_port()
    chip, chip_rev = read_chip(port)

    path = a.bin or choose_bin(chip, chip_rev)
    if not os.path.isfile(path):
        fail(f"File not found: {path}")
    info = image_info(path)

    print()
    print(f"  {c('board', DIM)}  {c(f'{chip} {rev(chip_rev)}', BOLD)}  {c(port, DIM)}")
    print(f"  {c('image', DIM)}  {c(os.path.basename(path), BOLD)}  {c(describe(info), DIM)}")
    found = problems(info, chip, chip_rev)
    for p in found:
        print(c(f"  ✗ MISMATCH: {p}", RED, BOLD))
    if found and not a.force:
        fail("Not flashing (use --force to override).")
    if not found:
        print(c("  ✓ chip and revision match", GREEN))

    prompt = f"\nFlash it{' (erasing all flash first)' if a.erase else ''}? [y/N] "
    if not a.yes and input(c(prompt, YELLOW, BOLD)).strip().lower() != "y":
        sys.exit(c("Cancelled", YELLOW))

    base = ["--chip", chip.lower().replace("-", ""), "--port", port, "--baud", str(a.baud)]
    if a.erase and esptool(*base, "erase-flash")[0] != 0:
        fail("Erase failed")
    if esptool(*base, "write-flash", "0x0", path)[0] != 0:
        fail("FLASH FAILED")
    print(c("\n✓ DONE - flash verified.", GREEN, BOLD) + " If the screen stays blank, press RST or power-cycle the board.")


if __name__ == "__main__":
    main()
