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

# Standard Milk-V Duo Pin to Sysfs GPIO mapping
# Waveshare 1.3" HAT connected to Milk-V Duo header:
# UP: GP14 (GPIO 426), DOWN: GP15 (GPIO 427), LEFT: GP16 (GPIO 428), RIGHT: GP17 (GPIO 429), PRESS: GP18 (GPIO 430)
# KEY1: GP19 (GPIO 431), KEY2: GP20 (GPIO 432), KEY3: GP21 (GPIO 433)
# DC: GP4 (GPIO 448), RST: GP3 (GPIO 511), BL: GP2 (GPIO 510)
MILKV_PIN_MAP = {
    # BOARD pin numbers to Sysfs GPIO IDs
    31: 426,  # KEY_UP
    35: 427,  # KEY_DOWN
    29: 428,  # KEY_LEFT
    37: 429,  # KEY_RIGHT
    33: 430,  # KEY_PRESS
    40: 431,  # KEY1
    38: 432,  # KEY2
    36: 433,  # KEY3
    22: 448,  # LCD DC
    13: 511,  # LCD RST
    18: 510,  # LCD BL
    # 1.8" TFT V1.1 (L07-1.8TFT-ChuMo) touch controller pins
    26: 430,  # T_CS (GP18)
    27: 429,  # T_IRQ (GP17)
}

_mode = BOARD
_warnings = False
_gpio_exported = set()
_callbacks = {}
_term_key_state = {}
_term_lock = threading.Lock()


def _get_sysfs_gpio(channel):
    if _mode == BOARD:
        return MILKV_PIN_MAP.get(channel, channel)
    return channel


def setmode(mode):
    global _mode
    _mode = mode


def setwarnings(flag):
    global _warnings
    _warnings = flag


def setup(channel, direction, pull_up_down=PUD_OFF, initial=LOW):
    gpio_num = _get_sysfs_gpio(channel)
    gpio_path = f"/sys/class/gpio/gpio{gpio_num}"

    # Try exporting sysfs GPIO if running on Linux with root/gpio permissions
    if os.path.exists("/sys/class/gpio"):
        try:
            if not os.path.exists(gpio_path):
                with open("/sys/class/gpio/export", "w") as f:
                    f.write(str(gpio_num))
                time.sleep(0.05)
            
            with open(f"{gpio_path}/direction", "w") as f:
                f.write("out" if direction == OUT else "in")
            
            if direction == OUT:
                with open(f"{gpio_path}/value", "w") as f:
                    f.write(str(initial))
            
            _gpio_exported.add(gpio_num)
        except Exception:
            pass

    _term_key_state[channel] = HIGH


def output(channel, value):
    gpio_num = _get_sysfs_gpio(channel)
    gpio_path = f"/sys/class/gpio/gpio{gpio_num}/value"
    if os.path.exists(gpio_path):
        try:
            with open(gpio_path, "w") as f:
                f.write("1" if value else "0")
        except Exception:
            pass


def input(channel):
    # Check terminal/virtual state first
    with _term_lock:
        if channel in _term_key_state and _term_key_state[channel] == LOW:
            _term_key_state[channel] = HIGH  # Auto reset momentary button press
            return LOW

    gpio_num = _get_sysfs_gpio(channel)
    gpio_path = f"/sys/class/gpio/gpio{gpio_num}/value"
    if os.path.exists(gpio_path):
        try:
            with open(gpio_path, "r") as f:
                val = f.read().strip()
                return LOW if val == "0" else HIGH
        except Exception:
            pass
    return HIGH


def add_event_detect(channel, edge, callback=None, bouncetime=None):
    if callback:
        _callbacks[channel] = callback


def cleanup(channel=None):
    if channel:
        channels = [channel]
    else:
        channels = list(_gpio_exported)
    
    for ch in channels:
        gpio_num = _get_sysfs_gpio(ch)
        if os.path.exists(f"/sys/class/gpio/gpio{gpio_num}"):
            try:
                with open("/sys/class/gpio/unexport", "w") as f:
                    f.write(str(gpio_num))
            except Exception:
                pass
    _gpio_exported.clear()


# Terminal / Keyboard helper for testing and remote console control
def inject_key_press(channel):
    with _term_lock:
        _term_key_state[channel] = LOW
    if channel in _callbacks:
        try:
            _callbacks[channel](channel)
        except Exception:
            pass
