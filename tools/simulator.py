#!/usr/bin/env python3
"""
Interactive Milk-V Duo XmrSigner Device Simulator
Supports both Web Browser UI and Pygame Native Window with:
- ST7735 1.8" 128x160 (or ST7789 240x240) real-time display rendering
- Event Queue-based virtual hardware Joystick & Function Keys (1, 2, 3)
- Real-time Touch Screen (XPT2046) simulation via mouse clicks / taps
"""
from __future__ import annotations
import sys
import os
import io
import time
import queue
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
    """Thread-safe event queue for virtual hardware keys & touch."""
    def __init__(self, width=128, height=160):
        self.width = width
        self.height = height
        self.event_queue = queue.Queue()

    def push_key(self, key_code: int):
        self.event_queue.put(key_code)

    def touch_at(self, x: int, y: int):
        from xmrsigner.hardware.buttons import HardwareButtonsConstants as C
        # Coordinate mapping for 128x160:
        # Top-Nav / Back (y < 26) -> KEY_LEFT / BACK
        # Top quarter (26 <= y < 55) -> KEY_UP
        # Bottom quarter (y > 135) -> KEY_DOWN (or KEY1/KEY3 on corners)
        # Left (x < 30) -> KEY_LEFT
        # Right (x > 98) -> KEY_RIGHT
        # Center (30 <= x <= 98, 55 <= y <= 135) -> KEY_PRESS
        if y < 26:
            self.push_key(C.KEY_LEFT)
        elif y < 55:
            self.push_key(C.KEY_UP)
        elif y > 135:
            if x < 40:
                self.push_key(C.KEY1)
            elif x > 88:
                self.push_key(C.KEY3)
            else:
                self.push_key(C.KEY_DOWN)
        elif x < 30:
            self.push_key(C.KEY_LEFT)
        elif x > 98:
            self.push_key(C.KEY_RIGHT)
        else:
            self.push_key(C.KEY_PRESS)


def patch_xmrsigner_for_simulation(sim_display: SimulatedDisplay, sim_state: SimulatedHardwareState):
    """Hooks simulator display and input into XmrSigner HAL."""
    from xmrsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants
    from xmrsigner.gui.renderer import Renderer

    # 1. Patch HardwareButtons class methods
    def mock_wait_for(self, keys=[], check_release=True, release_keys=[]):
        while True:
            try:
                key = sim_state.event_queue.get(timeout=0.03)
                if not keys or key in keys:
                    return key
            except queue.Empty:
                pass

    def mock_check_for_low(self, key=None, keys=None):
        return False

    HardwareButtons.wait_for = mock_wait_for
    HardwareButtons.check_for_low = mock_check_for_low
    HardwareButtons.has_any_input = lambda self: not sim_state.event_queue.empty()

    # 2. Patch Renderer to stream frames directly into sim_display
    orig_show = Renderer.show_image
    def patched_show_image(self, image=None, alpha_overlay=None, show_direct=False):
        orig_show(self, image, alpha_overlay, show_direct)
        sim_display.ShowImage(self.canvas)

    Renderer.show_image = patched_show_image


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
        * { box-sizing: border-box; }
        body {
            background-color: #0b0d10;
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
            background: #181b20;
            border-radius: 30px;
            padding: 24px 30px 30px 30px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.9), inset 0 1px 2px rgba(255,255,255,0.12);
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
            padding: 12px;
            border-radius: 16px;
            border: 2px solid #141619;
            box-shadow: inset 0 0 15px rgba(0,0,0,0.95);
            cursor: crosshair;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        #screen {
            display: block;
            image-rendering: pixelated;
            border-radius: 4px;
            box-shadow: 0 0 12px rgba(0,0,0,0.7);
        }
        .controls {
            display: flex;
            gap: 36px;
            margin-top: 24px;
            align-items: center;
        }
        .dpad {
            display: grid;
            grid-template-columns: repeat(3, 50px);
            grid-template-rows: repeat(3, 50px);
            gap: 5px;
        }
        .action-keys {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        button {
            background: #252a32;
            color: #f0f6fc;
            border: 1px solid #3d4450;
            border-radius: 12px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 0 #121418;
            transition: all 0.04s ease;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        button:hover {
            background: #323842;
        }
        button:active {
            transform: translateY(3px);
            box-shadow: 0 1px 0 #121418;
            background: #ed5f00;
            color: #fff;
        }
        .btn-center { background: #3d4450; font-size: 18px; }
        .action-btn { width: 84px; height: 42px; font-size: 13px; border-radius: 21px; }
        .legend {
            margin-top: 24px;
            font-size: 13px;
            color: #8b949e;
            line-height: 1.6;
            text-align: center;
        }
        kbd {
            background: #161b22;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid #30363d;
            color: #c9d1d9;
            font-family: monospace;
            font-size: 12px;
        }
        .touch-indicator {
            position: absolute;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: rgba(237, 95, 0, 0.7);
            border: 2px solid #fff;
            transform: translate(-50%, -50%);
            pointer-events: none;
            display: none;
        }
    </style>
</head>
<body>
    <div class="device">
        <div class="header-badge">Milk-V Duo 64MB • XmrSigner</div>
        <div class="screen-bezel" style="position: relative;">
            <img id="screen" src="/frame" width="256" height="320" alt="Display Screen">
            <div id="touch-dot" class="touch-indicator"></div>
        </div>
        <div class="controls">
            <div class="dpad">
                <div></div>
                <button id="btn-up" onclick="sendKey(31)" title="Up">▲</button>
                <div></div>
                <button id="btn-left" onclick="sendKey(29)" title="Left">◀</button>
                <button id="btn-press" class="btn-center" onclick="sendKey(33)" title="Press / OK">●</button>
                <button id="btn-right" onclick="sendKey(37)" title="Right">▶</button>
                <div></div>
                <button id="btn-down" onclick="sendKey(35)" title="Down">▼</button>
                <div></div>
            </div>
            <div class="action-keys">
                <button id="btn-k1" class="action-btn" onclick="sendKey(40)">KEY 1</button>
                <button id="btn-k2" class="action-btn" onclick="sendKey(38)">KEY 2</button>
                <button id="btn-k3" class="action-btn" onclick="sendKey(36)">KEY 3</button>
            </div>
        </div>
    </div>
    <div class="legend">
        <b>Controls:</b> <kbd>▲</kbd> <kbd>▼</kbd> <kbd>◀</kbd> <kbd>▶</kbd> Navigate | <kbd>Enter</kbd> / <kbd>Space</kbd> Select | <kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> Function Keys | <kbd>Touch</kbd> Click on screen
    </div>

    <script>
        const screen = document.getElementById('screen');
        const touchDot = document.getElementById('touch-dot');
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
        setInterval(refreshFrame, 45);

        function sendKey(code) {
            fetch('/key?code=' + code, { method: 'POST' });
        }

        screen.addEventListener('click', (e) => {
            const rect = screen.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;

            // Show touch indicator
            touchDot.style.left = (clickX + 12) + 'px';
            touchDot.style.top = (clickY + 12) + 'px';
            touchDot.style.display = 'block';
            setTimeout(() => { touchDot.style.display = 'none'; }, 200);

            const normX = Math.floor(clickX / rect.width * 128);
            const normY = Math.floor(clickY / rect.height * 160);
            fetch(`/touch?x=${normX}&y=${normY}`, { method: 'POST' });
        });

        window.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') { e.preventDefault(); sendKey(31); }
            else if (e.key === 'ArrowDown') { e.preventDefault(); sendKey(35); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); sendKey(29); }
            else if (e.key === 'ArrowRight') { e.preventDefault(); sendKey(37); }
            else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sendKey(33); }
            else if (e.key === '1' || e.key === 'q') { sendKey(40); }
            else if (e.key === '2' || e.key === 'w') { sendKey(38); }
            else if (e.key === '3' || e.key === 'e' || e.key === 'Escape') { sendKey(36); }
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
                pass

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
                import urllib.parse
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if self.path.startswith('/key'):
                    code = int(query.get('code', [33])[0])
                    parent.state.push_key(code)
                elif self.path.startswith('/touch'):
                    x = int(query.get('x', [64])[0])
                    y = int(query.get('y', [80])[0])
                    parent.state.touch_at(x, y)
                self.send_response(200)
                self.send_header('Content-Length', '0')
                self.end_headers()

        server = HTTPServer(('0.0.0.0', self.port), RequestHandler)
        print(f"\n[+] Interactive Web Simulator running at http://localhost:{self.port}")
        threading.Thread(target=server.serve_forever, daemon=True).start()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Milk-V Duo XmrSigner Interactive Simulator")
    parser.add_argument('--display', choices=['ST7735', 'ST7789'], default='ST7735', help="Display model")
    parser.add_argument('--port', type=int, default=5000, help="Web simulator port (default: 5000)")
    args = parser.parse_args()

    os.environ['DISPLAY_TYPE'] = args.display
    width, height = (128, 160) if args.display == 'ST7735' else (240, 240)

    print("=" * 65)
    print(f" Starting Milk-V Duo XmrSigner Simulator ({args.display} {width}x{height})")
    print("=" * 65)

    sim_display = SimulatedDisplay(width, height)
    sim_state = SimulatedHardwareState(width, height)

    patch_xmrsigner_for_simulation(sim_display, sim_state)

    web_server = WebSimulatorServer(sim_display, sim_state, port=args.port)
    web_server.start()

    from xmrsigner.controller import Controller
    controller = Controller.get_instance()

    app_thread = threading.Thread(target=controller.start, daemon=True)
    app_thread.start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
