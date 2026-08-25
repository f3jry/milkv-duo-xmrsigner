"""
ST7735S / ST7735R 1.8" 128x160 SPI TFT Display Driver
Specifically tailored for '128x160 1.8TFT SPI V1.1' (L07-1.8TFT-ChuMo / H1376 11-10)
Supports offset compensation (Red/Black/Green Tab), RGB/BGR color selection,
and Milk-V Duo (CV1800B) 4KB SPI buffer chunking.
"""
from __future__ import annotations
import os
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
    Driver for 1.8" 128x160 SPI TFT with ST7735S / ST7735R Chip-On-Glass (COG) controller.
    Header Pins:
      [SD_CS, SD_MOSI, SD_MISO, SD_SCK, T_IRQ, T_DO, T_DIN, T_CS, T_CLK, VCC, GND, CS, RESET, A0, SDA, SCK, LED]
    """

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

    def __init__(
        self,
        width: int = 128,
        height: int = 160,
        orientation: int = 0,     # 0: Portrait (128x160), 1: Landscape (160x128)
        tab_type: str = "black",   # "black", "red", "green" (handles pixel offsets)
        bgr: bool = True,
        invert: bool = False,
        dc_pin: int = 22,         # Milk-V Duo GP4 (sysfs GPIO 448)
        rst_pin: int = 13,        # Milk-V Duo GP3 (sysfs GPIO 511)
        bl_pin: int = 18,         # Milk-V Duo GP2 (sysfs GPIO 510)
        cs_pin: int = 24,         # Milk-V Duo GP5 (SPI2_CS / sysfs GPIO 431)
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

        # Calculate pixel offset based on panel tab type
        if tab_type == "green":
            self.col_offset = 2 if self.orientation == 0 else 1
            self.row_offset = 1 if self.orientation == 0 else 2
        elif tab_type == "red":
            self.col_offset = 0
            self.row_offset = 0
        else:  # "black" (standard 1.8" 128x160)
            self.col_offset = 0
            self.row_offset = 0

        if self.orientation == 1:
            self.width, self.height = 160, 128

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(self._dc, GPIO.OUT)
        GPIO.setup(self._rst, GPIO.OUT)
        GPIO.setup(self._bl, GPIO.OUT)
        GPIO.setup(self._cs, GPIO.OUT, initial=GPIO.HIGH)
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

    def command(self, cmd: int):
        GPIO.output(self._dc, GPIO.LOW)
        GPIO.output(self._cs, GPIO.LOW)
        if self._spi:
            try:
                self._spi.writebytes([cmd])
            except Exception:
                pass
        GPIO.output(self._cs, GPIO.HIGH)

    def data(self, val):
        GPIO.output(self._dc, GPIO.HIGH)
        GPIO.output(self._cs, GPIO.LOW)
        if self._spi:
            try:
                if isinstance(val, (list, bytes, bytearray)):
                    self._spi_write_chunked(val)
                else:
                    self._spi.writebytes([val])
            except Exception:
                pass
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

        # Frame Rate Control (normal & idle modes)
        self.command(self.FRMCTR1)
        self.data([0x01, 0x2C, 0x2D])
        self.command(self.FRMCTR2)
        self.data([0x01, 0x2C, 0x2D])
        self.command(self.FRMCTR3)
        self.data([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])

        # Display Inversion Control
        self.command(self.INVCTR)
        self.data(0x07)

        # Power Control 1-5
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

        # Inversion mode
        if self.invert:
            self.command(self.INVON)
        else:
            self.command(self.INVOFF)

        # Color Format (16-bit RGB 5-6-5)
        self.command(self.COLMOD)
        self.data(0x05)

        # Memory Access Control (Orientation & BGR/RGB)
        self.command(self.MADCTL)
        bgr_bit = 0x08 if self.bgr else 0x00
        if self.orientation == 1:
            self.data(0xA0 | bgr_bit)  # Landscape
        else:
            self.data(0xC0 | bgr_bit)  # Portrait (top-to-bottom, left-to-right)

        # Gamma Correction (+ / -)
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

    def SetWindows(self, x_start: int, y_start: int, x_end: int, y_end: int):
        x0 = x_start + self.col_offset
        x1 = (x_end - 1) + self.col_offset
        y0 = y_start + self.row_offset
        y1 = (y_end - 1) + self.row_offset

        # Column address set (CASET)
        self.command(self.CASET)
        self.data([0x00, x0 & 0xFF, 0x00, x1 & 0xFF])

        # Row address set (RASET)
        self.command(self.RASET)
        self.data([0x00, y0 & 0xFF, 0x00, y1 & 0xFF])

        # RAM Write (RAMWR)
        self.command(self.RAMWR)

    def ShowImage(self, image: Image.Image, x_start: int = 0, y_start: int = 0):
        if image.size != (self.width, self.height):
            resample = getattr(Image, "Resampling", Image).BILINEAR
            image = image.resize((self.width, self.height), resample)

        pix = to_rgb565_be(image, bgr=self.bgr)

        self.SetWindows(0, 0, self.width, self.height)
        GPIO.output(self._dc, GPIO.HIGH)
        GPIO.output(self._cs, GPIO.LOW)
        self._spi_write_chunked(pix)
        GPIO.output(self._cs, GPIO.HIGH)

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)):
        img = Image.new('RGB', (self.width, self.height), color)
        self.ShowImage(img)
