"""
ST7735 / ST7735S 128x160 1.8" SPI TFT Display Driver for Milk-V Duo (CV1800B)
Supports 128x160 (Portrait) and 160x128 (Landscape) with 4KB SPI buffer chunking.
"""
from __future__ import annotations
import os
from time import sleep
from array import array
from PIL import Image

try:
    from spidev import SpiDev
except ImportError:
    SpiDev = None

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from xmrsigner.hardware import milkv_gpio as GPIO


class ST7735(object):
    """Driver for 1.8 inch 128x160 SPI TFT (ST7735/ST7735S) with Milk-V Duo support."""

    # ST7735 Commands
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

    def __init__(self, width=128, height=160, orientation=0, spi_bus=0, spi_device=0):
        self.width = width
        self.height = height
        self.orientation = orientation  # 0: Portrait (128x160), 1: Landscape (160x128)

        if self.orientation == 1:
            self.width, self.height = 160, 128

        # Standard Milk-V Duo Pins for 1.8" TFT:
        # DC: GP4 (GPIO 448), RST: GP3 (GPIO 511), BL: GP2 (GPIO 510)
        self._dc = 22
        self._rst = 13
        self._bl = 18

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(self._dc, GPIO.OUT)
        GPIO.setup(self._rst, GPIO.OUT)
        GPIO.setup(self._bl, GPIO.OUT)
        GPIO.output(self._bl, GPIO.HIGH)

        self._spi = None
        if SpiDev is not None:
            for bus, dev in [(spi_bus, spi_device), (0, 0), (2, 0), (1, 0)]:
                spidev_path = f"/dev/spidev{bus}.{dev}"
                if os.path.exists(spidev_path):
                    try:
                        self._spi = SpiDev(bus, dev)
                        self._spi.max_speed_hz = 24000000
                        break
                    except Exception:
                        pass

        self.init()

    def command(self, cmd):
        GPIO.output(self._dc, GPIO.LOW)
        if self._spi:
            try:
                self._spi.writebytes([cmd])
            except Exception:
                pass

    def data(self, val):
        GPIO.output(self._dc, GPIO.HIGH)
        if self._spi:
            try:
                if isinstance(val, (list, bytes, bytearray)):
                    self._spi_write_chunked(val)
                else:
                    self._spi.writebytes([val])
            except Exception:
                pass

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
        sleep(0.01)
        GPIO.output(self._rst, GPIO.LOW)
        sleep(0.02)
        GPIO.output(self._rst, GPIO.HIGH)
        sleep(0.05)

    def init(self):
        self.reset()

        # Software Reset
        self.command(self.SWRESET)
        sleep(0.12)

        # Out of Sleep
        self.command(self.SLPOUT)
        sleep(0.12)

        # Frame Rate Control
        self.command(self.FRMCTR1)
        self.data([0x01, 0x2C, 0x2D])
        self.command(self.FRMCTR2)
        self.data([0x01, 0x2C, 0x2D])
        self.command(self.FRMCTR3)
        self.data([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])

        # Display Inversion Control
        self.command(self.INVCTR)
        self.data(0x07)

        # Power Control
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

        # VCOM Control
        self.command(self.VMCTR1)
        self.data(0x0E)

        # Color Format (16-bit RGB 5-6-5)
        self.command(self.COLMOD)
        self.data(0x05)

        # Memory Access Control (Orientation / RGB Order)
        self.command(self.MADCTL)
        if self.orientation == 1:
            self.data(0xA8)  # Landscape RGB
        else:
            self.data(0xC8)  # Portrait RGB

        # Gamma Correction
        self.command(self.GMCTRP1)
        self.data([
            0x02, 0x1C, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2D,
            0x29, 0x25, 0x2B, 0x39, 0x00, 0x01, 0x03, 0x10
        ])
        self.command(self.GMCTRN1)
        self.data([
            0x03, 0x1D, 0x07, 0x06, 0x2E, 0x2C, 0x29, 0x2D,
            0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00, 0x02, 0x10
        ])

        # Display On
        self.command(self.DISPON)
        sleep(0.05)

    def SetWindows(self, x_start, y_start, x_end, y_end):
        # Column address set
        self.command(self.CASET)
        self.data([0x00, x_start & 0xFF, 0x00, (x_end - 1) & 0xFF])

        # Row address set
        self.command(self.RASET)
        self.data([0x00, y_start & 0xFF, 0x00, (y_end - 1) & 0xFF])

        # Write to RAM
        self.command(self.RAMWR)

    def ShowImage(self, image: Image.Image, x_start=0, y_start=0):
        # If incoming image doesn't match 128x160, auto resize with antialiasing
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.BILINEAR)

        arr = array("H", image.convert("BGR;16").tobytes())
        arr.byteswap()
        pix = arr.tobytes()

        self.SetWindows(0, 0, self.width, self.height)
        GPIO.output(self._dc, GPIO.HIGH)
        self._spi_write_chunked(pix)

    def clear(self):
        _buffer = bytes([0x00] * (self.width * self.height * 2))
        self.SetWindows(0, 0, self.width, self.height)
        GPIO.output(self._dc, GPIO.HIGH)
        self._spi_write_chunked(_buffer)
