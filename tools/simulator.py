#!/usr/bin/env python3
"""
Interactive Milk-V Duo XmrSigner Device Simulator
Supports both Web Browser UI and Pygame Native Window with:
- ST7735 1.8" 128x160 (or ST7789 240x240) real-time display rendering
- Virtual Hardware Joystick & Function Keys (1, 2, 3)
- Real-time Touch Screen (XPT2046) simulation via mouse clicks / taps
"""
from __future__ import annotations
import sys
import os
import io
import time
import base64
import threading
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class SimulatedDisplay:
    """Mock display backend capturing framebuffers for the simulator."""
    def __init__(self, width=128, height=160):
        self.width = width
        self.height = height
        self.current_frame = Image.new('RGB', (width, height), (0, 0, 0))
        self.frame_id = 0
        self.lock = threading.Lock()

    def ShowImage(self, image: Image.Image, x_start=0, y_start=0):
        with self.lock:
            if image.size != (self.width, self.height):
                self.current_frame = image.resize((self.width, self.height), Image.BILINEAR)
            else:
                self.current_frame = image.copy()
            self.frame_id += 1

    def clear(self, color=(0, 0, 0)):
        with self.lock:
            self.current_frame = Image.new('RGB', (self.width, self.height), color)
            self.frame_id += 1

    def get_frame_png(self) -> bytes:
        with self.lock:
            buf = io.BytesIO()
            self.current_frame.save(buf, format='PNG')
            return buf.getvalue()


class SimulatedHardwareState:
    """Simulated state for GPIO buttons & XPT2046 touch."""
    def __init__(self, width=128, height=160):
        self.width = width
        self.height = height
        self.active_keys = set()
        self.last_touch_pt: tuple[int, int] | None = None
        self.touch_active = False
        self.lock = threading.Lock()

    def press_key(self, key_code: int):
        with self.lock:
            self.active_keys.add(key_code)

    def release_key(self, key_code: int):
        with self.lock:
            self.active_keys.discard(key_code)

    def pulse_key(self, key_code: int, duration=0.15):
        def _pulse():
            self.press_key(key_code)
            time.sleep(duration)
            self.release_key(key_code)
        threading.Thread(target=_pulse, daemon=True).start()

    def touch_at(self, x: int, y: int, duration=0.15):
        with self.lock:
            self.last_touch_pt = (max(0, min(self.width - 1, x)), max(0, min(self.height - 1, y)))
            self.touch_active = True
        def _release():
            time.sleep(duration)
            with self.lock:
                self.touch_active = False
        threading.Thread(target=_release, daemon=True).start()


def patch_xmrsigner_for_simulation(sim_display: SimulatedDisplay, sim_state: SimulatedHardwareState):
    """Hooks simulator display and input into XmrSigner HAL."""
    from xmrsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants
    from xmrsigner.gui.renderer import Renderer

    orig_configure = Renderer.configure_instance

    @classmethod
    def patched_configure(cls):
        orig_configure()
        r = cls.get_instance()
        r.disp = sim_display

    Renderer.configure_instance = patched_configure
    Renderer.configure_instance()

    # Hook HardwareButtons
    hb = HardwareButtons.get_instance()

    def mock_wait_for(keys=[], check_release=True, release_keys=[]):
        while True:
            # Check touch
            if sim_state.touch_active and sim_state.last_touch_pt:
                x, y = sim_state.last_touch_pt
                if hb.touch:
                    mapped = hb.touch.get_mapped_button((x, y))
                    if mapped and mapped in keys:
                        time.sleep(0.15)
                        return mapped

            # Check buttons
            with sim_state.lock:
                for k in keys:
                    if k in sim_state.active_keys:
                        time.sleep(0.15)
                        return k
            time.sleep(0.015)

    def mock_check_for_low(key=None, keys=None):
        if key:
            keys = [key]
        with sim_state.lock:
            return any(k in sim_state.active_keys for k in (keys or []))

    hb.wait_for = mock_wait_for
    hb.check_for_low = mock_check_for_low
    hb.has_any_input = lambda: bool(sim_state.active_keys or sim_state.touch_active)


# =============================================================================
# Web Browser Interactive Simulator Server
# =============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Milk-V Duo XmrSigner Simulator</title>
    <style>
        body {
            background-color: #0d0f12;
            color: #eee;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            user-select: none;
        }
        .device {
            background: #1e2227;
            border-radius: 28px;
            padding: 24px 28px 28px 28px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.85), inset 0 2px 3px rgba(255,255,255,0.08);
            border: 2px solid #2d333b;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .header-badge {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            color: #ed5f00;
            margin-bottom: 16px;
            text-transform: uppercase;
        }
        .screen-bezel {
            background: #000;
            padding: 10px;
            border-radius: 14px;
            border: 2px solid #141619;
            box-shadow: inset 0 0 12px rgba(0,0,0,0.95);
            cursor: crosshair;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        #screen {
            display: block;
            image-rendering: pixelated;
            border-radius: 4px;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
        }
        .controls {
            display: flex;
            gap: 32px;
            margin-top: 24px;
            align-items: center;
        }
        .dpad {
            display: grid;
            grid-template-columns: repeat(3, 46px);
            grid-template-rows: repeat(3, 46px);
            gap: 4px;
        }
        .action-keys {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        button {
            background: #2d333b;
            color: #f0f6fc;
            border: 1px solid #444c56;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 0 #181b20;
            transition: all 0.05s ease;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        button:hover {
            background: #373e47;
        }
        button:active {
            transform: translateY(3px);
            box-shadow: 0 1px 0 #181b20;
            background: #ed5f00;
            color: #fff;
        }
        .btn-center { background: #444c56; }
        .action-btn { width: 76px; height: 38px; font-size: 12px; border-radius: 19px; }
        .legend {
            margin-top: 24px;
            font-size: 13px;
            color: #8b949e;
            line-height: 1.6;
            text-align: center;
        }
        kbd {
            background: #161b22;
            padding: 3px 7px;
            border-radius: 5px;
            border: 1px solid #30363d;
            color: #c9d1d9;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="device">
        <div class="header-badge">Milk-V Duo (64MB) • XmrSigner</div>
        <div class="screen-bezel">
            <img id="screen" src="/frame" width="256" height="320" alt="Display Screen">
        </div>
        <div class="controls">
            <div class="dpad">
                <div></div>
                <button onmousedown="sendKey(31)" title="Up">▲</button>
                <div></div>
                <button onmousedown="sendKey(29)" title="Left">◀</button>
                <button class="btn-center" onmousedown="sendKey(33)" title="Press / OK">●</button>
                <button onmousedown="sendKey(37)" title="Right">▶</button>
                <div></div>
                <button onmousedown="sendKey(35)" title="Down">▼</button>
                <div></div>
            </div>
            <div class="action-keys">
                <button class="action-btn" onmousedown="sendKey(40)">KEY 1</button>
                <button class="action-btn" onmousedown="sendKey(38)">KEY 2</button>
                <button class="action-btn" onmousedown="sendKey(36)">KEY 3</button>
            </div>
        </div>
    </div>
    <div class="legend">
        <b>Controls:</b> <kbd>▲</kbd> <kbd>▼</kbd> <kbd>◀</kbd> <kbd>▶</kbd> Navigate | <kbd>Enter</kbd> / <kbd>Space</kbd> Select | <kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> Function Keys | <kbd>Touch</kbd> Click on screen
    </div>

    <script>
        const screen = document.getElementById('screen');
        let framePending = false;

        function refreshFrame() {
            if (framePending) return;
            framePending = true;
            const nextImg = new Image();
            nextImg.src = '/frame?t=' + Date.now();
            nextImg.onload = () => {
                screen.src = nextImg.src;
                framePending = false;
            };
            nextImg.onerror = () => { framePending = false; };
        }
        setInterval(refreshFrame, 50);

        function sendKey(code) {
            fetch('/key?code=' + code, { method: 'POST' });
        }

        screen.addEventListener('mousedown', (e) => {
            const rect = screen.getBoundingClientRect();
            const normX = Math.floor((e.clientX - rect.left) / rect.width * 128);
            const normY = Math.floor((e.clientY - rect.top) / rect.height * 160);
            fetch(`/touch?x=${normX}&y=${normY}`, { method: 'POST' });
        });

        window.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') sendKey(31);
            else if (e.key === 'ArrowDown') sendKey(35);
            else if (e.key === 'ArrowLeft') sendKey(29);
            else if (e.key === 'ArrowRight') sendKey(37);
            else if (e.key === 'Enter' || e.key === ' ') sendKey(33);
            else if (e.key === '1' || e.key === 'q') sendKey(40);
            else if (e.key === '2' || e.key === 'w') sendKey(38);
            else if (e.key === '3' || e.key === 'e' || e.key === 'Escape') sendKey(36);
        });
    </script>
</body>
</html>
"""


class WebSimulatorServer:
    def __init__(self, display: SimulatedDisplay, state: SimulatedHardwareState, port=5000):
        self.display = display
        self.state = state
        self.port = port

    def start(self):
        parent = self
        class RequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # suppress request logging

            def do_GET(self):
                if self.path.startswith('/frame'):
                    data = parent.display.get_frame_png()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Cache-Control', 'no-cache, no-store')
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

            def do_POST(self):
                if self.path.startswith('/key'):
                    import urllib.parse
                    query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                    code = int(query.get('code', [33])[0])
                    parent.state.pulse_key(code)
                    self.send_response(200)
                    self.end_headers()
                elif self.path.startswith('/touch'):
                    import urllib.parse
                    query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                    x = int(query.get('x', [64])[0])
                    y = int(query.get('y', [80])[0])
                    parent.state.touch_at(x, y)
                    self.send_response(200)
                    self.end_headers()

        server = HTTPServer(('0.0.0.0', self.port), RequestHandler)
        print(f"\n[+] Interactive Web Simulator running at http://localhost:{self.port}")
        threading.Thread(target=server.serve_forever, daemon=True).start()


# =============================================================================
# Pygame Desktop Window Simulator
# =============================================================================

def run_pygame_window(display: SimulatedDisplay, state: SimulatedHardwareState, scale=3):
    import pygame
    pygame.init()
    pygame.display.set_caption("Milk-V Duo XmrSigner Simulator (1.8\" ST7735 + Touch)")

    win_w = display.width * scale
    win_h = display.height * scale
    screen = pygame.display.set_mode((win_w, win_h))
    clock = pygame.time.Clock()

    key_map = {
        pygame.K_UP: 31,
        pygame.K_DOWN: 35,
        pygame.K_LEFT: 29,
        pygame.K_RIGHT: 37,
        pygame.K_RETURN: 33,
        pygame.K_SPACE: 33,
        pygame.K_1: 40,
        pygame.K_2: 38,
        pygame.K_3: 36,
        pygame.K_ESCAPE: 36,
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                os._exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key in key_map:
                    state.press_key(key_map[event.key])
            elif event.type == pygame.KEYUP:
                if event.key in key_map:
                    state.release_key(key_map[event.key])
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                state.touch_at(mx // scale, my // scale)

        # Render display frame
        with display.lock:
            raw_bytes = display.current_frame.tobytes()
            surf = pygame.image.fromstring(raw_bytes, (display.width, display.height), 'RGB')
            scaled = pygame.transform.scale(surf, (win_w, win_h))
            screen.blit(scaled, (0, 0))

        pygame.display.flip()
        clock.tick(30)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Milk-V Duo XmrSigner Interactive Simulator")
    parser.add_argument('--display', choices=['ST7735', 'ST7789'], default='ST7735', help="Display model")
    parser.add_argument('--web', action='store_true', help="Run Web-only simulator (no GUI window)")
    parser.add_argument('--port', type=int, default=5000, help="Web simulator port (default: 5000)")
    parser.add_argument('--scale', type=int, default=3, help="Window scale factor")
    args = parser.parse_args()

    os.environ['DISPLAY_TYPE'] = args.display
    width, height = (128, 160) if args.display == 'ST7735' else (240, 240)

    print("=" * 65)
    print(f" Starting Milk-V Duo XmrSigner Simulator ({args.display} {width}x{height})")
    print("=" * 65)

    sim_display = SimulatedDisplay(width, height)
    sim_state = SimulatedHardwareState(width, height)

    patch_xmrsigner_for_simulation(sim_display, sim_state)

    # Start Web Server
    web_server = WebSimulatorServer(sim_display, sim_state, port=args.port)
    web_server.start()

    # Start Controller App in background thread
    from xmrsigner.controller import Controller
    controller = Controller.get_instance()

    app_thread = threading.Thread(target=controller.start, daemon=True)
    app_thread.start()

    # If Pygame available and not forced web-only, run Pygame window on main thread
    if not args.web:
        try:
            run_pygame_window(sim_display, sim_state, scale=args.scale)
        except Exception as e:
            print(f"[!] Pygame window could not be opened ({e}). Falling back to Web Simulator.")
            while True:
                time.sleep(1)
    else:
        while True:
            time.sleep(1)


if __name__ == '__main__':
    main()
