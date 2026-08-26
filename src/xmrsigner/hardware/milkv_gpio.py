from __future__ import annotations
"""
Milk-V Duo (CV1800B) GPIO Driver and Compatibility Layer
Provides RPi.GPIO compatible API using Linux sysfs (/sys/class/gpio) and terminal fallback.
"""
import os
import sys
import time
import select
import threading

# Pin Modes
BCM = 11
BOARD = 10

# Pin Directions
IN = 1
OUT = 0

# Pin Values
HIGH = 1
LOW = 0

# Pull Up / Down
PUD_OFF = 0
PUD_DOWN = 1
PUD_UP = 2

# Edge Detection
RISING = 1
FALLING = 2
BOTH = 3

RPI_INFO = {
    'P1_REVISION': 3,
    'RAM': '64M',
    'REVISION': 'milkv-duo-cv1800b',
    'TYPE': 'Milk-V Duo 64MB',
    'PROCESSOR': 'CV1800B RISC-V 64'
}

# Milk-V Duo Pin to Sysfs GPIO mapping
MILKV_PIN_MAP = {
    # DIP-40 Physical Pin Numbers -> Sysfs GPIO IDs
    4:  510,  # GP2 (LCD BL)
    5:  511,  # GP3 (LCD RST)
    6:  448,  # GP4 (LCD DC)
    7:  431,  # GP5 (SPI2_CS / LCD CS)
    22: 429,  # GP17 (Touch T_IRQ)
    24: 430,  # GP18 (Touch T_CS)

    # Legacy RPi HAT BOARD numbers mapping:
    31: 426,  # KEY_UP
    35: 427,  # KEY_DOWN
    29: 428,  # KEY_LEFT
    37: 429,  # KEY_RIGHT
    33: 430,  # KEY_PRESS
    40: 431,  # KEY1
    38: 432,  # KEY2
    36: 433,  # KEY3
    18: 510,  # BL
    13: 511,  # RST
    26: 430,  # T_CS
    27: 429,  # T_IRQ
}

_mode = BOARD
_warnings = False
_gpio_exported = set()
_callbacks = {}
_term_key_state = {}
_term_lock = threading.Lock()


def _get_sysfs_gpio(channel):
    if channel > 100:
        return channel
    return MILKV_PIN_MAP.get(channel, channel)


def setmode(mode):
    global _mode
    _mode = mode


def setwarnings(flag):
    global _warnings
    _warnings = flag


def setup(channel, direction, pull_up_down=PUD_OFF, initial=LOW):
    gpio_num = _get_sysfs_gpio(channel)
    gpio_path = f"/sys/class/gpio/gpio{gpio_num}"

    # Export GPIO if not already exported
    if not os.path.exists(gpio_path):
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(gpio_num))
            _gpio_exported.add(gpio_num)
        except Exception:
            pass

    # Set Direction
    dir_str = "out" if direction == OUT else "in"
    try:
        with open(f"{gpio_path}/direction", "w") as f:
            f.write(dir_str)
    except Exception:
        pass

    if direction == OUT:
        output(channel, initial)


def output(channel, value):
    gpio_num = _get_sysfs_gpio(channel)
    gpio_val_path = f"/sys/class/gpio/gpio{gpio_num}/value"
    val_str = "1" if value else "0"
    try:
        with open(gpio_val_path, "w") as f:
            f.write(val_str)
    except Exception:
        pass


def input(channel):
    gpio_num = _get_sysfs_gpio(channel)
    gpio_val_path = f"/sys/class/gpio/gpio{gpio_num}/value"
    try:
        with open(gpio_val_path, "r") as f:
            v = f.read().strip()
            return HIGH if v == "1" else LOW
    except Exception:
        with _term_lock:
            return _term_key_state.get(channel, HIGH)


def cleanup(channel=None):
    if channel is not None:
        pins = [channel]
    else:
        pins = list(_gpio_exported)

    for p in pins:
        gpio_num = _get_sysfs_gpio(p)
        try:
            with open("/sys/class/gpio/unexport", "w") as f:
                f.write(str(gpio_num))
        except Exception:
            pass
