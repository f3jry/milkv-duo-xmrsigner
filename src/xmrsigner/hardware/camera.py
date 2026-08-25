from __future__ import annotations
import numpy as np
from PIL.Image import Image

from xmrsigner.hardware.interfaces import CameraInterface

CameraImplementation = None

# Try Milk-V Duo / V4L2 / OpenCV backend
try:
    from xmrsigner.hardware.milkv_camera import MilkVCamera as CameraImplementation
    print('=> backend: milkv_camera (V4L2/OpenCV/Fallback)')
except Exception:
    pass

if CameraImplementation is None:
    try:
        import picamera2
        from xmrsigner.hardware.picamera2.camera import Camera as CameraImplementation
        print('=> backend: picamera2')
    except Exception:
        try:
            import picamera
            from xmrsigner.hardware.picamera.camera import Camera as CameraImplementation
            print('=> backend: picamera')
        except Exception:
            from xmrsigner.hardware.milkv_camera import MilkVCamera as CameraImplementation
            print('=> backend: generic/milkv_camera')


class Camera(CameraInterface):

    @classmethod
    def get_instance(cls) -> 'Camera':
        return CameraImplementation.get_instance()

    def start_video_stream_mode(
        self,
        resolution: tuple[int, int] = (320, 240),
        framerate: int = 12,
        format: str = 'bgr'
    ) -> None:
        pass

    def read_video_stream(self, as_image: bool = False) -> Image | np.ndarray:
        pass

    def stop_video_stream_mode(self) -> None:
        pass

    def start_single_frame_mode(self, resolution: tuple[int, int] = (640, 480)) -> None:
        pass

    def capture_frame(self) -> Image:
        pass

    def stop_single_frame_mode(self) -> None:
        pass
