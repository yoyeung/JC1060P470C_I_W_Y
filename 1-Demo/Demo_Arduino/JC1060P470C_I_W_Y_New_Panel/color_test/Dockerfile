FROM debian:bookworm-slim

ARG ARDUINO_CLI_VERSION=1.5.1
ARG ESP32_CORE_VERSION=3.3.12

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl python3 python3-pip python3-venv git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
        | BINDIR=/usr/local/bin sh -s ${ARDUINO_CLI_VERSION}

ENV ARDUINO_BOARD_MANAGER_ADDITIONAL_URLS=https://espressif.github.io/arduino-esp32/package_esp32_index.json
RUN arduino-cli core update-index \
    && arduino-cli core install esp32:esp32@${ESP32_CORE_VERSION}

RUN python3 -m venv /opt/esptool && /opt/esptool/bin/pip install --no-cache-dir esptool pyserial
ENV PATH=/opt/esptool/bin:$PATH

# Board settings from the vendor's 配置.png: 360MHz, QIO 80MHz, 16MB flash, 3MB APP/9.9MB FATFS, PSRAM on
# prev3 = ESP32-P4 silicon before v3.00 (this board reports v1.3)
ARG CHIP_VARIANT=prev3
ENV FQBN=esp32:esp32:esp32p4:ChipVariant=${CHIP_VARIANT},FlashMode=qio,FlashFreq=80,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=enabled

# Mount the sketch at /work/color_test (folder name must match the .ino)
WORKDIR /work/color_test
CMD ["sh", "-c", "arduino-cli compile --fqbn \"$FQBN\" --output-dir build ."]
