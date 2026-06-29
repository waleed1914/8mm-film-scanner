import os
import time
import tkinter as tk
from datetime import datetime
from PIL import Image, ImageDraw, ImageTk, ImageEnhance
import customtkinter as ctk

# =========================
# SETTINGS
# =========================
SCREEN_W = 480
SCREEN_H = 320

BASE_DIR = "/home/pi/film_digitizer"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FRAMES_DIR = os.path.join(BASE_DIR, "frames")
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")

DUMMY_IMAGE = os.path.join(ASSETS_DIR, "dummy.jpg")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =========================
# CREATE DUMMY IMAGE
# =========================
def create_dummy_image():
    if os.path.exists(DUMMY_IMAGE):
        return

    img = Image.new("RGB", (4056, 3040), (22, 22, 26))
    draw = ImageDraw.Draw(img)

    draw.rectangle((400, 300, 3650, 2700), outline=(255, 255, 255), width=20)
    draw.rectangle((700, 600, 3350, 2400), outline=(0, 170, 255), width=14)
    draw.rectangle((1000, 850, 3050, 2200), outline=(255, 190, 40), width=10)

    draw.text((1350, 1350), "DUMMY FILM", fill=(255, 255, 255))
    draw.text((1250, 1500), "Camera preview later", fill=(180, 180, 180))

    img.save(DUMMY_IMAGE)


create_dummy_image()


# =========================
# MAIN APP
# =========================
class FilmDigitizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Film Digitizer")
        self.geometry(f"{SCREEN_W}x{SCREEN_H}")
        self.resizable(False, False)

        # Use this for real 3.5 inch LCD fullscreen
        # self.attributes("-fullscreen", True)

        self.recording = False
        self.frame_count = 0
        self.session_name = ""
        self.last_capture_time = 0

        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.brightness = 0
        self.contrast = 0
        self.sharpness = 0
        self.tint = 0

        self.film_type = "8mm"
        self.output_fps = 20
        self.motor_status = "Stopped"

        self.original_img = Image.open(DUMMY_IMAGE).convert("RGB")
        self.preview_photo = None

        self.main_frame = None

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<BackSpace>", lambda e: self.go_home())

        self.show_home()

        self.after(100, self.record_loop)

    # =========================
    # BASIC HELPERS
    # =========================
    def clear(self):
        if self.main_frame:
            self.main_frame.destroy()

        self.main_frame = ctk.CTkFrame(self, fg_color="#0b0f14", corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

    def top_bar(self, title):
        bar = ctk.CTkFrame(self.main_frame, height=34, fg_color="#111827", corner_radius=0)
        bar.pack(fill="x")

        label = ctk.CTkLabel(
            bar,
            text=title,
            font=("Arial", 15, "bold"),
            text_color="white"
        )
        label.place(x=12, y=4)

        if self.recording:
            rec = ctk.CTkLabel(
                bar,
                text="● REC",
                font=("Arial", 13, "bold"),
                text_color="#ff3333"
            )
            rec.place(x=398, y=5)

    def make_button(self, parent, text, command, w=120, h=45, color="#2563eb"):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=w,
            height=h,
            fg_color=color,
            hover_color="#1d4ed8",
            corner_radius=14,
            font=("Arial", 14, "bold")
        )

    def get_preview_image(self, size=(480, 210)):
        img = self.original_img.copy()
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

        # Dummy picture settings
        if self.brightness != 0:
            img = ImageEnhance.Brightness(img).enhance(1 + self.brightness / 20)

        if self.contrast != 0:
            img = ImageEnhance.Contrast(img).enhance(1 + self.contrast / 20)

        img = img.resize(size, Image.LANCZOS)
        return img

    def save_frame(self):
        if not self.session_name:
            return

        session_dir = os.path.join(FRAMES_DIR, self.session_name)
        os.makedirs(session_dir, exist_ok=True)

        img = self.get_preview_image(size=(480, 240))
        path = os.path.join(session_dir, f"frame_{self.frame_count:06d}.jpg")
        img.save(path)

        self.frame_count += 1

    def record_loop(self):
        if self.recording:
            now = time.time()
            if now - self.last_capture_time >= 0.5:
                self.save_frame()
                self.last_capture_time = now

        self.after(100, self.record_loop)

    def start_recording(self):
        self.session_name = datetime.now().strftime("scan_%Y%m%d_%H%M%S")
        self.frame_count = 0
        self.recording = True
        self.last_capture_time = time.time()
        self.show_capture()

    def stop_recording(self):
        self.recording = False

        file_path = os.path.join(RECORDINGS_DIR, self.session_name + "_dummy_recording.txt")
        with open(file_path, "w") as f:
            f.write("Dummy recording created\n")
            f.write(f"Session: {self.session_name}\n")
            f.write(f"Frames captured: {self.frame_count}\n")

        self.session_name = ""
        self.show_capture()

    def go_home(self):
        self.show_home()

    # =========================
    # PAGES
    # =========================
    def show_home(self):
        self.clear()

        title = ctk.CTkLabel(
            self.main_frame,
            text="FILM DIGITIZER",
            font=("Arial", 30, "bold"),
            text_color="white"
        )
        title.pack(pady=(32, 0))

        sub = ctk.CTkLabel(
            self.main_frame,
            text="Raspberry Pi Modern UI",
            font=("Arial", 13),
            text_color="#9ca3af"
        )
        sub.pack(pady=(0, 25))

        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack()

        self.make_button(btn_frame, "Capture", self.show_capture, 125, 70).grid(row=0, column=0, padx=7)
        self.make_button(btn_frame, "Menu", self.show_menu, 125, 70, "#374151").grid(row=0, column=1, padx=7)
        self.make_button(btn_frame, "Settings", self.show_settings, 125, 70, "#374151").grid(row=0, column=2, padx=7)

        info = ctk.CTkLabel(
            self.main_frame,
            text="Dummy image mode • Camera streaming will be added later",
            font=("Arial", 11),
            text_color="#facc15"
        )
        info.pack(pady=(35, 0))

    def show_capture(self):
        self.clear()
        self.top_bar("Capture")

        img = self.get_preview_image(size=(480, 205))
        self.preview_photo = ImageTk.PhotoImage(img)

        preview = tk.Label(self.main_frame, image=self.preview_photo, bg="black")
        preview.pack()

        overlay_text = f"Zoom {self.zoom:.1f}x"
        if self.recording:
            overlay_text += f"  •  Frames: {self.frame_count}"

        info = ctk.CTkLabel(
            self.main_frame,
            text=overlay_text,
            font=("Arial", 11),
            text_color="#facc15"
        )
        info.place(x=10, y=38)

        bottom = ctk.CTkFrame(self.main_frame, height=78, fg_color="#111827", corner_radius=0)
        bottom.pack(fill="x")

        if self.recording:
            self.make_button(bottom, "STOP", self.stop_recording, 90, 42, "#dc2626").place(x=8, y=18)
        else:
            self.make_button(bottom, "RECORD", self.start_recording, 90, 42, "#16a34a").place(x=8, y=18)

        self.make_button(bottom, "Frame", self.show_frame_adjust, 80, 42, "#2563eb").place(x=105, y=18)
        self.make_button(bottom, "Picture", self.show_picture, 90, 42, "#2563eb").place(x=192, y=18)
        self.make_button(bottom, "Back", self.show_home, 80, 42, "#374151").place(x=390, y=18)

    def show_frame_adjust(self):
        self.clear()
        self.top_bar("Frame Adjust")

        img = self.get_preview_image(size=(480, 190))
        self.preview_photo = ImageTk.PhotoImage(img)

        preview = tk.Label(self.main_frame, image=self.preview_photo, bg="black")
        preview.pack()

        controls = ctk.CTkFrame(self.main_frame, fg_color="#111827", corner_radius=0)
        controls.pack(fill="both", expand=True)

        ctk.CTkLabel(
            controls,
            text=f"Zoom: {self.zoom:.1f}x   X:{self.offset_x} Y:{self.offset_y}",
            font=("Arial", 11),
            text_color="#facc15"
        ).pack(pady=(3, 0))

        row = ctk.CTkFrame(controls, fg_color="transparent")
        row.pack(pady=3)

        self.make_button(row, "◀", self.move_left, 50, 32, "#374151").grid(row=0, column=0, padx=3)
        self.make_button(row, "▲", self.move_up, 50, 32, "#374151").grid(row=0, column=1, padx=3)
        self.make_button(row, "▼", self.move_down, 50, 32, "#374151").grid(row=0, column=2, padx=3)
        self.make_button(row, "▶", self.move_right, 50, 32, "#374151").grid(row=0, column=3, padx=3)
        self.make_button(row, "Zoom +", self.zoom_in, 75, 32, "#2563eb").grid(row=0, column=4, padx=3)
        self.make_button(row, "Zoom -", self.zoom_out, 75, 32, "#2563eb").grid(row=0, column=5, padx=3)

        self.make_button(controls, "Back", self.show_capture, 90, 30, "#374151").pack(pady=2)

    def move_left(self):
        self.offset_x -= 40
        self.show_frame_adjust()

    def move_right(self):
        self.offset_x += 40
        self.show_frame_adjust()

    def move_up(self):
        self.offset_y -= 40
        self.show_frame_adjust()

    def move_down(self):
        self.offset_y += 40
        self.show_frame_adjust()

    def zoom_in(self):
        self.zoom = min(4.0, self.zoom + 0.1)
        self.show_frame_adjust()

    def zoom_out(self):
        self.zoom = max(1.0, self.zoom - 0.1)
        self.show_frame_adjust()

    def show_picture(self):
        self.clear()
        self.top_bar("Picture Settings")

        panel = ctk.CTkFrame(self.main_frame, fg_color="#111827", corner_radius=18)
        panel.pack(padx=18, pady=16, fill="both", expand=True)

        self.setting_row(panel, "Brightness", self.brightness, self.inc_brightness, self.dec_brightness, 0)
        self.setting_row(panel, "Contrast", self.contrast, self.inc_contrast, self.dec_contrast, 1)
        self.setting_row(panel, "Sharpness", self.sharpness, self.inc_sharpness, self.dec_sharpness, 2)
        self.setting_row(panel, "Tint", self.tint, self.inc_tint, self.dec_tint, 3)

        self.make_button(panel, "Reset", self.reset_picture, 100, 32, "#dc2626").place(x=105, y=205)
        self.make_button(panel, "Back", self.show_capture, 100, 32, "#374151").place(x=220, y=205)

    def setting_row(self, parent, name, value, plus_cmd, minus_cmd, row):
        y = 18 + row * 45

        ctk.CTkLabel(
            parent,
            text=name,
            font=("Arial", 13, "bold"),
            text_color="white"
        ).place(x=20, y=y)

        ctk.CTkLabel(
            parent,
            text=str(value),
            font=("Arial", 13, "bold"),
            text_color="#facc15"
        ).place(x=210, y=y)

        self.make_button(parent, "-", minus_cmd, 42, 28, "#374151").place(x=270, y=y - 3)
        self.make_button(parent, "+", plus_cmd, 42, 28, "#2563eb").place(x=320, y=y - 3)

    def inc_brightness(self):
        self.brightness += 1
        self.show_picture()

    def dec_brightness(self):
        self.brightness -= 1
        self.show_picture()

    def inc_contrast(self):
        self.contrast += 1
        self.show_picture()

    def dec_contrast(self):
        self.contrast -= 1
        self.show_picture()

    def inc_sharpness(self):
        self.sharpness += 1
        self.show_picture()

    def dec_sharpness(self):
        self.sharpness -= 1
        self.show_picture()

    def inc_tint(self):
        self.tint += 1
        self.show_picture()

    def dec_tint(self):
        self.tint -= 1
        self.show_picture()

    def reset_picture(self):
        self.brightness = 0
        self.contrast = 0
        self.sharpness = 0
        self.tint = 0
        self.show_picture()

    def show_menu(self):
        self.clear()
        self.top_bar("Menu")

        panel = ctk.CTkFrame(self.main_frame, fg_color="#111827", corner_radius=18)
        panel.pack(padx=18, pady=18, fill="both", expand=True)

        self.make_button(panel, "My Recordings", self.show_recordings, 300, 38).pack(pady=(18, 8))
        self.make_button(panel, "Rewind", self.rewind_motor, 300, 38, "#374151").pack(pady=8)
        self.make_button(panel, "Fast Forward", self.forward_motor, 300, 38, "#374151").pack(pady=8)
        self.make_button(panel, "Motor Stop", self.stop_motor, 300, 38, "#dc2626").pack(pady=8)

        ctk.CTkLabel(
            panel,
            text=f"Motor: {self.motor_status}",
            font=("Arial", 12),
            text_color="#facc15"
        ).pack(pady=4)

        self.make_button(panel, "Back", self.show_home, 120, 32, "#374151").pack(pady=4)

    def rewind_motor(self):
        self.motor_status = "Rewinding"
        self.show_menu()

    def forward_motor(self):
        self.motor_status = "Fast Forward"
        self.show_menu()

    def stop_motor(self):
        self.motor_status = "Stopped"
        self.show_menu()

    def show_recordings(self):
        self.clear()
        self.top_bar("My Recordings")

        files = []
        for f in os.listdir(RECORDINGS_DIR):
            if f.endswith(".txt") or f.endswith(".mp4"):
                files.append(f)

        files = sorted(files, reverse=True)

        panel = ctk.CTkScrollableFrame(self.main_frame, fg_color="#111827", corner_radius=18)
        panel.pack(padx=18, pady=12, fill="both", expand=True)

        if not files:
            ctk.CTkLabel(
                panel,
                text="No recordings yet",
                font=("Arial", 16, "bold"),
                text_color="#9ca3af"
            ).pack(pady=50)
        else:
            for f in files:
                ctk.CTkLabel(
                    panel,
                    text=f,
                    font=("Arial", 12),
                    text_color="white",
                    anchor="w"
                ).pack(fill="x", padx=8, pady=4)

        self.make_button(self.main_frame, "Back", self.show_menu, 100, 30, "#374151").pack(pady=(0, 8))

    def show_settings(self):
        self.clear()
        self.top_bar("Settings")

        panel = ctk.CTkFrame(self.main_frame, fg_color="#111827", corner_radius=18)
        panel.pack(padx=18, pady=18, fill="both", expand=True)

        self.make_button(
            panel,
            f"Film Type: {self.film_type}",
            self.toggle_film_type,
            320,
            36
        ).pack(pady=(20, 8))

        self.make_button(
            panel,
            f"Output FPS: {self.output_fps}",
            self.change_fps,
            320,
            36,
            "#374151"
        ).pack(pady=8)

        self.make_button(
            panel,
            "Erase Recordings",
            self.erase_recordings,
            320,
            36,
            "#dc2626"
        ).pack(pady=8)

        self.make_button(
            panel,
            "Factory Reset",
            self.factory_reset,
            320,
            36,
            "#7c2d12"
        ).pack(pady=8)

        self.make_button(panel, "Back", self.show_home, 120, 32, "#374151").pack(pady=6)

    def toggle_film_type(self):
        self.film_type = "Super 8" if self.film_type == "8mm" else "8mm"
        self.show_settings()

    def change_fps(self):
        self.output_fps += 1
        if self.output_fps > 30:
            self.output_fps = 10
        self.show_settings()

    def erase_recordings(self):
        for f in os.listdir(RECORDINGS_DIR):
            path = os.path.join(RECORDINGS_DIR, f)
            if os.path.isfile(path):
                os.remove(path)
        self.show_settings()

    def factory_reset(self):
        self.film_type = "8mm"
        self.output_fps = 20
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.brightness = 0
        self.contrast = 0
        self.sharpness = 0
        self.tint = 0
        self.motor_status = "Stopped"
        self.show_settings()


if __name__ == "__main__":
    app = FilmDigitizerApp()
    app.mainloop()
