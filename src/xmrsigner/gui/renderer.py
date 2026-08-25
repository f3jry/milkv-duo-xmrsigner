from __future__ import annotations
import os
from PIL import Image, ImageDraw
from threading import Lock

from xmrsigner.models.singleton import ConfigurableSingleton

try:
    from xmrsigner.hardware.ST7735 import ST7735
except ImportError:
    ST7735 = None

try:
    from xmrsigner.hardware.ST7789 import ST7789
except ImportError:
    ST7789 = None


class Renderer(ConfigurableSingleton):

    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas: Image.Image = None
    draw: ImageDraw.ImageDraw = None
    disp = None
    lock = Lock()

    @classmethod
    def configure_instance(cls):
        renderer = cls.__new__(cls)
        cls._instance = renderer

        # Check display type from environment or hardware preference
        # DISPLAY_TYPE can be 'ST7735' (128x160) or 'ST7789' (240x240)
        display_type = os.environ.get('DISPLAY_TYPE', 'ST7735').upper()

        if display_type == 'ST7735' and ST7735 is not None:
            print('=> Initializing ST7735 128x160 1.8" TFT SPI Display')
            renderer.disp = ST7735(width=128, height=160)
            renderer.canvas_width = 240  # Standard virtual canvas for crisp UI layout
            renderer.canvas_height = 240
        elif ST7789 is not None:
            print('=> Initializing ST7789 240x240 Display')
            renderer.disp = ST7789()
            renderer.canvas_width = renderer.disp.width
            renderer.canvas_height = renderer.disp.height
        elif ST7735 is not None:
            renderer.disp = ST7735()
            renderer.canvas_width = 240
            renderer.canvas_height = 240
        else:
            # Headless fallback
            renderer.disp = None
            renderer.canvas_width = 240
            renderer.canvas_height = 240

        renderer.canvas = Image.new('RGB', (renderer.canvas_width, renderer.canvas_height))
        renderer.draw = ImageDraw.Draw(renderer.canvas)

    def show_image(self, image=None, alpha_overlay=None, show_direct=False):
        with self.lock:
            if show_direct and image is not None:
                if self.disp:
                    self.disp.ShowImage(image, 0, 0)
                return

            if alpha_overlay:
                if image is None:
                    image = self.canvas
                image = Image.alpha_composite(image, alpha_overlay)

            if image:
                self.canvas.paste(image)

            if self.disp:
                # If physical display is 128x160, ShowImage automatically resizes with bilinear antialiasing
                self.disp.ShowImage(self.canvas, 0, 0)

    def show_image_pan(self, image, start_x, start_y, end_x, end_y, rate, alpha_overlay=None):
        cur_x = start_x
        cur_y = start_y
        rate_x = rate if end_x >= start_x else -rate
        rate_y = rate if end_y >= start_y else -rate

        while (cur_x != end_x or cur_y != end_y) and (rate_x != 0 or rate_y != 0):
            cur_x += rate_x
            if (rate_x > 0 and cur_x > end_x) or (rate_x < 0 and cur_x < end_x):
                cur_x = end_x
                rate_x = 0

            cur_y += rate_y
            if (rate_y > 0 and cur_y > end_y) or (rate_y < 0 and cur_y < end_y):
                cur_y = end_y
                rate_y = 0

            crop = image.crop((cur_x, cur_y, cur_x + self.canvas_width, cur_y + self.canvas_height))
            if alpha_overlay:
                crop = Image.alpha_composite(crop, alpha_overlay)

            self.canvas.paste(crop)
            if self.disp:
                self.disp.ShowImage(crop, 0, 0)

    def display_blank_screen(self):
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.show_image()
