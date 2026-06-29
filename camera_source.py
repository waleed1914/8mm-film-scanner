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
        print("Loaded dummy image:", DUMMY_IMAGE, self.image.size)

    def get_frame(self):
        return self.image.copy()
