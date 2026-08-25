# Repository Knowledge

## Display Pipeline (ST7735 / ST7789)
- Never use `image.convert("BGR;16")` / `"RGB;16"` — not valid Pillow modes on any version. Use `xmrsigner.hardware.rgb565.to_rgb565_be(image, bgr=...)` (numpy fast path + pure-python fallback).
- `DISPLAY_TYPE` env var selects the driver: `ST7735` (128x160, default) or `ST7789` (240x240). It is read in two places that must stay in agreement: `gui/renderer.py` (canvas/driver) and `gui/theme.py` (font/padding scaling).
- ST7735 renders at native 128x160 — no 240x240 virtual canvas + downscale (that distorted the aspect ratio).
- CV1800B SPI FIFO limit: framebuffer writes must be chunked to <= 4096 bytes (`_spi_write_chunked`); a full 128x160 RGB565 frame is 40960 bytes = 10 chunks.

## Theme Scaling
- `gui/theme.py::_apply_display_scale()` runs at import time for ST7735 and scales the 240px-reference theme (fonts/icons/padding) by 128/240. It must run at import time because `gui/components.py` binds `Theme.*`/`Padding.*` as dataclass defaults at import.
- `TextArea` auto-shrinks font (down to 9px) when unbreakable text doesn't fit; raises `TextDoesNotFitException` below the floor.

## Known Pre-existing Test Failures (not regressions)
- `tests/test_seedqr.py`, `tests/test_decodepsbtqr.py`: stale upstream SeedSigner tests (import `QR` class that was renamed `Qr`, missing module path).
- `tests/test_controller.py::test_missing_settings_get_defaults` and `tests/test_seed.py::test_seed` fail on clean tree too.
- Tests need `pip install -e .` or `PYTHONPATH=src` plus `mock` (`tests/requirements.txt`).

## Headless Testing
- `tests/test_display_18tft.py` (14 tests) uses a fake spidev + milkv_gpio fallback to verify init sequence, 4KB chunking, RGB565 encoding, XPT2046 mapping, renderer canvas, theme scaling, and keyboard layout.
- Headless UI rendering requires stubs for `pyzbar` (package with `pyzbar` submodule exposing `ZBarSymbol` + `decode`) and `urtypes` (`RegistryType`, `Bytes`).
- `tools/test_18tft_touch.py` is interactive; headless smoke test = run under `timeout`, expect init + color bars + touch loop until killed.
