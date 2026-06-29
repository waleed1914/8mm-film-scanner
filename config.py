import os

SCREEN_W = 480
SCREEN_H = 320

# Defaults to the project folder on Windows and Raspberry Pi. Override it when
# needed by setting the FILM_DIGITIZER_HOME environment variable.
BASE_DIR = os.environ.get(
    "FILM_DIGITIZER_HOME",
    os.path.dirname(os.path.abspath(__file__)),
)

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CAPTURE_DIR = os.path.join(BASE_DIR, "captures")
FRAMES_DIR = os.path.join(BASE_DIR, "frames")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DUMMY_IMAGE = os.path.join(ASSETS_DIR, "dummy.jpg")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)
