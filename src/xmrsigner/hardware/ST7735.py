"""
ST7735S / ST7735R 1.8" 128x160 SPI TFT Display Driver
Tailored for Milk-V Duo (CV1800B) with 4KB SPI buffer chunking,
hardware/software CS, and robust reset sequences.
"""
from __future__ import annotations
import os
import sys
from time import sleep
from PIL import Image

from xmrsigner.hardware.rgb565 import to_rgb565_be

try:
    from spidev import SpiDev
except ImportError:
    SpiDev = None

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from xmrsigner.hardware import milkv_gpio as GPIO


class ST7735(object):
    """
    Driver for 1.8" 128x160 SPI TFT with ST7735S / ST7735R controller.
    """
    # Commands
    SWRESET = 0x01
    SLPOUT  = 0x11
    FRMCTR1 = 0xB1
    FRMCTR2 = 0xB2
    FRMCTR3 = 0xB3
    INVCTR  = 0xB4
    PWCTR1  = 0xC0
    PWCTR2  = 0xC1
    PWCTR3  = 0xC2
    PWCTR4  = 0xC3
    PWCTR5  = 0xC4
    VMCTR1  = 0xC5
    INVOFF  = 0x20
    INVON   = 0x21
    MADCTL  = 0x36
    COLMOD  = 0x3A
    CASET   = 0x2A
    RASET   = 0x2B
    RAMWR   = 0x2C
    GMCTRP1 = 0xE0
    GMCTRN1 = 0xE1
    DISPON  = 0x29

    def __init__(
        self,
        width: int = 128,
        height: int = 160,
        orientation: int = 0,
        tab_type: str = "black",
        bgr: bool = True,
        invert: bool = False,
        dc_pin: int = 448,        # GP4 / GPIO 448 (Physical Pin 6)
        rst_pin: int = 511,       # GP3 / GPIO 511 (Physical Pin 5)
        bl_pin: int = 510,        # GP2 / GPIO 510 (Physical Pin 4)
        cs_pin: int = 431,        # GP5 / GPIO 431 (Physical Pin 7)
        spi_bus: int = 0,
        spi_device: int = 0
    ):
        self.width = width
        self.height = height
        self.orientation = orientation
        self.bgr = bgr
        self.invert = invert
        self._dc = dc_pin
        self._rst = rst_pin
        self._bl = bl_pin
        self._cs = cs_pin

        self.col_offset = 0
        self.row_offset = 0
        if tab_type == "green":
            self.col_offset = 2 if self.orientation == 0 else 1
            self.row_offset = 1 if self.orientation == 0 else 2

        if self.orientation == 1:
            self.width, self.height = 160, 128

        # GPIO setup
        GPIO.setmode(GPIO.BCM if hasattr(GPIO, 'BCM') else GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(self._dc, GPIO.OUT)
        GPIO.setup(self._rst, GPIO.OUT)
        GPIO.setup(self._bl, GPIO.OUT)
        GPIO.setup(self._cs, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(self._bl, GPIO.HIGH)

        # SPI setup
        self._spi = None
        if SpiDev is not None:
            for bus, dev in [(spi_bus, spi_device), (0, 0), (2, 0), (1, 0)]:
                spidev_path = f"/dev/spidev{bus}.{dev}"
                if os.path.exists(spidev_path):
                    try:
                        self._spi = SpiDev(bus, dev)
                        self._spi.max_speed_hz = 16000000
                        self._spi.mode = 0
                        break
                    except Exception:
                        pass

        self.init()

    def command(self, cmd: int):
        GPIO.output(self._dc, GPIO.LOW)
        GPIO.output(self._cs, GPIO.LOW)
        if self._spi:
            self._spi.writebytes([cmd])
        GPIO.output(self._cs, GPIO.HIGH)

    def data(self, val):
        GPIO.output(self._dc, GPIO.HIGH)
        GPIO.output(self._cs, GPIO.LOW)
        if self._spi:
            if isinstance(val, int):
                self._spi.writebytes([val])
            elif isinstance(val, (list, tuple, bytes, bytearray)):
                self._spi_write_chunked(val)
        GPIO.output(self._cs, GPIO.HIGH)

    def _spi_write_chunked(self, data_bytes, chunk_size=4096):
        if not self._spi:
            return
        total = len(data_bytes)
        for offset in range(0, total, chunk_size):
            chunk = data_bytes[offset:offset + chunk_size]
            try:
                if hasattr(self._spi, 'writebytes2'):
                    self._spi.writebytes2(chunk)
                else:
                    self._spi.writebytes(list(chunk))
            except Exception:
                pass

    def reset(self):
        GPIO.output(self._rst, GPIO.HIGH)
        sleep(0.02)
        GPIO.output(self._rst, GPIO.LOW)
        sleep(0.05)
        GPIO.output(self._rst, GPIO.HIGH)
        sleep(0.05)

    def init(self):
        self.reset()

        self.command(self.SWRESET)
        sleep(0.15)

        self.command(self.SLPOUT)
        sleep(0.15)

        # Frame rate control
        self.command(self.FRMCTR1)
        self.data([0x01, 0x2C, 0x2D])
        self.command(self.FRMCTR2)
        self.data([0x01, 0x2C, 0x2D])
        self.command(self.FRMCTR3)
        self.data([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])

        # Display Inversion Control
        self.command(self.INVCTR)
        self.data(0x07)

        # Power control
        self.command(self.PWCTR1)
        self.data([0xA2, 0x02, 0x84])
        self.command(self.PWCTR2)
        self.data(0xC5)
        self.command(self.PWCTR3)
        self.data([0x0A, 0x00])
        self.command(self.PWCTR4)
        self.data([0x8A, 0x2A])
        self.command(self.PWCTR5)
        self.data([0x8A, 0xEE])

        # VCOM control
        self.command(self.VMCTR1)
        self.data(0x0E)

        # Inversion
        self.command(self.INVON if self.invert else self.INVOFF)

        # Color Mode: 16-bit RGB565
        self.command(self.COLMOD)
        self.data(0x05)

        # Memory Access Control (Orientation & BGR/RGB)
        self.command(self.MADCTL)
        if self.orientation == 0:
            madctl = 0x08 if self.bgr else 0x00
        elif self.orientation == 1:
            madctl = 0x68 if self.bgr else 0x60
        elif self.orientation == 2:
            madctl = 0xC8 if self.bgr else 0xC0
        else:
            madctl = 0xA8 if self.bgr else 0xA0
        self.data(madctl)

        # Gamma
        self.command(self.GMCTRP1)
        self.data([0x02, 0x1c, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2d, 0x29, 0x25, 0x2B, 0x39, 0x00, 0x01, 0x03, 0x10])
        self.command(self.GMCTRN1)
        self.data([0x03, 0x1d, 0x07, 0x06, 0x2E, 0x2C, 0x29, 0x2D, 0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00, 0x02, 0x10])

        # Display ON
        self.command(self.DISPON)
        sleep(0.1)

    def set_window(self, x0: int, y0: int, x1: int, y1: int):
        x0 += self.col_offset
        x1 += self.col_offset
        y0 += self.row_offset
        y1 += self.row_offset

        self.command(self.CASET)
        self.data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])

        self.command(self.RASET)
        self.data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])

        self.command(self.RAMWR)

    def ShowImage(self, image: Image.Image, x_start: int = 0, y_start: int = 0):
        """Streams a PIL Image in RGB565 to the display."""
        if image.mode != "RGB":
            image = image.convert("RGB")
        w, h = image.size
        self.set_window(x_start, y_start, x_start + w - 1, y_start + h - 1)
        raw_rgb565 = to_rgb565_be(image)
        self.data(raw_rgb565)

    def clear(self, color=(0, 0, 0)):
        img = Image.new("RGB", (self.width, self.height), color)
        self.ShowImage(img)
