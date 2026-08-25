from __future__ import annotations
import os
from .constants import (
    Color,
    FontAwesome,
    Padding,
    Font
)
from .constants import Icon as IconConstants

class Theme:
    BACKGROUND_COLOR: Color = Color.BLACK
    WARNING_COLOR: Color = Color.YELLOW
    DIRE_WARNING_COLOR: Color = Color.RED_FADED
    DISCARD_COLOR: Color = Color.RED
    SUCCESS_COLOR: Color = Color.GREEN
    ACCENT_COLOR: Color = Color.MONERO_ORANGE
    ACCENT_COLOR_FADED: Color = Color.MONERO_ORANGE_FADED
    MAINNET_COLOR: Color = ACCENT_COLOR
    TESTNET_COLOR: Color = Color.GREEN_PASTEL
    STAGENET_COLOR: Color = Color.BLUE_PASTEL
    INFO_COLOR: Color = Color.BLUE
    VERSION_COLOR: Color = ACCENT_COLOR

    ICON_FONT_NAME__FONT_AWESOME: Font = Font.AWESOME
    ICON_FONT_NAME__XMRSIGNER: Font = Font.ICON
    ICON_FONT_SIZE: int = 22
    ICON_INLINE_FONT_SIZE: int = 24
    ICON_LARGE_BUTTON_SIZE: int = 36
    ICON_PRIMARY_SCREEN_SIZE: int = 50

    TOP_NAV_TITLE_FONT_NAME: Font = Font.OPEN_SANS_SEMI_BOLD
    TOP_NAV_TITLE_FONT_SIZE: int = 20
    TOP_NAV_HEIGHT: int = 48
    TOP_NAV_BUTTON_SIZE: int = 32

    BODY_FONT_NAME: Font = Font.OPEN_SANS_REGULAR
    BODY_FONT_SIZE: int = 17
    BODY_FONT_MAX_SIZE: int = TOP_NAV_TITLE_FONT_SIZE
    BODY_FONT_MIN_SIZE: int = 15
    BODY_FONT_COLOR: Color = Color.WHITE_FADED
    BODY_LINE_SPACING: int = Padding.COMPONENT

    FIXED_WIDTH_FONT_NAME: Font = Font.INCONSOLATA_REGULAR
    FIXED_WIDTH_EMPHASIS_FONT_NAME: Font = Font.INCONSOLATA_SEMI_BOLD

    LABEL_FONT_SIZE: int = BODY_FONT_MIN_SIZE
    LABEL_FONT_COLOR: Color = Color.GRAY

    BUTTON_FONT_NAME: Font = Font.OPEN_SANS_SEMI_BOLD
    BUTTON_FONT_SIZE: int = 18
    BUTTON_FONT_COLOR: Color = Color.WHITE_FADED
    BUTTON_BACKGROUND_COLOR: Color = Color.BLACK_FADED
    BUTTON_HEIGHT: int = 32
    BUTTON_SELECTED_FONT_COLOR: Color = BACKGROUND_COLOR

    FINGERPRINT_MONERO_SEED_COLOR: Color = Color.BLUE
    FINGERPRINT_POLYSEED_COLOR: Color = Color.PURPLE
    FINGERPRINT_LEGACY_SEED_COLOR: Color = Color.RED
    LOADING_SCREEN_LOGO_IMAGE: str = 'xmr_logo_60x60.png'
    LOADING_SCREEN_ARC_COLOR: Color = ACCENT_COLOR
    LOADING_SCREEN_ARC_TRAILING_COLOR: Color = ACCENT_COLOR_FADED
    BRIGHTNESS_TEXT_COLOR: Color = Color.BLACK
    ARROW_COLOR: Color = Color.BLACK
    QRCODE_FILL_COLOR: Color = Color.BLACK
    XMRSIGNER_DOMAIN: str = 'xmrsigner.github.io'
    XMRSIGNER_DONATION_TEXT: str = f'XmrSigner is 100% free & open source, funded solely by the Monero community.\n\nDonate onchain at: {XMRSIGNER_DOMAIN}/donate'

    XMRSIGNER_UPDATE_URL: str = f'{XMRSIGNER_DOMAIN}/download'

    KEYBOARD_OUTLINE_COLOR: Color = Color.GRAY_DARK
    KEYBOARD_HIGHLIGHT_COLOR: Color = ACCENT_COLOR
    KEYBOARD_KEY_BACKGROUND_COLOR: Color = BUTTON_BACKGROUND_COLOR
    KEYBOARD_KEY_BACKGROUND_COLOR_DEACTIVATED: Color = BACKGROUND_COLOR
    KEYBOARD_KEY_COLOR: Color = Color.BLACK
    KEYBOARD_KEY_COLOR_DEACTIVATED: Color = Color.GRAY_DARK
    KEYBOARD_ADDITONAL_KEY_COLOR: Color = Color.GRAY_LIGHT
    KEYBOARD_OTHER_KEY_COLOR: Color = Color.WHITE_DARK
    KEYBOARD_CURSOR_COLOR: Color = Color.GRAY_DARKER
    KEYBOARD_CURSOR_BAR_COLOR: Color = Color.GRAY_LIGHTER

    @classmethod
    def XMRSIGNER_ABOUT_TEXT(cls) -> str:
        from xmrsigner.controller import Controller
        version = Controller.VERSION
        return f'XmrSigner Version {Controller.VERSION}\n\nYou can find the newest version always at: {cls.XMRSIGNER_UPDATE_URL}'


def _apply_display_scale(scale: float):
    """Scale fonts, icons, and padding for canvases smaller than the 240px
    reference layout (e.g. the 128x160 1.8" ST7735 TFT).

    Must run at import time: components bind Theme/Padding values as dataclass
    defaults when they are first imported.
    """
    def s(value, floor):
        return max(floor, int(round(value * scale)))

    Theme.ICON_FONT_SIZE = s(Theme.ICON_FONT_SIZE, 12)
    Theme.ICON_INLINE_FONT_SIZE = s(Theme.ICON_INLINE_FONT_SIZE, 13)
    Theme.ICON_LARGE_BUTTON_SIZE = s(Theme.ICON_LARGE_BUTTON_SIZE, 20)
    Theme.ICON_PRIMARY_SCREEN_SIZE = s(Theme.ICON_PRIMARY_SCREEN_SIZE, 28)
    Theme.TOP_NAV_TITLE_FONT_SIZE = s(Theme.TOP_NAV_TITLE_FONT_SIZE, 12)
    Theme.TOP_NAV_HEIGHT = s(Theme.TOP_NAV_HEIGHT, 26)
    Theme.TOP_NAV_BUTTON_SIZE = s(Theme.TOP_NAV_BUTTON_SIZE, 18)
    Theme.BODY_FONT_SIZE = s(Theme.BODY_FONT_SIZE, 10)
    Theme.BODY_FONT_MIN_SIZE = s(Theme.BODY_FONT_MIN_SIZE, 9)
    Theme.BODY_FONT_MAX_SIZE = Theme.TOP_NAV_TITLE_FONT_SIZE
    Theme.LABEL_FONT_SIZE = Theme.BODY_FONT_MIN_SIZE
    Theme.BUTTON_FONT_SIZE = s(Theme.BUTTON_FONT_SIZE, 10)
    Theme.BUTTON_HEIGHT = s(Theme.BUTTON_HEIGHT, 18)
    Padding.EDGE = s(Padding.EDGE, 4)
    Padding.COMPONENT = s(Padding.COMPONENT, 4)
    Padding.LIST_ITEM = s(Padding.LIST_ITEM, 2)
    Theme.BODY_LINE_SPACING = Padding.COMPONENT


# The 128x160 ST7735 renders at native resolution; shrink the 240px-reference
# theme to match. Must agree with Renderer.configure_instance().
if os.environ.get('DISPLAY_TYPE', 'ST7735').upper() == 'ST7735':
    _apply_display_scale(128 / 240)
