from __future__ import annotations
try:
    from spidev import SpiDev
except ImportError:
    SpiDev = None

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from xmrsigner.hardware import milkv_gpio as GPIO

import os
from time import sleep
from PIL import Image

from xmrsigner.hardware.rgb565 import to_rgb565_be


class ST7789(object):
    """class for ST7789 240*240 1.3inch OLED/LCD displays on Milk-V Duo and Raspberry Pi."""

    def __init__(self, spi_bus=0, spi_device=0):
        self.width = 240
        self.height = 240

        # Standard Pins for Waveshare 1.3inch LCD HAT
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
            # Check possible SPI devices on Milk-V Duo or Pi
            for bus, dev in [(spi_bus, spi_device), (0, 0), (2, 0), (1, 0)]:
                spidev_path = f"/dev/spidev{bus}.{dev}"
                if os.path.exists(spidev_path):
                    try:
                        self._spi = SpiDev(bus, dev)
                        self._spi.max_speed_hz = 40000000
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
                self._spi.writebytes([val])
            except Exception:
                pass

    def _spi_write_chunked(self, data_bytes, chunk_size=4096):
        """Milk-V Duo CV1800B SPI FIFO requires chunked transfers to prevent buffer overflow."""
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

    def init(self):
        """Initialize display"""
        self.reset()

        self.command(0x36)
        self.data(0x70)

        self.command(0x3A)
        self.data(0x05)

        self.command(0xB2)
        self.data(0x0C)
        self.data(0x0C)
        self.data(0x00)
        self.data(0x33)
        self.data(0x33)

        self.command(0xB7)
        self.data(0x35)

        self.command(0xBB)
        self.data(0x19)

        self.command(0xC0)
        self.data(0x2C)

        self.command(0xC2)
        self.data(0x01)

        self.command(0xC3)
        self.data(0x12)

        self.command(0xC4)
        self.data(0x20)

        self.command(0xC6)
        self.data(0x0F)

        self.command(0xD0)
        self.data(0xA4)
        self.data(0xA1)

        self.command(0xE0)
        self.data(0xD0)
        self.data(0x04)
        self.data(0x0D)
        self.data(0x11)
        self.data(0x13)
        self.data(0x2B)
        self.data(0x3F)
        self.data(0x54)
        self.data(0x4C)
        self.data(0x18)
        self.data(0x0D)
        self.data(0x0B)
        self.data(0x1F)
        self.data(0x23)

        self.command(0xE1)
        self.data(0xD0)
        self.data(0x04)
        self.data(0x0C)
        self.data(0x11)
        self.data(0x13)
        self.data(0x2C)
        self.data(0x3F)
        self.data(0x44)
        self.data(0x51)
        self.data(0x2F)
        self.data(0x1F)
        self.data(0x1F)
        self.data(0x20)
        self.data(0x23)
        self.command(0x21)
        self.command(0x11)
        self.command(0x29)

    def reset(self):
        """Reset the display"""
        GPIO.output(self._rst, GPIO.HIGH)
        sleep(0.01)
        GPIO.output(self._rst, GPIO.LOW)
        sleep(0.01)
        GPIO.output(self._rst, GPIO.HIGH)
        sleep(0.01)

    def SetWindows(self, x_start, y_start, x_end, y_end):
        self.command(0x2A)
        self.data(0x00)
        self.data(x_start & 0xff)
        self.data(0x00)
        self.data((x_end - 1) & 0xff)

        self.command(0x2B)
        self.data(0x00)
        self.data(y_start & 0xff)
        self.data(0x00)
        self.data((y_end - 1) & 0xff)

        self.command(0x2C)

    def ShowImage(self, image: Image.Image, x_start=0, y_start=0):
        imwidth, imheight = image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError(f'Image must be {self.width}x{self.height}, got {imwidth}x{imheight}')
        
        pix = to_rgb565_be(image, bgr=True)
        self.SetWindows(0, 0, self.width, self.height)
        GPIO.output(self._dc, GPIO.HIGH)
        self._spi_write_chunked(pix)

    def clear(self):
        _buffer = bytes([0xff] * (self.width * self.height * 2))
        self.SetWindows(0, 0, self.width, self.height)
        GPIO.output(self._dc, GPIO.HIGH)
        self._spi_write_chunked(_buffer)
