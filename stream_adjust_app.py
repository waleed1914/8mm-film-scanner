import os
import time
import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import customtkinter as ctk

# =====================================================
# MODERN FILM DIGITIZER PREVIEW APP
# Dummy image stream version
# Later we will replace dummy image with real camera stream
# =====================================================

SCREEN_W = 480
SCREEN_H = 320

BASE_DIR = "/home/pi/film_digitizer"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CAPTURE_DIR = os.path.join(BASE_DIR, "captures")

DUMMY_IMAGE = os.path.join(ASSETS_DIR, "dummy.jpg")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(CAPTURE_DIR, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class StreamAdjustApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Film Stream Adjust")
        self.geometry(f"{SCREEN_W}x{SCREEN_H}")
        self.resizable(False, False)

        # For real 3.5 inch LCD later, uncomment this:
        # self.attributes("-fullscreen", True)

        if not os.path.exists(DUMMY_IMAGE):
            raise FileNotFoundError(
                f"Dummy image not found: {DUMMY_IMAGE}\n"
                "Put your image at /home/pi/film_digitizer/assets/dummy.jpg"
            )

        self.original_img = Image.open(DUMMY_IMAGE).convert("RGB")

        # Adjustment values
        self.rotation = 0
        self.brightness = 0
        self.contrast = 0
        self.sharpness = 0

        # Crop / frame adjust
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Stream simulation
        self.stream_running = True
        self.last_refresh = 0

        self.preview_photo = None

        self.bind("<Escape>", lambda e: self.destroy())

        self.build_ui()
        self.update_stream()

    # =====================================================
    # IMAGE PROCESSING
    # =====================================================

    def get_processed_image(self, preview_size=(480, 215)):
        img = self.original_img.copy()

        # Rotate first
        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)

        # Apply crop/zoom
        img_w, img_h = img.size

        crop_w = int(img_w / self.zoom)
        crop_h = int(img_h / self.zoom)

        cx = img_w // 2 + self.offset_x
        cy = img_h // 2 + self.offset_y

        x1 = max(0, min(img_w - crop_w, cx - crop_w // 2))
        y1 = max(0, min(img_h - crop_h, cy - crop_h // 2))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        img = img.crop((x1, y1, x2, y2))

        # Brightness
        if self.brightness != 0:
            factor = 1.0 + (self.brightness / 20.0)
            factor = max(0.1, factor)
            img = ImageEnhance.Brightness(img).enhance(factor)

        # Contrast
        if self.contrast != 0:
            factor = 1.0 + (self.contrast / 20.0)
            factor = max(0.1, factor)
            img = ImageEnhance.Contrast(img).enhance(factor)

        # Sharpness
        if self.sharpness != 0:
            factor = 1.0 + (self.sharpness / 10.0)
            factor = max(0.1, factor)
            img = ImageEnhance.Sharpness(img).enhance(factor)

        img = img.resize(preview_size, Image.LANCZOS)
        return img

    def get_full_capture_image(self):
        """
        This returns the final processed image at higher quality.
        This is what we will save/capture.
        Later camera frame will use same function.
        """
        img = self.original_img.copy()

        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)

        img_w, img_h = img.size

        crop_w = int(img_w / self.zoom)
        crop_h = int(img_h / self.zoom)

        cx = img_w // 2 + self.offset_x
        cy = img_h // 2 + self.offset_y

        x1 = max(0, min(img_w - crop_w, cx - crop_w // 2))
        y1 = max(0, min(img_h - crop_h, cy - crop_h // 2))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        img = img.crop((x1, y1, x2, y2))

        if self.brightness != 0:
            factor = max(0.1, 1.0 + self.brightness / 20.0)
            img = ImageEnhance.Brightness(img).enhance(factor)

        if self.contrast != 0:
            factor = max(0.1, 1.0 + self.contrast / 20.0)
            img = ImageEnhance.Contrast(img).enhance(factor)

        if self.sharpness != 0:
            factor = max(0.1, 1.0 + self.sharpness / 10.0)
            img = ImageEnhance.Sharpness(img).enhance(factor)

        return img

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):
        self.main = ctk.CTkFrame(self, fg_color="#0b0f14", corner_radius=0)
        self.main.pack(fill="both", expand=True)

        # Top bar
        self.top = ctk.CTkFrame(self.main, height=32, fg_color="#111827", corner_radius=0)
        self.top.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            self.top,
            text="Film Preview Adjust",
            font=("Arial", 14, "bold"),
            text_color="white"
        )
        self.title_label.place(x=10, y=3)

        self.status_label = ctk.CTkLabel(
            self.top,
            text="STREAM",
            font=("Arial", 12, "bold"),
            text_color="#22c55e"
        )
        self.status_label.place(x=405, y=4)

        # Preview area
        self.preview_label = tk.Label(self.main, bg="black")
        self.preview_label.pack()

        # Info row
        self.info_label = ctk.CTkLabel(
            self.main,
            text="",
            font=("Arial", 10),
            text_color="#facc15"
        )
        self.info_label.place(x=8, y=34)

        # Bottom controls
        self.controls = ctk.CTkFrame(self.main, height=73, fg_color="#111827", corner_radius=0)
        self.controls.pack(fill="x")

        # Row 1 controls
        self.btn_rotate = self.btn("Rotate", self.rotate_image, 70, 28, "#2563eb")
        self.btn_rotate.place(x=5, y=5)

        self.btn_zoom_in = self.btn("Zoom +", self.zoom_in, 70, 28, "#374151")
        self.btn_zoom_in.place(x=80, y=5)

        self.btn_zoom_out = self.btn("Zoom -", self.zoom_out, 70, 28, "#374151")
        self.btn_zoom_out.place(x=155, y=5)

        self.btn_reset = self.btn("Reset", self.reset_all, 70, 28, "#7c2d12")
        self.btn_reset.place(x=230, y=5)

        self.btn_capture = self.btn("Capture", self.capture_image, 85, 28, "#16a34a")
        self.btn_capture.place(x=305, y=5)

        self.btn_exit = self.btn("Exit", self.destroy, 70, 28, "#dc2626")
        self.btn_exit.place(x=397, y=5)

        # Row 2 frame movement
        self.btn_left = self.btn("◀", self.move_left, 45, 27, "#374151")
        self.btn_left.place(x=5, y=39)

        self.btn_up = self.btn("▲", self.move_up, 45, 27, "#374151")
        self.btn_up.place(x=55, y=39)

        self.btn_down = self.btn("▼", self.move_down, 45, 27, "#374151")
        self.btn_down.place(x=105, y=39)

        self.btn_right = self.btn("▶", self.move_right, 45, 27, "#374151")
        self.btn_right.place(x=155, y=39)

        self.btn_b_minus = self.btn("B-", self.brightness_down, 45, 27, "#374151")
        self.btn_b_minus.place(x=215, y=39)

        self.btn_b_plus = self.btn("B+", self.brightness_up, 45, 27, "#2563eb")
        self.btn_b_plus.place(x=265, y=39)

        self.btn_c_minus = self.btn("C-", self.contrast_down, 45, 27, "#374151")
        self.btn_c_minus.place(x=315, y=39)

        self.btn_c_plus = self.btn("C+", self.contrast_up, 45, 27, "#2563eb")
        self.btn_c_plus.place(x=365, y=39)

        self.btn_s_plus = self.btn("S+", self.sharpness_up, 45, 27, "#2563eb")
        self.btn_s_plus.place(x=415, y=39)

    def btn(self, text, command, w, h, color):
        return ctk.CTkButton(
            self.controls,
            text=text,
            command=command,
            width=w,
            height=h,
            fg_color=color,
            hover_color="#1d4ed8",
            corner_radius=8,
            font=("Arial", 11, "bold")
        )

    # =====================================================
    # STREAM UPDATE
    # =====================================================

    def update_stream(self):
        if self.stream_running:
            img = self.get_processed_image(preview_size=(480, 215))
            self.preview_photo = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self.preview_photo)

            self.info_label.configure(
                text=(
                    f"Rot:{self.rotation}°  "
                    f"Zoom:{self.zoom:.1f}x  "
                    f"X:{self.offset_x} Y:{self.offset_y}  "
                    f"B:{self.brightness} C:{self.contrast} S:{self.sharpness}"
                )
            )

        # refresh like stream
        self.after(80, self.update_stream)

    # =====================================================
    # CONTROL FUNCTIONS
    # =====================================================

    def rotate_image(self):
        self.rotation += 90
        if self.rotation >= 360:
            self.rotation = 0

    def zoom_in(self):
        self.zoom = min(5.0, self.zoom + 0.1)

    def zoom_out(self):
        self.zoom = max(1.0, self.zoom - 0.1)

    def move_left(self):
        self.offset_x -= 40

    def move_right(self):
        self.offset_x += 40

    def move_up(self):
        self.offset_y -= 40

    def move_down(self):
        self.offset_y += 40

    def brightness_up(self):
        self.brightness = min(20, self.brightness + 1)

    def brightness_down(self):
        self.brightness = max(-20, self.brightness - 1)

    def contrast_up(self):
        self.contrast = min(20, self.contrast + 1)

    def contrast_down(self):
        self.contrast = max(-20, self.contrast - 1)

    def sharpness_up(self):
        self.sharpness = min(20, self.sharpness + 1)

    def reset_all(self):
        self.rotation = 0
        self.brightness = 0
        self.contrast = 0
        self.sharpness = 0
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def capture_image(self):
        img = self.get_full_capture_image()

        filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
        path = os.path.join(CAPTURE_DIR, filename)

        img.save(path, quality=95)

        self.status_label.configure(text="SAVED", text_color="#facc15")
        self.after(1000, lambda: self.status_label.configure(text="STREAM", text_color="#22c55e"))

        print(f"Saved capture: {path}")


if __name__ == "__main__":
    app = StreamAdjustApp()
    app.mainloop()
