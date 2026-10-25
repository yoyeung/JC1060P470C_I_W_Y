# JC1060P470C_I_W_Y – Old panel vs New panel (Arduino demos)

The board ships with one of two LCD panels. Both use the **JD9165** controller (1024×600, MIPI-DSI, 2 lanes),
but they need **different LCD driver settings**. The application code is identical.

Compared with `Wifi_scan` (old vs new); the same driver files are shared by every demo in each folder
(`Wifi_scan`, `lvgl_demo_v8`, `lvgl_v9_sw_rotation`).

## Which files differ

| File | Same? |
|---|---|
| `Wifi_scan.ino`, `pins_config.h`, `lv_conf.h`, `weiruanyahei_14.c` | ✅ identical |
| `src/touch/*` (GT911) | ✅ identical |
| `src/lcd/jd9165_lcd.cpp/.h` | ✅ identical |
| `src/lcd/esp_lcd_jd9165.h` | ❌ video timing |
| `src/lcd/esp_lcd_jd9165.c` | ❌ init command table |

## 1. Video timing – `esp_lcd_jd9165.h` (`JD9165_1024_600_PANEL_60HZ_DPI_CONFIG`)

| Parameter | Old panel | New panel |
|---|---|---|
| `hsync_pulse_width` | 20 | **24** |
| `hsync_back_porch` | 160 | **136** |
| `hsync_front_porch` | 160 | 160 |
| `vsync_pulse_width` | 10 | **2** |
| `vsync_back_porch` | 23 | **21** |
| `vsync_front_porch` | 12 | 12 |
| Total frame (H × V) | 1364 × 645 | 1344 × 635 |
| Refresh @ 52 MHz pixel clock | ≈ 59.1 Hz | ≈ 60.9 Hz |

Unchanged: 1024×600 resolution, `dpi_clock_freq_mhz = 52`, `lane_bit_rate_mbps = 750`, RGB565.

## 2. Panel init sequence – `esp_lcd_jd9165.c` (`vendor_specific_init_default[]`)

The JD9165 registers are paged (`0x30` = page select). Vendor-tuned per panel:

| Page | Purpose | Change (old → new) |
|---|---|---|
| 0x01 | Power / voltages | `0x05` 00→**08**, `0x23` 00→**38**, `0x29` 04→**29**, `0x2B` 04→**29**; removed `0x06`, `0x17`, `0x25` |
| 0x02 | GIP / panel timing | **Largest change.** All mapping tables `0x0B`–`0x12` rewritten; `0x14` `00 00 11 11`→`00 00 41 41`; `0x18` 99→**85**; added `0x00, 0x02, 0x06–0x09, 0x13, 0x15, 0x17, 0x19–0x1B, 0x26, 0x27` |
| 0x06 | Gamma | New positive/negative gamma curves (`0x12`, `0x13`); new panel uses slightly different +/- curves |
| 0x0A | – | Removed `0x12 = 3E`, `0x13 = 78` |
| 0x0D | – | `0x10` 0C→**05**, `0x12` 0C→**05** |
| 0x00 | Standard | Unchanged: `0x3A=0x55` (RGB565), `0x11` sleep out (120 ms), `0x29` display on (20 ms) |

The old file also had commented-out page 0x07/0x08 commands that were dropped.

## Impact

- The drivers are **not interchangeable**: the old init on the new panel (or vice versa) will most likely give a
  blank or corrupted image.
- **Porting an old-panel demo to the new panel:** replace `src/lcd/esp_lcd_jd9165.c` and `src/lcd/esp_lcd_jd9165.h`
  with the versions from `JC1060P470C_I_W_Y_New_Panel/`. No sketch changes are needed.
- `JC1060P470C_I_W_Y_New_Panel/color_test` was built this way and verified on a new-panel board
  (ESP32-P4 rev v1.3).

## Reproduce the comparison

```bash
diff -ru JC1060P470C_I_W_Y_Old_Panel/Wifi_scan JC1060P470C_I_W_Y_New_Panel/Wifi_scan
```
