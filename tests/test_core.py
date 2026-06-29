import json
import os
import re
import tempfile
import time
import unittest

from PIL import Image, ImageDraw

import app_settings
import storage
from app_settings import AppSettings
from image_processor import ImageProcessor


class FakeSettings:
    save_location = "INTERNAL"


class SettingsTests(unittest.TestCase):
    def test_settings_and_image_edits_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            old_file = app_settings.SETTINGS_FILE
            app_settings.SETTINGS_FILE = os.path.join(temp_dir, "settings.json")
            try:
                settings = AppSettings()
                settings.film_type = "Super 8"
                settings.video_fps = 18
                settings.capture_tab = 3

                processor = ImageProcessor()
                processor.crop_zoom_w = 2.25
                processor.rotation = 270
                processor.exposure = 4
                settings.save_processor_settings(processor)

                loaded = AppSettings.load()
                restored = ImageProcessor()
                loaded.load_processor_settings(restored)

                self.assertEqual(loaded.film_type, "Super 8")
                self.assertEqual(loaded.video_fps, 18)
                self.assertEqual(loaded.capture_tab, 3)
                self.assertEqual(restored.crop_zoom_w, 2.25)
                self.assertEqual(restored.rotation, 270)
                self.assertEqual(restored.exposure, 4)

                with open(app_settings.SETTINGS_FILE, encoding="utf-8") as file:
                    json.load(file)
            finally:
                app_settings.SETTINGS_FILE = old_file


class ImageProcessorTests(unittest.TestCase):
    @staticmethod
    def sample_image():
        image = Image.new("RGB", (320, 240), "#203040")
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 30, 280, 210), fill="#E0B040")
        draw.line((0, 0, 319, 239), fill="white", width=4)
        return image

    def test_every_preview_has_exact_requested_size(self):
        processor = ImageProcessor()
        image = self.sample_image()
        expected = (432, 166)

        self.assertEqual(processor.make_crop_preview(image, expected).size, expected)
        self.assertEqual(
            processor.make_rotate_zoom_preview(image, expected).size, expected
        )
        self.assertEqual(
            processor.make_picture_preview(image, expected).size, expected
        )

    def test_crop_rotation_zoom_and_color_produce_valid_output(self):
        processor = ImageProcessor()
        image = self.sample_image()

        processor.crop_zoom_w = 1.75
        processor.crop_zoom_h = 1.30
        processor.crop_offset_x = 9999
        processor.crop_offset_y = -9999
        processor.rotation = 90
        processor.final_zoom = 1.4
        processor.exposure = 3
        processor.sharpness = 2
        processor.tint = -4

        x1, y1, x2, y2 = processor.get_crop_box(image)
        self.assertGreaterEqual(x1, 0)
        self.assertGreaterEqual(y1, 0)
        self.assertLessEqual(x2, image.width)
        self.assertLessEqual(y2, image.height)

        output = processor.make_final_image(image)
        self.assertEqual(output.mode, "RGB")
        self.assertGreater(output.width, 0)
        self.assertGreater(output.height, 0)

    def test_adjustment_limits_are_enforced(self):
        processor = ImageProcessor()
        for _ in range(100):
            processor.exposure_up()
            processor.sharpness_down()
            processor.tint_up()
            processor.final_zoom_out()

        self.assertEqual(processor.exposure, 30)
        self.assertEqual(processor.sharpness, -30)
        self.assertEqual(processor.tint, 30)
        self.assertEqual(processor.final_zoom, 1.0)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_paths = (
            storage.BASE_DIR,
            storage.FRAMES_DIR,
            storage.RECORDINGS_DIR,
        )
        storage.BASE_DIR = self.temp.name
        storage.FRAMES_DIR = os.path.join(self.temp.name, "frames")
        storage.RECORDINGS_DIR = os.path.join(self.temp.name, "recordings")

    def tearDown(self):
        storage.BASE_DIR, storage.FRAMES_DIR, storage.RECORDINGS_DIR = self.old_paths
        self.temp.cleanup()

    def test_sessions_are_unique_and_frames_do_not_overwrite(self):
        first = storage.start_session(FakeSettings(), prefix="recording")
        second = storage.start_session(FakeSettings(), prefix="recording")
        self.assertNotEqual(first["name"], second["name"])
        self.assertRegex(
            first["name"],
            r"^recording_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[0-9a-f]{8}$",
        )

        image = Image.new("RGB", (64, 48), "navy")
        first_path = storage.save_frame_to_session(image, first)
        second_path = storage.save_frame_to_session(image, first)

        self.assertNotEqual(first_path, second_path)
        self.assertTrue(os.path.isfile(first_path))
        self.assertTrue(os.path.isfile(second_path))
        self.assertEqual(first["frame_count"], 2)

    def test_real_ffmpeg_export_and_recording_index(self):
        if not storage.find_ffmpeg():
            self.skipTest("FFmpeg is not installed")

        session = storage.start_session(FakeSettings(), prefix="recording")
        for index in range(3):
            image = Image.new("RGB", (65, 49), (index * 60, 80, 120))
            storage.save_frame_to_session(image, session)

        output = storage.make_mp4_from_session(session, 12)
        self.assertIsNotNone(output)
        self.assertTrue(os.path.isfile(output))
        self.assertGreater(os.path.getsize(output), 0)
        self.assertIn(output, storage.list_recordings(FakeSettings()))
        self.assertFalse(os.path.isdir(session["frames_dir"]))

    def test_frame_sessions_are_indexed_as_saved_items(self):
        session = storage.start_session(FakeSettings(), prefix="frames")
        image = Image.new("RGB", (80, 60), "orange")
        storage.save_frame_to_session(image, session)
        storage.save_frame_to_session(image, session)

        items = storage.list_saved_items(FakeSettings())
        frame_items = [item for item in items if item["type"] == "FRAMES"]

        self.assertEqual(len(frame_items), 1)
        self.assertEqual(frame_items[0]["path"], session["frames_dir"])
        self.assertEqual(frame_items[0]["frame_count"], 2)

    def test_copy_recording_to_usb_creates_recordings_copy(self):
        recordings_dir = os.path.join(self.temp.name, "recordings")
        os.makedirs(recordings_dir, exist_ok=True)
        source = os.path.join(recordings_dir, "sample.mp4")
        usb_root = os.path.join(self.temp.name, "usb")
        os.makedirs(usb_root, exist_ok=True)

        with open(source, "wb") as file:
            file.write(b"demo-video")

        original_find_usb_base = storage.find_usb_base
        storage.find_usb_base = lambda: usb_root
        try:
            copied = storage.copy_recording_to_usb(source)
        finally:
            storage.find_usb_base = original_find_usb_base

        self.assertIsNotNone(copied)
        self.assertTrue(os.path.isfile(copied))
        self.assertEqual(os.path.basename(copied), "sample.mp4")

    def test_copy_frame_session_to_usb_and_delete_helpers(self):
        session = storage.start_session(FakeSettings(), prefix="frames")
        image = Image.new("RGB", (40, 30), "green")
        storage.save_frame_to_session(image, session)

        usb_root = os.path.join(self.temp.name, "usb")
        os.makedirs(usb_root, exist_ok=True)

        original_find_usb_base = storage.find_usb_base
        storage.find_usb_base = lambda: usb_root
        try:
            copied = storage.copy_frame_session_to_usb(session["frames_dir"])
        finally:
            storage.find_usb_base = original_find_usb_base

        self.assertIsNotNone(copied)
        self.assertTrue(os.path.isdir(copied))
        self.assertTrue(storage.delete_frame_session(session["frames_dir"]))
        self.assertFalse(os.path.isdir(session["frames_dir"]))

        recording_path = os.path.join(self.temp.name, "recordings", "delete_me.mp4")
        os.makedirs(os.path.dirname(recording_path), exist_ok=True)
        with open(recording_path, "wb") as file:
            file.write(b"demo-video")
        self.assertTrue(storage.delete_recording(recording_path))
        self.assertFalse(os.path.exists(recording_path))


class UiSmokeTests(unittest.TestCase):
    def test_complete_dummy_recording_workflow(self):
        if not storage.find_ffmpeg():
            self.skipTest("FFmpeg is not installed")

        from ui.app import FilmDigitizerApp

        with tempfile.TemporaryDirectory() as temp_dir:
            old_paths = (
                storage.BASE_DIR,
                storage.FRAMES_DIR,
                storage.RECORDINGS_DIR,
            )
            storage.BASE_DIR = temp_dir
            storage.FRAMES_DIR = os.path.join(temp_dir, "frames")
            storage.RECORDINGS_DIR = os.path.join(temp_dir, "recordings")

            app = FilmDigitizerApp()
            try:
                app.withdraw()
                app.show_home()
                app.show_menu()
                app.show_recordings()
                app.show_frames()
                app.show_settings()
                app.show_capture()
                for tab in range(1, 5):
                    app.capture_step = tab
                    app.draw_capture_controls()
                app.update_idletasks()

                app.settings.output_mode = "MP4"
                app.capture_step = 4
                app.start_capturing()

                app.last_auto_capture = 0
                app.fake_capture_loop()
                app.last_auto_capture = 0
                app.fake_capture_loop()
                app.stop_capturing()

                deadline = time.time() + 30
                while app.encoding and time.time() < deadline:
                    app.update()
                    time.sleep(0.02)

                self.assertFalse(app.encoding, "Background encoding timed out")
                recordings = storage.list_recordings(app.settings)
                self.assertEqual(len(recordings), 1)
                self.assertGreater(os.path.getsize(recordings[0]), 0)

                frame_sessions = storage.list_frame_sessions(app.settings)
                self.assertEqual(len(frame_sessions), 0)

                app.settings.output_mode = "FRAMES"
                app.start_capturing()
                app.last_auto_capture = 0
                app.fake_capture_loop()
                app.stop_capturing()
                frame_sessions = storage.list_frame_sessions(app.settings)
                self.assertEqual(len(frame_sessions), 1)

                app.show_recordings()
                app.play_recording(recordings[0])
                playback_deadline = time.time() + 2
                while time.time() < playback_deadline:
                    app.update()
                    time.sleep(0.02)
                self.assertEqual(app.page, "player")
                app.stop_video_and_show_frames()

                app.show_frame_session(frame_sessions[0])
                app.update_idletasks()
                self.assertEqual(app.page, "frame_viewer")
                self.assertGreater(len(app.frame_session_images), 0)
                self.assertTrue("/" in app.status_label.cget("text"))
            finally:
                app.close_app()
                (
                    storage.BASE_DIR,
                    storage.FRAMES_DIR,
                    storage.RECORDINGS_DIR,
                ) = old_paths


if __name__ == "__main__":
    unittest.main()
