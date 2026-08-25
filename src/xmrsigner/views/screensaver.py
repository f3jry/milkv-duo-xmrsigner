from __future__ import annotations
from random import uniform, choice
from time import time, sleep
from PIL import Image

from xmrsigner.gui.constants import Padding
from xmrsigner.gui.components import Fonts, Theme, load_image
from xmrsigner.gui.screens.screen import BaseScreen
from xmrsigner.models.settings import (
    Settings,
    Setting,
    Option
)


# TODO: This early code is now outdated vis-a-vis Screen vs View distinctions
class LogoScreen(BaseScreen):

    def __init__(self):
        super().__init__()
        raw_logo = load_image('logo_black_240.png')
        if raw_logo.size != (self.canvas_width, self.canvas_height):
            self.logo = raw_logo.resize((self.canvas_width, self.canvas_height), Image.BILINEAR)
        else:
            self.logo = raw_logo
        self.partners = [
            'monero_ccs',
        ]
        self.partner_logos: dict[str, Image.Image]  = {
            partner: load_image(f'partner_{partner}_logo.png')
            for partner in self.partners
        }

    def get_random_partner(self) -> str:
        return choice(self.partners)


class OpeningSplashScreen(LogoScreen):

    def start(self):
        from xmrsigner.controller import Controller
        controller: Controller = Controller.get_instance()
        show_partner_logos: bool = Settings.get_instance().get_value(Setting.PARTNER_LOGOS) == Option.ENABLED
        logo_offset_y = int(-56 * self.canvas_height / 240) if show_partner_logos else 0
        # Fade in alpha
        for i in range(250, -1, -50):
            self.logo.putalpha(255 - i)
            background = Image.new('RGBA', size=self.logo.size, color=Theme.BACKGROUND_COLOR)
            self.renderer.canvas.paste(Image.alpha_composite(background, self.logo), (0, logo_offset_y))
            self.renderer.show_image()
        # Display version num below XmrSigner logo
        font = Fonts.get_font(Theme.BODY_FONT_NAME, Theme.TOP_NAV_TITLE_FONT_SIZE)
        version = f'v{controller.VERSION}'
        version_x = int(self.renderer.canvas_width - 15)
        version_y = int(self.canvas_height / 2) + int(35 * self.canvas_height / 240) + logo_offset_y + Padding.COMPONENT
        self.renderer.draw.text(xy=(version_x, version_y), text=version, font=font, fill=Theme.VERSION_COLOR, anchor='rt')
        self.renderer.show_image()
        sleep(0.5)


class ScreensaverScreen(LogoScreen):

    def __init__(self, buttons):
        super().__init__()
        self.buttons = buttons
        self.is_running = False

    def start(self):
        self.is_running = True
        self.renderer.display_blank_screen()
        while self.is_running:
            if self.buttons.has_any_input():
                self.is_running = False
                break
            sleep(0.05)

    def stop(self):
        self.is_running = False
