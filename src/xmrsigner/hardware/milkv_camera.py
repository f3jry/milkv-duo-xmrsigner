from __future__ import annotations
"""
Milk-V Duo Camera Implementation (V4L2 / OpenCV / Fallback)
Supports CV1800B MIPI-CSI camera (/dev/video0) and USB UVC cameras on Milk-V Duo.
"""
import os
import time
import numpy as np
from PIL import Image
from threading import Thread, Lock
from xmrsigner.hardware.interfaces import CameraInterface
from xmrsigner.models.settings import Settings, Setting

try:
    import cv2
except ImportError:
    cv2 = None


class MilkVCamera(CameraInterface):
    _instance = None
    _video_stream = None
    _camera_rotation = 0

    @classmethod
    def get_instance(cls) -> CameraInterface:
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._instance._video_stream = None
            cls._instance._single_frame_cap = None
        cls._instance._camera_rotation = int(Settings.get_instance().get_value(Setting.CAMERA_ROTATION))
        return cls._instance

    def start_video_stream_mode(
        self,
        resolution: tuple[int, int] = (320, 240),
        framerate: int = 15,
        format: str = 'bgr'
    ) -> None:
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        self._video_stream = MilkVVideoStream(resolution=resolution, framerate=framerate)
        self._video_stream.start()

    def read_video_stream(self, as_image=False) -> Image.Image | np.ndarray:
        if not self._video_stream:
            # Fallback black dummy frame
            dummy = np.zeros((240, 320, 3), dtype=np.uint8)
            return Image.fromarray(dummy, 'RGB') if as_image else dummy
        frame = self._video_stream.read()
        if frame is None:
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
        if not as_image:
            return frame
        # Convert BGR to RGB
        rgb_frame = frame[:, :, ::-1] if frame.ndim == 3 else frame
        img = Image.fromarray(rgb_frame.astype('uint8'), 'RGB')
        if self._camera_rotation:
            img = img.rotate(self._camera_rotation)
        return img

    def stop_video_stream_mode(self) -> None:
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None

    def start_single_frame_mode(self, resolution=(640, 480)) -> None:
        self.stop_video_stream_mode()
        if cv2 is not None:
            for dev_idx in [0, 1, 2]:
                if os.path.exists(f"/dev/video{dev_idx}"):
                    self._single_frame_cap = cv2.VideoCapture(dev_idx)
                    self._single_frame_cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                    self._single_frame_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
                    break

    def capture_frame(self) -> Image.Image:
        if self._single_frame_cap is not None and self._single_frame_cap.isOpened():
            ret, frame = self._single_frame_cap.read()
            if ret and frame is not None:
                rgb = frame[:, :, ::-1]
                img = Image.fromarray(rgb.astype('uint8'), 'RGB')
                if self._camera_rotation:
                    img = img.rotate(self._camera_rotation)
                return img
        # Return fallback test pattern image
        img = Image.new('RGB', (320, 240), color=(30, 30, 40))
        return img

    def stop_single_frame_mode(self) -> None:
        if self._single_frame_cap is not None:
            self._single_frame_cap.release()
            self._single_frame_cap = None


class MilkVVideoStream:
    def __init__(self, resolution=(320, 240), framerate=15):
        self.resolution = resolution
        self.framerate = framerate
        self.stream = None
        self.frame = None
        self.stopped = False
        self.lock = Lock()

        if cv2 is not None:
            for dev_idx in [0, 1, 2]:
                if os.path.exists(f"/dev/video{dev_idx}"):
                    try:
                        self.stream = cv2.VideoCapture(dev_idx)
                        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
                        self.stream.set(cv2.CAP_PROP_FPS, framerate)
                        break
                    except Exception:
                        pass

    def start(self):
        self.stopped = False
        t = Thread(target=self.update, args=(), daemon=True)
        t.start()
        return self

    def update(self):
        while not self.stopped:
            if self.stream is not None and self.stream.isOpened():
                ret, frame = self.stream.read()
                if ret and frame is not None:
                    with self.lock:
                        self.frame = frame
            else:
                # Generate blank/dummy frame
                with self.lock:
                    self.frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
            time.sleep(1.0 / max(self.framerate, 1))

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)

    def stop(self):
        self.stopped = True
        if self.stream is not None:
            try:
                self.stream.release()
            except Exception:
                pass
            self.stream = None
