import json
import os
from config import SETTINGS_FILE


class AppSettings:
    EDIT_FIELDS = (
        "crop_zoom_w", "crop_zoom_h", "crop_offset_x", "crop_offset_y",
        "rotation", "final_zoom", "final_offset_x", "final_offset_y",
        "exposure", "sharpness", "tint",
    )

    def __init__(self):
        self.film_type = "8mm"
        self.video_fps = 20
        self.output_mode = "MP4"      # MP4 or FRAMES
        self.save_location = "INTERNAL"  # INTERNAL or USB
        self.capture_tab = 4
        self.edit_settings = {}

    def toggle_film_type(self):
        self.film_type = "Super 8" if self.film_type == "8mm" else "8mm"
        self.save()

    def cycle_fps(self):
        fps_options = [10, 12, 15, 18, 20, 24, 30]
        index = fps_options.index(self.video_fps) if self.video_fps in fps_options else 4
        self.video_fps = fps_options[(index + 1) % len(fps_options)]
        self.save()

    def toggle_output_mode(self):
        self.output_mode = "FRAMES" if self.output_mode == "MP4" else "MP4"
        self.save()

    def toggle_save_location(self):
        self.save_location = "USB" if self.save_location == "INTERNAL" else "INTERNAL"
        self.save()

    def to_dict(self):
        return {
            "film_type": self.film_type,
            "video_fps": self.video_fps,
            "output_mode": self.output_mode,
            "save_location": self.save_location,
            "capture_tab": self.capture_tab,
            "edit_settings": self.edit_settings,
        }

    def load_processor_settings(self, processor):
        for name in self.EDIT_FIELDS:
            if name in self.edit_settings:
                setattr(processor, name, self.edit_settings[name])

    def save_processor_settings(self, processor):
        self.edit_settings = {
            name: getattr(processor, name)
            for name in self.EDIT_FIELDS
        }
        self.save()

    def save(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load(cls):
        settings = cls()

        if not os.path.exists(SETTINGS_FILE):
            settings.save()
            return settings

        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)

            settings.film_type = data.get("film_type", settings.film_type)
            settings.video_fps = int(data.get("video_fps", settings.video_fps))
            settings.output_mode = data.get("output_mode", settings.output_mode)
            settings.save_location = data.get("save_location", settings.save_location)
            settings.capture_tab = int(data.get("capture_tab", settings.capture_tab))
            settings.capture_tab = max(1, min(4, settings.capture_tab))
            settings.edit_settings = data.get("edit_settings", {})

        except Exception as e:
            print("Settings load error:", e)
            settings.save()

        return settings
