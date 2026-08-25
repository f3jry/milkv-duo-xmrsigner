---
name: milkv_hardware
type: task
version: 1.0.0
agent: CodeActAgent
triggers:
  - hardware
  - display
  - touch
  - gpio
  - camera
  - st7735
  - st7789
  - xpt2046
---

# Milk-V Duo Hardware Development Guidelines

## Display & SPI Buffer Chunking
The SOPHGO CV1800B SPI controller has a 4KB FIFO buffer limit. When pushing framebuffers to SPI displays:
- Always chunk SPI transfers in 4096-byte blocks (`_spi_write_chunked()`).
- Direct single-buffer transfers over 4096 bytes will cause `[Errno 90] Message too long`.

## Touch Screen Integration (XPT2046)
- XPT2046 communicates via SPI (12-bit ADC mode).
- T_IRQ is active LOW on touch.
- Filter and smooth ADC readings over 3 samples to avoid jitter.
- Map on-screen coordinates to virtual navigation keys (`KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`, `KEY_PRESS`, `KEY1`, `KEY2`, `KEY3`).

## GPIO Mapping (CV1800B Sysfs)
- Always verify pinmux via `duo-pinmux` or devmem before exporting sysfs GPIOs.
- Backlight pins: Set active HIGH (`echo 1 > /sys/class/gpio/gpio510/value`).
