"""
RGB -> RGB565/BGR565 big-endian wire encoder for SPI TFT displays (ST7735/ST7789).

Pillow's Image.convert() does not support rawmodes like "BGR;16" (it raises
"image has wrong mode"), so framebuffers must be packed explicitly.
"""
from __future__ import annotations
import sys
from array import array
from PIL import Image

_HI_LUT = [(v & 0xF8) << 8 for v in range(256)]
_MID_LUT = [(v & 0xFC) << 3 for v in range(256)]
_LO_LUT = [v >> 3 for v in range(256)]

_LITTLE_ENDIAN = sys.byteorder == "little"


def to_rgb565_be(image: Image.Image, bgr: bool = False) -> bytes:
    """Pack an image into big-endian 16-bit 565 wire format.

    bgr=True puts the blue channel in the high bits (for panels initialized
    with the MADCTL BGR bit set, e.g. ST7735R black-tab 1.8" TFTs).
    """
    if image.mode != "RGB":
        image = image.convert("RGB")
    try:
        import numpy as np
    except ImportError:
        np = None

    if np is not None:
        px = np.asarray(image, dtype=np.uint16)
        hi = px[..., 2] if bgr else px[..., 0]
        lo = px[..., 0] if bgr else px[..., 2]
        packed = ((hi & 0xF8) << 8) | ((px[..., 1] & 0xFC) << 3) | (lo >> 3)
        if _LITTLE_ENDIAN:
            packed = packed.byteswap()
        return packed.tobytes()

    data = image.tobytes()
    hi_off, lo_off = (2, 0) if bgr else (0, 2)
    words = array("H", (
        _HI_LUT[data[i + hi_off]] | _MID_LUT[data[i + 1]] | _LO_LUT[data[i + lo_off]]
        for i in range(0, len(data), 3)
    ))
    if _LITTLE_ENDIAN:
        words.byteswap()
    return words.tobytes()
