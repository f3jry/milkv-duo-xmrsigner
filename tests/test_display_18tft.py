"""
Headless verification of the L07-1.8TFT-ChuMo (128x160 ST7735 + XPT2046) drivers.

Uses a fake spidev and the milkv_gpio sysfs fallback so the full driver stack
(init sequence, 4KB SPI chunking, RGB565 encoding, touch mapping, renderer
canvas) can be tested without hardware.
"""
import os
import sys
import types

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ---------------------------------------------------------------------------
# Fake spidev + GPIO state recorder
# ---------------------------------------------------------------------------

class FakeSpiDev:
    """Records every SPI write; serves scripted ADC responses for xfer2."""
    instances = []
    adc_values = {}       # cmd -> 12-bit value returned by xfer2
    gpio_state = {}       # pin -> last output value (shared with GPIO recorder)

    def __init__(self, bus, dev):
        self.bus = bus
        self.dev = dev
        self.max_speed_hz = None
        self.writes = []  # list of (dc_state, bytes)
        FakeSpiDev.instances.append(self)

    def _dc(self):
        return FakeSpiDev.gpio_state.get(22, 1)  # ST7735 DC = BOARD pin 22

    def writebytes(self, data):
        self.writes.append((self._dc(), bytes(data)))

    def writebytes2(self, data):
        self.writes.append((self._dc(), bytes(data)))

    def xfer2(self, data):
        self.writes.append((self._dc(), bytes(data)))
        val = FakeSpiDev.adc_values.get(data[0], 0)
        raw = (val & 0x0FFF) << 3
        return [0x00, (raw >> 8) & 0xFF, raw & 0xFF]

    def close(self):
        pass


@pytest.fixture()
def fake_hardware(monkeypatch):
    FakeSpiDev.instances = []
    FakeSpiDev.adc_values = {}
    FakeSpiDev.gpio_state = {}

    fake_spidev = types.ModuleType("spidev")
    fake_spidev.SpiDev = FakeSpiDev
    monkeypatch.setitem(sys.modules, "spidev", fake_spidev)

    real_exists = os.path.exists

    def fake_exists(path):
        if str(path).startswith("/dev/spidev"):
            return True
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", fake_exists)

    # Force the milkv_gpio fallback and record output() pin states
    monkeypatch.setitem(sys.modules, "RPi.GPIO", None)
    for mod in list(sys.modules):
        if mod.startswith("xmrsigner.hardware"):
            del sys.modules[mod]
    from xmrsigner.hardware import milkv_gpio
    real_output = milkv_gpio.output

    def recording_output(channel, value):
        FakeSpiDev.gpio_state[channel] = value
        real_output(channel, value)

    monkeypatch.setattr(milkv_gpio, "output", recording_output)
    yield FakeSpiDev


def _command_stream(spi):
    """Split recorded writes into (commands, data) based on DC pin state."""
    cmds, data = [], b""
    for dc, payload in spi.writes:
        if dc == 0:
            cmds.extend(payload)
        else:
            data += payload
    return cmds, data


def _pixel_data(spi):
    """Framebuffer payload only: data writes larger than 4-byte addr windows."""
    return b"".join(payload for dc, payload in spi.writes
                    if dc == 1 and len(payload) > 4)


# ---------------------------------------------------------------------------
# ST7735 display driver
# ---------------------------------------------------------------------------

def test_st7735_init_sequence(fake_hardware):
    from xmrsigner.hardware.ST7735 import ST7735
    disp = ST7735(width=128, height=160, bgr=True)
    spi = disp._spi
    assert spi is not None
    assert spi.max_speed_hz == 24000000

    cmds, _ = _command_stream(spi)
    for expected in [ST7735.SWRESET, ST7735.SLPOUT, ST7735.COLMOD,
                     ST7735.MADCTL, ST7735.DISPON]:
        assert expected in cmds, f"missing init command {expected:#x}"

    # MADCTL data must follow the MADCTL command: portrait 0xC0 | BGR 0x08
    madctl_data = None
    for i, (dc, payload) in enumerate(spi.writes):
        if dc == 0 and payload == bytes([ST7735.MADCTL]):
            madctl_data = spi.writes[i + 1][1][0]
            break
    assert madctl_data == 0xC8


def test_st7735_full_frame_4kb_chunking(fake_hardware):
    from xmrsigner.hardware.ST7735 import ST7735
    disp = ST7735(width=128, height=160, bgr=True)
    spi = disp._spi
    spi.writes.clear()

    disp.ShowImage(Image.new("RGB", (128, 160), (255, 0, 0)))

    data = _pixel_data(spi)
    assert len(data) == 128 * 160 * 2  # full RGB565 frame = 40960 bytes

    frame_writes = [len(payload) for dc, payload in spi.writes
                    if dc == 1 and len(payload) > 4]
    assert frame_writes, "no framebuffer writes recorded"
    assert max(frame_writes) <= 4096, "SPI write exceeds CV1800B 4KB FIFO limit"
    assert sum(frame_writes) == 40960
    # red pixel in BGR565: blue field (high bits) = 0, red field (low) = 0x1F
    assert data[:2] == bytes([0x00, 0x1F])


def test_st7735_rgb_mode_encoding(fake_hardware):
    from xmrsigner.hardware.ST7735 import ST7735
    disp = ST7735(width=128, height=160, bgr=False)
    spi = disp._spi
    spi.writes.clear()

    disp.ShowImage(Image.new("RGB", (128, 160), (255, 0, 0)))
    data = _pixel_data(spi)
    assert data[:2] == bytes([0xF8, 0x00])  # RGB565 red, big-endian


def test_st7735_resizes_mismatched_image(fake_hardware):
    from xmrsigner.hardware.ST7735 import ST7735
    disp = ST7735(width=128, height=160)
    spi = disp._spi
    spi.writes.clear()

    disp.ShowImage(Image.new("RGB", (240, 240), (0, 0, 255)))
    assert len(_pixel_data(spi)) == 40960


def test_st7735_green_tab_offsets(fake_hardware):
    from xmrsigner.hardware.ST7735 import ST7735
    disp = ST7735(width=128, height=160, tab_type="green")
    assert (disp.col_offset, disp.row_offset) == (2, 1)
    spi = disp._spi
    spi.writes.clear()
    disp.SetWindows(0, 0, 128, 160)
    cmds, data = _command_stream(spi)
    # CASET payload: x0=2, x1=129 ; RASET payload: y0=1, y1=160
    assert bytes([0x00, 0x02, 0x00, 0x81]) in data
    assert bytes([0x00, 0x01, 0x00, 0xA0]) in data


def test_rgb565_encoder_parity():
    from xmrsigner.hardware.rgb565 import to_rgb565_be

    img = Image.new("RGB", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            px[x, y] = (x * 17, y * 17, (x + y) * 8)

    numpy_result = to_rgb565_be(img, bgr=True)

    numpy_mod = sys.modules.get("numpy")
    sys.modules["numpy"] = None  # force ImportError -> pure-python path
    try:
        fallback_result = to_rgb565_be(img, bgr=True)
    finally:
        sys.modules["numpy"] = numpy_mod

    assert numpy_result == fallback_result
    assert len(numpy_result) == 16 * 16 * 2


# ---------------------------------------------------------------------------
# XPT2046 touch driver
# ---------------------------------------------------------------------------

def _make_touch(fake_hardware, raw_x, raw_y, pressed=True):
    from xmrsigner.hardware.xpt2046 import XPT2046
    FakeSpiDev.adc_values = {
        XPT2046.CMD_X: raw_x,
        XPT2046.CMD_Y: raw_y,
        XPT2046.CMD_Z1: 500 if pressed else 0,
    }
    return XPT2046(width=128, height=160)


def test_xpt2046_default_pins_match_spec(fake_hardware):
    from xmrsigner.hardware.xpt2046 import XPT2046
    touch = XPT2046()
    assert touch.cs_pin == 26   # T_CS  = physical pin 26 (GP18)
    assert touch.irq_pin == 27  # T_IRQ = physical pin 27 (GP17); must not collide with TFT CS on pin 24


def test_xpt2046_coordinate_mapping(fake_hardware):
    from xmrsigner.hardware.xpt2046 import XPT2046
    touch = _make_touch(fake_hardware, XPT2046.X_MIN, XPT2046.Y_MIN)
    assert touch.get_touch_point() == (0, 0)

    touch = _make_touch(fake_hardware, XPT2046.X_MAX, XPT2046.Y_MAX)
    assert touch.get_touch_point() == (127, 159)

    mid_x = (XPT2046.X_MIN + XPT2046.X_MAX) // 2
    mid_y = (XPT2046.Y_MIN + XPT2046.Y_MAX) // 2
    touch = _make_touch(fake_hardware, mid_x, mid_y)
    x, y = touch.get_touch_point()
    assert abs(x - 64) <= 1 and abs(y - 80) <= 1


def test_xpt2046_no_touch_returns_none(fake_hardware):
    touch = _make_touch(fake_hardware, 2000, 2000, pressed=False)
    assert touch.get_touch_point() is None
    assert touch.get_mapped_button() is None


def test_xpt2046_button_mapping(fake_hardware):
    from xmrsigner.hardware.xpt2046 import XPT2046
    from xmrsigner.hardware.buttons import HardwareButtonsConstants as C
    touch = _make_touch(fake_hardware, 2000, 2000)

    assert touch.get_mapped_button((64, 10)) == C.KEY_UP
    assert touch.get_mapped_button((64, 80)) == C.KEY_PRESS
    assert touch.get_mapped_button((10, 80)) == C.KEY_LEFT
    assert touch.get_mapped_button((120, 80)) == C.KEY_RIGHT
    assert touch.get_mapped_button((64, 150)) == C.KEY_DOWN
    assert touch.get_mapped_button((10, 150)) == C.KEY1
    assert touch.get_mapped_button((120, 150)) == C.KEY3


# ---------------------------------------------------------------------------
# Renderer canvas
# ---------------------------------------------------------------------------

def test_renderer_native_128x160_canvas(fake_hardware, monkeypatch):
    monkeypatch.setenv("DISPLAY_TYPE", "ST7735")
    for mod in list(sys.modules):
        if mod.startswith("xmrsigner.gui"):
            del sys.modules[mod]
    from xmrsigner.gui.renderer import Renderer
    Renderer._instance = None
    Renderer.configure_instance()
    r = Renderer.get_instance()
    assert (r.canvas_width, r.canvas_height) == (128, 160)
    assert r.canvas.size == (128, 160)

    r.disp._spi.writes.clear()
    r.draw.rectangle((0, 0, 127, 159), fill=(237, 95, 0))  # Monero orange
    r.show_image()
    data = _pixel_data(r.disp._spi)
    assert len(data) == 40960
    # (237, 95, 0) BGR565 -> high=blue(0), mid=green(95), low=red(237)
    expected = ((0 & 0xF8) << 8) | ((95 & 0xFC) << 3) | (237 >> 3)
    assert data[:2] == expected.to_bytes(2, "big")
    Renderer._instance = None


# ---------------------------------------------------------------------------
# Theme scaling & narrow-screen layouts
# ---------------------------------------------------------------------------

def _configure_gui(monkeypatch, display_type):
    """Re-import the gui stack under a given DISPLAY_TYPE (theme is scaled at
    import time) and configure a fresh Renderer."""
    monkeypatch.setenv("DISPLAY_TYPE", display_type)
    for mod in list(sys.modules):
        if mod.startswith("xmrsigner.gui"):
            del sys.modules[mod]
    from xmrsigner.gui.renderer import Renderer
    Renderer._instance = None
    Renderer.configure_instance()
    return Renderer.get_instance()


def test_theme_scaled_for_st7735_only(fake_hardware, monkeypatch):
    _configure_gui(monkeypatch, "ST7735")
    from xmrsigner.gui.components import Theme
    from xmrsigner.gui.constants import Padding
    assert Theme.TOP_NAV_TITLE_FONT_SIZE < 20
    assert Theme.BODY_FONT_SIZE < 17
    assert Padding.EDGE < 8

    _configure_gui(monkeypatch, "ST7789")
    from xmrsigner.gui.components import Theme as Theme240
    from xmrsigner.gui.constants import Padding as Padding240
    assert Theme240.TOP_NAV_TITLE_FONT_SIZE == 20
    assert Theme240.BODY_FONT_SIZE == 17
    assert Padding240.EDGE == 8


def test_textarea_shrinks_font_on_narrow_canvas(fake_hardware, monkeypatch):
    r = _configure_gui(monkeypatch, "ST7735")
    from xmrsigner.gui.components import TextArea, TextDoesNotFitException
    # Unbreakable word that cannot fit at the requested font size
    ta = TextArea(
        text="xmrsigner.github.io",
        font_size=16,
        width=r.canvas_width,
    )
    assert ta.font_size < 16
    assert max(line["text_width"] for line in ta.text_lines) <= r.canvas_width - 2 * ta.edge_padding + 1

    # A word that cannot fit even at the smallest font still raises
    with pytest.raises(TextDoesNotFitException):
        TextArea(
            text="xmrsigner.github.io/download",
            font_size=16,
            width=r.canvas_width,
        )


def test_mnemonic_keyboard_layout_fits_canvas(fake_hardware, monkeypatch):
    r = _configure_gui(monkeypatch, "ST7735")
    from xmrsigner.gui.screens.seed_screens import SeedMnemonicEntryScreen
    from xmrsigner.models.wordlists.monero.en import MoneroEnglishWordlist
    screen = SeedMnemonicEntryScreen(
        wordlist=MoneroEnglishWordlist.words,
        initial_letters=["a"],
    )
    assert screen.keyboard_width < r.canvas_width
    # The matches list panel to the right of the keyboard must have room
    assert r.canvas_width - screen.matches_list_x > 0
    screen._render()  # must not raise (regression: negative-width Image.new)
