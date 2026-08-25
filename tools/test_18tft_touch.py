#!/usr/bin/env python3
"""
Diagnostic & Calibration Utility for 1.8" 128x160 SPI TFT (ST7735) + XPT2046 Touch
Specifically for '128x160 1.8TFT SPI V1.1' (L07-1.8TFT-ChuMo / H1376 11-10)
"""
import sys
import os
import time
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from xmrsigner.hardware.ST7735 import ST7735
from xmrsigner.hardware.xpt2046 import XPT2046


def run_diagnostic():
    print("=" * 60)
    print(" 1.8\" 128x160 SPI TFT (ST7735) & Touch (XPT2046) Diagnostics")
    print("=" * 60)

    # 1. Initialize display
    print("[+] Initializing ST7735 (128x160)...")
    disp = ST7735(width=128, height=160, bgr=True)
    touch = XPT2046(width=128, height=160)

    # 2. Draw Color Test Pattern
    print("[+] Drawing RGB test pattern...")
    img = Image.new('RGB', (128, 160), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Color bars
    draw.rectangle((0, 0, 128, 30), fill=(255, 0, 0))    # Red
    draw.rectangle((0, 30, 128, 60), fill=(0, 255, 0))   # Green
    draw.rectangle((0, 60, 128, 90), fill=(0, 0, 255))   # Blue
    draw.rectangle((0, 90, 128, 120), fill=(237, 95, 0)) # Monero Orange
    draw.rectangle((0, 120, 128, 160), fill=(20, 20, 20)) # Dark Grey

    draw.text((10, 10), "RED", fill=(255, 255, 255))
    draw.text((10, 40), "GREEN", fill=(0, 0, 0))
    draw.text((10, 70), "BLUE", fill=(255, 255, 255))
    draw.text((10, 100), "XMR ORANGE", fill=(255, 255, 255))
    draw.text((10, 130), "TOUCH TEST", fill=(255, 255, 0))

    disp.ShowImage(img)
    print("[+] Color bars displayed. Starting interactive touch loop (Ctrl+C to exit)...")

    # 3. Interactive Touch Tracking Loop
    last_pt = None
    try:
        while True:
            pt = touch.get_touch_point()
            if pt:
                x, y = pt
                btn = touch.get_mapped_button()
                print(f"\r[TOUCH] Raw (X={x:3d}, Y={y:3d}) -> Virtual Button Code: {btn}", end="")
                
                # Draw dynamic touch indicator on screen
                touch_img = img.copy()
                t_draw = ImageDraw.Draw(touch_img)
                t_draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 0), outline=(255, 255, 255))
                t_draw.text((10, 145), f"X:{x} Y:{y}", fill=(0, 255, 255))
                disp.ShowImage(touch_img)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[+] Exiting test.")


if __name__ == '__main__':
    run_diagnostic()
