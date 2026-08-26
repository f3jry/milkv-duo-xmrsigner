#!/usr/bin/env python3
"""
Dynamic TV Static / Random Noise Generator for 1.8" 128x160 SPI TFT (ST7735)
Continuously flips every pixel randomly at maximum SPI refresh rate.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from xmrsigner.hardware.ST7735 import ST7735


def run_noise():
    print("=" * 60)
    print(" 1.8\" 128x160 ST7735 Real-Time Random Noise Pattern")
    print("=" * 60)

    disp = ST7735(width=128, height=160, bgr=True)
    disp.set_window(0, 0, 127, 159)

    frame_bytes_len = 128 * 160 * 2  # 40,960 bytes per 128x160 RGB565 frame
    frame_count = 0
    start_time = time.time()

    print("[+] Starting continuous high-speed TV static noise...")
    while True:
        # Generate 40,960 random bytes for maximum pixel modulation
        noise_frame = os.urandom(frame_bytes_len)
        disp.data(noise_frame)
        frame_count += 1
        if frame_count % 30 == 0:
            fps = frame_count / (time.time() - start_time)
            print(f"\r[+] Streaming Static Noise: {frame_count} frames ({fps:.1f} FPS)", end="", flush=True)


if __name__ == '__main__':
    run_noise()
