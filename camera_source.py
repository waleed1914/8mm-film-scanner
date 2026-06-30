import os

from PIL import Image

from config import DUMMY_IMAGE


class DummyCameraSource:
    def __init__(self):
        if not os.path.exists(DUMMY_IMAGE):
            raise FileNotFoundError(
                f"Dummy image not found: {DUMMY_IMAGE}"
            )

        self.image = Image.open(DUMMY_IMAGE).convert("RGB")
        self.is_real_camera = False
        self.camera_label = "DUMMY"
        print("Loaded dummy image:", DUMMY_IMAGE, self.image.size)

    def get_frame(self):
        return self.image.copy()

    def close(self):
        return None


class Picamera2Source:
    def __init__(self, size=(4056, 3040)):
        from picamera2 import Picamera2

        self.size = size
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": size, "format": "RGB888"}
        )
        self.camera.configure(config)
        self.camera.start()
        self.is_real_camera = True
        self.camera_label = "CAMERA OK"
        print("Picamera2 started:", size)

    def get_frame(self):
        frame = self.camera.capture_array("main")
        return Image.fromarray(frame, "RGB")

    def close(self):
        try:
            self.camera.stop()
        except Exception:
            pass


def create_camera_source(size=(4056, 3040)):
    try:
        return Picamera2Source(size=size)
    except Exception as error:
        print("Falling back to dummy camera source:", error)
        return DummyCameraSource()
