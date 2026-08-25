"""
XPT2046 Resistive Touch Controller Driver for 1.8" TFT V1.1 Module
Converts touch screen gestures & taps to navigation button presses on Milk-V Duo.
"""
from __future__ import annotations
import os
import time
import threading

try:
    from spidev import SpiDev
except ImportError:
    SpiDev = None

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from xmrsigner.hardware import milkv_gpio as GPIO

from xmrsigner.hardware.buttons import HardwareButtonsConstants


class XPT2046:
    """XPT2046 Touch Screen driver for 1.8" TFT SPI Module."""

    CMD_X = 0xD0
    CMD_Y = 0x90
    CMD_Z1 = 0xB0
    CMD_Z2 = 0xC0

    # Calibration defaults for 1.8" 128x160 TFT
    X_MIN, X_MAX = 200, 3900
    Y_MIN, Y_MAX = 250, 3850

    def __init__(self, cs_pin=26, irq_pin=27, width=128, height=160, spi_bus=0, spi_device=1):
        self.width = width
        self.height = height
        self.cs_pin = cs_pin
        self.irq_pin = irq_pin
        self.last_touch_time = 0
        self.is_pressed = False
        self.last_x, self.last_y = 0, 0
        self._lock = threading.Lock()

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.cs_pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.irq_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self._spi = None
        if SpiDev is not None:
            for bus, dev in [(spi_bus, spi_device), (0, 1), (0, 0), (2, 0)]:
                if os.path.exists(f"/dev/spidev{bus}.{dev}"):
                    try:
                        self._spi = SpiDev(bus, dev)
                        self._spi.max_speed_hz = 2000000
                        break
                    except Exception:
                        pass

    def _read_adc(self, cmd: int) -> int:
        if not self._spi:
            return 0
        GPIO.output(self.cs_pin, GPIO.LOW)
        try:
            resp = self._spi.xfer2([cmd, 0x00, 0x00])
            val = ((resp[1] << 8) | resp[2]) >> 3
            return val & 0x0FFF
        except Exception:
            return 0
        finally:
            GPIO.output(self.cs_pin, GPIO.HIGH)

    def is_touched(self) -> bool:
        # Check IRQ pin (active LOW) or pressure ADC
        if GPIO.input(self.irq_pin) == GPIO.LOW:
            return True
        z1 = self._read_adc(self.CMD_Z1)
        return z1 > 100

    def get_touch_point(self) -> tuple[int, int] | None:
        if not self.is_touched():
            self.is_pressed = False
            return None

        # Sample multiple reads for smoothing
        raw_x = sum(self._read_adc(self.CMD_X) for _ in range(3)) // 3
        raw_y = sum(self._read_adc(self.CMD_Y) for _ in range(3)) // 3

        if raw_x == 0 or raw_y == 0:
            return None

        # Map to display resolution (128x160)
        x = max(0, min(self.width - 1, int((raw_x - self.X_MIN) * self.width / (self.X_MAX - self.X_MIN))))
        y = max(0, min(self.height - 1, int((raw_y - self.Y_MIN) * self.height / (self.Y_MAX - self.Y_MIN))))

        self.last_x, self.last_y = x, y
        self.is_pressed = True
        self.last_touch_time = time.time()
        return (x, y)

    def get_mapped_button(self, point: tuple[int, int] | None = None) -> int | None:
        """Maps on-screen touch regions to HardwareButtonsConstants."""
        pt = point if point is not None else self.get_touch_point()
        if not pt:
            return None

        x, y = pt
        # Screen division for 128x160:
        # Center region -> KEY_PRESS / ENTER
        # Top 25% -> KEY_UP
        # Bottom 25% -> KEY_DOWN
        # Left 25% -> KEY_LEFT
        # Right 25% -> KEY_RIGHT
        # Bottom corners -> KEY1, KEY2, KEY3
        if y < self.height * 0.25:
            return HardwareButtonsConstants.KEY_UP
        elif y > self.height * 0.75:
            if x < self.width * 0.33:
                return HardwareButtonsConstants.KEY1
            elif x > self.width * 0.66:
                return HardwareButtonsConstants.KEY3
            return HardwareButtonsConstants.KEY_DOWN
        elif x < self.width * 0.25:
            return HardwareButtonsConstants.KEY_LEFT
        elif x > self.width * 0.75:
            return HardwareButtonsConstants.KEY_RIGHT
        else:
            return HardwareButtonsConstants.KEY_PRESS
