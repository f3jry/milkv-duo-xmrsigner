from __future__ import annotations
try:
    import picamera2
    from xmrsigner.hardware.picamera2.pivideostream import PiVideoStream2
    print('=> video backend: picamera2')
except Exception:
    import picamera
    from xmrsigner.hardware.picamera.pivideostream import PiVideoStream
    print('=> video backend: picamera')
