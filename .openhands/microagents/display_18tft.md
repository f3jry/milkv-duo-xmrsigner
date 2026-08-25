---
name: display_18tft_chumo
type: task
version: 1.1.0
agent: CodeActAgent
triggers:
  - 1.8tft
  - 128x160
  - chumo
  - l07
  - h1376
  - st7735
  - xpt2046
  - touch
  - spi_v1.1
---

# L07-1.8TFT-ChuMo (128x160 1.8TFT SPI V1.1) Specification & Guidelines

## 1. Hardware Architecture & Identification
- **Module Name:** `128x160 1.8TFT SPI V1.1` / `L07-1.8TFT-ChuMo`
- **Display Glass Stamp:** `H1376 11-10`
- **Display Driver IC:** **ST7735S / ST7735R** (COG / Chip-on-Glass, integrated under ribbon).
- **Touch Controller IC:** **XPT2046 / ADS7843** (16-pin SOIC on back of PCB).
- **Resolution:** 128 (width) x 160 (height) pixels (or 160x128 landscape).
- **Color Depth:** 16-bit RGB565 / BGR565.

## 2. 17-Pin Header Mapping (Milk-V Duo CV1800B)
| Pin # | Header Label | Function | Milk-V Duo Physical Pin | Signal / GPIO |
|---|---|---|---|---|
| 1 | `SD_CS` | MicroSD SPI Chip Select | Pin 16 | GP11 |
| 2 | `SD_MOSI` | MicroSD SPI Data In | Pin 19 (shared) | GP6 (`SPI2_SDO`) |
| 3 | `SD_MISO` | MicroSD SPI Data Out | Pin 21 (shared) | GP8 (`SPI2_SDI`) |
| 4 | `SD_SCK` | MicroSD SPI Clock | Pin 23 (shared) | GP7 (`SPI2_SCK`) |
| 5 | `T_IRQ` | Touch Pen Interrupt (Active LOW)| Pin 27 | GP17 (Sysfs 429) |
| 6 | `T_DO` | Touch SPI Data Out (MISO) | Pin 21 (shared) | GP8 (`SPI2_SDI`) |
| 7 | `T_DIN` | Touch SPI Data In (MOSI) | Pin 19 (shared) | GP6 (`SPI2_SDO`) |
| 8 | `T_CS` | Touch SPI Chip Select | Pin 26 | GP18 (Sysfs 430) |
| 9 | `T_CLK` | Touch SPI Clock (SCK) | Pin 23 (shared) | GP7 (`SPI2_SCK`) |
| 10 | `VCC` | Power (3.3V) | Pin 36 | 3.3V (OUT) |
| 11 | `GND` | Ground | Pin 38 | GND |
| 12 | `CS` | TFT Display Chip Select | Pin 24 | GP5 (`SPI2_CS`) |
| 13 | `RESET` | TFT Display Hardware Reset | Pin 13 | GP3 (Sysfs 511) |
| 14 | `A0` / `DC` | Data / Command Select | Pin 22 | GP4 (Sysfs 448) |
| 15 | `SDA` / `MOSI`| TFT Display Data In | Pin 19 (shared) | GP6 (`SPI2_SDO`) |
| 16 | `SCK` | TFT Display Clock | Pin 23 (shared) | GP7 (`SPI2_SCK`) |
| 17 | `LED` / `BLK` | Backlight Anode (3.3V) | Pin 18 | GP2 (Sysfs 510) |

## 3. Driver & Tooling Reference
- **Display Driver:** `src/xmrsigner/hardware/ST7735.py`
  - Supports 4KB chunking (`_spi_write_chunked()`) for CV1800B FIFO limits.
  - Supports `offset_x`, `offset_y`, `bgr`, and `tab_type` calibration.
- **Touch Driver:** `src/xmrsigner/hardware/xpt2046.py`
  - Reads 12-bit ADC coordinates from XPT2046 via SPI.
  - Automatically maps touch coordinates to virtual buttons (`KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`, `KEY_PRESS`, `KEY1`, `KEY2`, `KEY3`).
- **Interactive Diagnostic Tool:** `tools/test_18tft_touch.py`
  - Tests color pattern rendering, orientation, and real-time touch crosshair feedback.
