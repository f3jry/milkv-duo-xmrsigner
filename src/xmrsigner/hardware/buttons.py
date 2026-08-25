from __future__ import annotations
try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    from xmrsigner.hardware import milkv_gpio as GPIO

from time import time, sleep
from xmrsigner.models.singleton import Singleton

try:
    from xmrsigner.hardware.xpt2046 import XPT2046
except ImportError:
    XPT2046 = None


class HardwareButtons(Singleton):
    KEY_UP_PIN = 31
    KEY_DOWN_PIN = 35
    KEY_LEFT_PIN = 29
    KEY_RIGHT_PIN = 37
    KEY_PRESS_PIN = 33
    KEY1_PIN = 40
    KEY2_PIN = 38
    KEY3_PIN = 36

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            # init GPIO
            GPIO.setmode(GPIO.BOARD)
            for pin in [
                HardwareButtons.KEY_UP_PIN,
                HardwareButtons.KEY_DOWN_PIN,
                HardwareButtons.KEY_LEFT_PIN,
                HardwareButtons.KEY_RIGHT_PIN,
                HardwareButtons.KEY_PRESS_PIN,
                HardwareButtons.KEY1_PIN,
                HardwareButtons.KEY2_PIN,
                HardwareButtons.KEY3_PIN
            ]:
                try:
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                except Exception:
                    pass

            cls._instance.GPIO = GPIO
            cls._instance.override_ind = False
            cls._instance.add_events([
                HardwareButtonsConstants.KEY_UP,
                HardwareButtonsConstants.KEY_DOWN,
                HardwareButtonsConstants.KEY_PRESS,
                HardwareButtonsConstants.KEY_LEFT,
                HardwareButtonsConstants.KEY_RIGHT,
                HardwareButtonsConstants.KEY1,
                HardwareButtonsConstants.KEY2,
                HardwareButtonsConstants.KEY3
            ])
            cls._instance.cur_input = None
            cls._instance.cur_input_started = None
            cls._instance.last_input_time = int(time() * 1000)
            cls._instance.first_repeat_threshold = 225
            cls._instance.next_repeat_threshold = 250

            # Initialize Touch Controller if available
            cls._instance.touch = None
            if XPT2046 is not None:
                try:
                    cls._instance.touch = XPT2046()
                except Exception:
                    pass

        return cls._instance

    def wait_for(self, keys=[], check_release=True, release_keys=[]) -> int:
        from xmrsigner.controller import Controller
        controller = Controller.get_instance()
        if not release_keys:
            release_keys = keys
        self.override_ind = False
        while True:
            cur_time = int(time() * 1000)
            if cur_time - self.last_input_time > controller.screensaver_activation_ms and (not controller.screensaver or not controller.screensaver.is_running):
                controller.start_screensaver()
                self.update_last_input_time()
                sleep(self.next_repeat_threshold / 1000.0)
                continue

            # Check Touch Screen input
            if self.touch:
                try:
                    touch_key = self.touch.get_mapped_button()
                    if touch_key is not None and touch_key in keys:
                        self.last_input_time = cur_time
                        sleep(0.15)  # Touch debounce
                        return touch_key
                except Exception:
                    pass

            # Check GPIO buttons
            for key in keys:
                if not check_release or ((check_release and key in release_keys and HardwareButtonsConstants.release_lock) or check_release and key not in release_keys):
                    if self.GPIO.input(key) == GPIO.LOW or self.override_ind:
                        HardwareButtonsConstants.release_lock = False
                        if self.override_ind:
                            self.override_ind = False
                            return HardwareButtonsConstants.OVERRIDE
                        if self.cur_input != key:
                            self.cur_input = key
                            self.cur_input_started = int(time() * 1000)
                            self.last_input_time = self.cur_input_started
                            return key
                        if cur_time - self.last_input_time > self.next_repeat_threshold:
                            self.cur_input_started = cur_time
                            self.last_input_time = cur_time
                            return key
                        if cur_time - self.cur_input_started > self.first_repeat_threshold:
                            self.last_input_time = cur_time
                            return key
            sleep(0.01)

    def update_last_input_time(self):
        self.last_input_time = int(time() * 1000)

    def add_events(self, keys=[]):
        for key in keys:
            try:
                self.GPIO.add_event_detect(key, self.GPIO.RISING, callback=HardwareButtons.rising_callback)
            except Exception:
                pass

    @staticmethod
    def rising_callback(channel):
        HardwareButtonsConstants.release_lock = True

    def trigger_override(self, force_release=False) -> bool:
        if force_release:
            HardwareButtonsConstants.release_lock = True
        if not self.override_ind:
            self.override_ind = True
            return True
        return False

    def force_release(self) -> bool:
        HardwareButtonsConstants.release_lock = True
        return True

    def check_for_low(self, key: int = None, keys: list[int] = None) -> bool:
        if key:
            keys = [key]
        for key in keys:
            if self.GPIO.input(key) == self.GPIO.LOW:
                self.update_last_input_time()
                return True
        return False

    def has_any_input(self) -> bool:
        for key in HardwareButtonsConstants.ALL_KEYS:
            if self.GPIO.input(key) == GPIO.LOW:
                return True
        if self.touch and self.touch.is_touched():
            return True
        return False


class HardwareButtonsConstants:
    KEY_UP = 31
    KEY_DOWN = 35
    KEY_LEFT = 29
    KEY_RIGHT = 37
    KEY_PRESS = 33
    KEY1 = 40
    KEY2 = 38
    KEY3 = 36
    OVERRIDE = 1000

    ALL_KEYS = [
        KEY_UP,
        KEY_DOWN,
        KEY_LEFT,
        KEY_RIGHT,
        KEY_PRESS,
        KEY1,
        KEY2,
        KEY3,
    ]

    KEYS__LEFT_RIGHT_UP_DOWN = [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]
    KEYS__ANYCLICK = [KEY_PRESS, KEY1, KEY2, KEY3]

    release_lock = True
