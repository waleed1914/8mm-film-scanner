import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk

# Allow this file to run directly from VS Code Code Runner as well as through
# the project entry point (main.py).
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageTk
import customtkinter as ctk

from config import SCREEN_W, SCREEN_H
from image_processor import ImageProcessor
from camera_source import create_camera_source
from app_settings import AppSettings
from storage import (
    start_session,
    save_frame_to_session,
    save_single_frame,
    make_mp4_from_session,
    list_recordings,
    list_frame_sessions,
    find_ffmpeg,
    copy_recording_to_usb,
    copy_frame_session_to_usb,
    delete_recording,
    delete_frame_session,
)
from ui.icons import make_icon
from ui.theme import (
    ACCENT, ACCENT_HOVER, APP_BG, SIDEBAR_BG, TOPBAR_BG,
    PANEL_BG, PANEL_ALT, BUTTON_BG, BUTTON_HOVER,
    TEXT, TEXT_MUTED, SUCCESS, WARNING, DANGER,
)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class FilmDigitizerApp(ctk.CTk):
    PREVIEW_SIZE = (432, 166)

    def __init__(self):
        super().__init__()

        self.title("CARRERO-8")
        self.geometry(f"{SCREEN_W}x{SCREEN_H}")
        self.resizable(False, False)
        self.overrideredirect(True)

        # For 3.5 inch LCD fullscreen later:
        # self.attributes("-fullscreen", True)

        self.camera = create_camera_source(size=(4056, 3040))
        self.processor = ImageProcessor()
        self.settings = AppSettings.load()
        self.settings.load_processor_settings(self.processor)

        self.page = "home"
        self.capture_step = self.settings.capture_tab
        self.capturing = False
        self.encoding = False
        self.motor_status = "Stopped"

        self.capture_session = None
        self.last_auto_capture = 0
        self.encode_results = queue.Queue()
        self.save_results = queue.Queue()
        self.progress_updates = queue.Queue()
        self.running = True
        self.stream_after_id = None
        self.video_frame_queue = queue.Queue(maxsize=3)
        self.video_thread = None
        self.video_process = None
        self.video_stop_event = threading.Event()
        self.video_current_path = None
        self.frame_session_images = []
        self.frame_session_index = 0

        self.preview_photo = None
        self.preview_label = None
        self.info_label = None
        self.controls = None
        self.busy_overlay = None
        self.busy_title_label = None
        self.busy_detail_label = None
        self.busy_percent_label = None
        self.busy_progress = None
        self.busy_active = False
        self.icons = {
            name: make_icon(name)
            for name in (
                "logo", "home", "camera", "menu", "settings", "back",
                "next", "rewind", "forward", "stop", "play", "save",
                "edit", "reset", "film", "crop", "frame", "color", "delete"
            )
        }
        self.brand_icons = {
            "top": make_icon("logo", size=24),
            "side": make_icon("logo", size=22),
            "hero": make_icon("logo", size=58),
        }
        self.dark_icons = {
            name: make_icon(name, color=APP_BG)
            for name in self.icons
        }

        self.bind("<Escape>", lambda e: self.close_app())
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        self.build_base()
        self.show_splash()
        self.update_stream()

    def close_app(self):
        self.stop_video_playback()
        if self.busy_active:
            self.status_label.configure(text="PLEASE WAIT", text_color=WARNING)
            return
        if self.capturing:
            self.stop_capturing()
            return
        if self.encoding:
            self.status_label.configure(text="PLEASE WAIT", text_color=WARNING)
            return

        self.running = False
        try:
            self.camera.close()
        except Exception:
            pass
        if self.stream_after_id is not None:
            try:
                self.after_cancel(self.stream_after_id)
            except (ValueError, tk.TclError):
                pass
        self.destroy()

    def navigation_allowed(self):
        if self.busy_active:
            self.status_label.configure(text="PLEASE WAIT", text_color=WARNING)
            return False
        if self.video_current_path:
            self.status_label.configure(text="STOP VIDEO", text_color=WARNING)
            return False
        if self.capturing:
            self.status_label.configure(text="STOP FIRST", text_color=WARNING)
            return False
        return True

    # =====================================================
    # SPLASH SCREEN
    # =====================================================

    def show_splash(self):
        self.page = "splash"
        self.clear_content()
        self.hide_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="START")
        self.status_label.configure(text="BOOTING", text_color=WARNING)

        splash = ctk.CTkFrame(
            self.content,
            width=432,
            height=272,
            fg_color=APP_BG,
            corner_radius=0,
        )
        splash.place(x=0, y=0)

        ctk.CTkLabel(
            splash,
            text="",
            image=make_icon("logo", size=92),
        ).place(x=170, y=38)

        ctk.CTkLabel(
            splash,
            text="CARRERO-8",
            width=432,
            anchor="center",
            font=("Arial", 34, "bold"),
            text_color=TEXT,
        ).place(x=0, y=138)

        ctk.CTkLabel(
            splash,
            text="CINE FILM SCANNER",
            width=432,
            anchor="center",
            font=("Arial", 14, "bold"),
            text_color=TEXT_MUTED,
        ).place(x=0, y=182)

        ctk.CTkLabel(
            splash,
            text="Initializing camera and controls...",
            width=432,
            anchor="center",
            font=("Arial", 11),
            text_color=ACCENT,
        ).place(x=0, y=226)

        self.after(1500, self.finish_splash)

    def finish_splash(self):
        if self.page != "splash":
            return
        self.show_home()

    # =====================================================
    # BASE UI
    # =====================================================

    def build_base(self):
        self.main = ctk.CTkFrame(
            self,
            fg_color=APP_BG,
            corner_radius=0
        )
        self.main.pack(fill="both", expand=True)

        self.top = ctk.CTkFrame(
            self.main,
            height=34,
            fg_color=TOPBAR_BG,
            corner_radius=0
        )
        self.top.pack(fill="x", padx=(48, 0))

        self.title_label = ctk.CTkLabel(
            self.top,
            text=" CARRERO-8",
            image=self.brand_icons["top"],
            compound="left",
            font=("Arial", 12, "bold"),
            text_color=TEXT
        )
        self.title_label.place(x=8, y=3)

        self.mid_label = ctk.CTkLabel(
            self.top,
            text="HOME",
            font=("Arial", 12, "bold"),
            text_color=ACCENT
        )
        self.mid_label.place(x=205, y=5)

        self.status_label = ctk.CTkLabel(
            self.top,
            text="READY",
            font=("Arial", 12, "bold"),
            text_color=SUCCESS
        )
        self.status_label.place(x=365, y=5)

        self.camera_status_dot = ctk.CTkFrame(
            self.top, width=10, height=10, fg_color=DANGER, corner_radius=5
        )
        self.camera_status_dot.place(x=334, y=9)

        self.arduino_status_dot = ctk.CTkFrame(
            self.top, width=10, height=10, fg_color=DANGER, corner_radius=5
        )
        self.arduino_status_dot.place(x=349, y=9)

        self.sidebar = ctk.CTkFrame(
            self.main, width=48, fg_color=SIDEBAR_BG, corner_radius=0
        )
        self.sidebar.place(x=0, y=0, relheight=1)

        self.side_logo = ctk.CTkLabel(
            self.sidebar, text="", image=self.brand_icons["side"]
        )
        self.side_logo.place(x=13, y=8)

        nav_items = (
            ("home", self.show_home, 60),
            ("camera", self.show_capture, 108),
            ("menu", self.show_menu, 156),
            ("settings", self.show_settings, 204),
        )
        for icon_name, command, y in nav_items:
            ctk.CTkButton(
                self.sidebar, text="", image=self.icons[icon_name],
                command=command, width=36, height=36,
                fg_color="transparent", hover_color=PANEL_BG,
                corner_radius=8
            ).place(x=6, y=y)

        self.content = ctk.CTkFrame(
            self.main,
            fg_color=APP_BG,
            corner_radius=0
        )
        self.content.pack(fill="both", expand=True, padx=(48, 0))
        self.build_busy_overlay()

    def refresh_hardware_status(self):
        self.camera_status_dot.configure(
            fg_color=SUCCESS if self.camera_detected() else DANGER
        )
        self.arduino_status_dot.configure(
            fg_color=SUCCESS if self.arduino_detected() else DANGER
        )

    def show_standard_brand(self):
        self.title_label.place(x=8, y=3)
        self.side_logo.place(x=13, y=8)

    def hide_standard_brand(self):
        self.title_label.place_forget()
        self.side_logo.place_forget()

    def build_busy_overlay(self):
        self.busy_overlay = ctk.CTkFrame(
            self.main,
            width=SCREEN_W,
            height=SCREEN_H,
            fg_color=APP_BG,
            corner_radius=0,
        )

        card = ctk.CTkFrame(
            self.busy_overlay,
            width=320,
            height=150,
            fg_color=PANEL_BG,
            corner_radius=16,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        self.busy_title_label = ctk.CTkLabel(
            card,
            text="PLEASE WAIT",
            font=("Arial", 18, "bold"),
            text_color=TEXT,
        )
        self.busy_title_label.place(x=82, y=20)

        self.busy_detail_label = ctk.CTkLabel(
            card,
            text="Saving your file...",
            font=("Arial", 11),
            text_color=TEXT_MUTED,
        )
        self.busy_detail_label.place(x=82, y=50)

        self.busy_progress = ctk.CTkProgressBar(
            card,
            width=240,
            height=16,
            progress_color=ACCENT,
            fg_color=PANEL_ALT,
        )
        self.busy_progress.place(x=40, y=88)
        self.busy_progress.set(0)

        self.busy_percent_label = ctk.CTkLabel(
            card,
            text="0%",
            font=("Arial", 16, "bold"),
            text_color=ACCENT,
        )
        self.busy_percent_label.place(x=138, y=113)

    def show_busy_overlay(self, title, detail, percent=0):
        self.busy_active = True
        self.busy_title_label.configure(text=title)
        self.busy_detail_label.configure(text=detail)
        self.update_busy_progress(percent)
        self.busy_overlay.place(x=0, y=0)
        self.busy_overlay.lift()

    def update_busy_progress(self, percent, detail=None):
        percent = max(0, min(100, int(percent)))
        if detail is not None:
            self.busy_detail_label.configure(text=detail)
        self.busy_progress.set(percent / 100)
        self.busy_percent_label.configure(text=f"{percent}%")

    def hide_busy_overlay(self):
        self.busy_active = False
        if self.busy_overlay is not None:
            self.busy_overlay.place_forget()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def btn(self, parent, text, command, x, y, w=90, h=40,
            color=BUTTON_BG, icon=None):
        # Safety: if color accidentally comes into height position
        if isinstance(h, str):
            color = h
            h = 28

        b = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=w,
            height=h,
            fg_color=color,
            hover_color=ACCENT_HOVER if color == ACCENT else BUTTON_HOVER,
            corner_radius=8,
            font=("Arial", 10, "bold"),
            text_color=APP_BG if color == ACCENT else TEXT,
            image=(
                self.dark_icons.get(icon)
                if icon and color == ACCENT
                else self.icons.get(icon) if icon else None
            ),
            compound="left"
        )
        b.place(x=x, y=y)
        return b

    def fit_image_to_preview(self, image):
        target_w, target_h = self.PREVIEW_SIZE
        fitted = image.convert("RGB")
        fitted.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), "black")
        offset_x = (target_w - fitted.width) // 2
        offset_y = (target_h - fitted.height) // 2
        canvas.paste(fitted, (offset_x, offset_y))
        return canvas

    def camera_detected(self):
        return bool(getattr(self.camera, "is_real_camera", False))

    def arduino_detected(self):
        try:
            from serial.tools import list_ports
        except Exception:
            return False

        keywords = ("arduino", "usb serial", "ch340", "cp210", "ft232")
        for port in list_ports.comports():
            text = " ".join(
                filter(None, [port.device, port.description, port.manufacturer])
            ).lower()
            if any(keyword in text for keyword in keywords):
                return True
        return False

    def hardware_dot(self, parent, x, y, width, label, detected):
        dot_color = SUCCESS if detected else DANGER
        row = ctk.CTkFrame(
            parent,
            width=width,
            height=22,
            fg_color="transparent",
            corner_radius=0,
        )
        row.place(x=x, y=y)
        ctk.CTkFrame(
            row,
            width=12,
            height=12,
            fg_color=dot_color,
            corner_radius=6,
        ).place(x=0, y=5)
        ctk.CTkLabel(
            row,
            text=label,
            width=width - 18,
            anchor="w",
            font=("Arial", 10, "bold"),
            text_color=TEXT_MUTED if detected else TEXT,
        ).place(x=18, y=1)

    # =====================================================
    # HOME PAGE
    # =====================================================

    def show_home(self):
        if not self.navigation_allowed():
            return
        self.page = "home"
        self.clear_content()
        self.refresh_hardware_status()

        self.mid_label.configure(text="HOME")
        self.status_label.configure(text="READY", text_color=SUCCESS)
        self.show_standard_brand()

        brand_row = ctk.CTkFrame(
            self.content,
            width=400,
            height=62,
            fg_color="transparent",
            corner_radius=0,
        )
        brand_row.place(x=16, y=12)

        ctk.CTkLabel(
            brand_row,
            text="",
            image=self.brand_icons["hero"],
        ).place(x=64, y=0)

        title = ctk.CTkLabel(
            brand_row,
            text="CARRERO-8",
            width=250,
            anchor="center",
            font=("Arial", 28, "bold"),
            text_color=TEXT
        )
        title.place(x=118, y=6)

        subtitle = ctk.CTkLabel(
            brand_row,
            text="CINE FILM SCANNER",
            width=250,
            anchor="center",
            font=("Arial", 11, "bold"),
            text_color=TEXT_MUTED,
        )
        subtitle.place(x=118, y=38)

        status_items = (
            ("FILM", self.settings.film_type),
            ("RATE", f"{self.settings.video_fps} FPS"),
            ("OUTPUT", self.settings.output_mode),
        )
        for index, (label, value) in enumerate(status_items):
            card = ctk.CTkFrame(
                self.content, width=125, height=48,
                fg_color=PANEL_BG, corner_radius=8
            )
            card.place(x=18 + index * 135, y=84)
            ctk.CTkLabel(
                card, text=label, width=109, anchor="w",
                font=("Arial", 9, "bold"), text_color=TEXT_MUTED
            ).place(x=8, y=3)
            ctk.CTkLabel(
                card, text=value, width=109, anchor="w",
                font=("Arial", 12, "bold"), text_color=ACCENT
            ).place(x=8, y=22)

        self.btn(
            self.content,
            "Capture",
            self.show_capture,
            18, 143, 125, 65, ACCENT, "camera"
        )

        self.btn(
            self.content,
            "Menu",
            self.show_menu,
            153, 143, 125, 65, BUTTON_BG, "menu"
        )

        self.btn(
            self.content,
            "Settings",
            self.show_settings,
            288, 143, 125, 65, BUTTON_BG, "settings"
        )

        note = ctk.CTkLabel(
            self.content,
            text="DEMO STREAM  •  CAMERA MODULE READY TO CONNECT",
            font=("Arial", 11),
            text_color=WARNING
        )
        note.place(x=62, y=236)

    # =====================================================
    # CAPTURE PAGE
    # =====================================================

    def show_capture(self):
        self.page = "capture"
        self.show_standard_brand()
        self.refresh_hardware_status()
        self.build_capture_page()

    def build_capture_page(self):
        self.clear_content()

        self.preview_label = tk.Label(
            self.content,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        self.preview_label.pack()

        self.controls = ctk.CTkFrame(
            self.content,
            height=116,
            fg_color=PANEL_ALT,
            corner_radius=0
        )
        self.controls.pack(fill="x")

        self.draw_capture_controls()

    def clear_controls(self):
        if self.controls is None:
            return

        for widget in self.controls.winfo_children():
            widget.destroy()

    def cbtn(self, text, command, x, y, w=60, h=28,
             color=BUTTON_BG, icon=None):
        if isinstance(h, str):
            color = h
            h = 28

        return self.btn(self.controls, text, command, x, y, w, h, color, icon)

    def draw_capture_controls(self):
        self.clear_controls()
        self.draw_capture_tabs()

        if self.capture_step == 1:
            self.draw_crop_controls()

        elif self.capture_step == 2:
            self.draw_rotate_zoom_controls()

        elif self.capture_step == 3:
            self.draw_picture_controls()

        elif self.capture_step == 4:
            self.draw_final_controls()

    def draw_capture_tabs(self):
        tabs = (
            (1, "Crop", "crop"),
            (2, "Frame", "frame"),
            (3, "Color", "color"),
            (4, "Capture", "camera"),
        )
        for index, label, icon in tabs:
            active = index == self.capture_step
            self.cbtn(
                label,
                lambda selected=index: self.set_capture_tab(selected),
                4 + (index - 1) * 107,
                3,
                103,
                28,
                ACCENT if active else PANEL_BG,
                icon,
            )

    def apply_edit(self, command):
        command()
        self.settings.save_processor_settings(self.processor)

    # =====================================================
    # STEP 1: CROP
    # =====================================================

    def draw_crop_controls(self):
        actions = (
            ("W−", self.processor.crop_width_smaller, 4, 36),
            ("W+", self.processor.crop_width_bigger, 52, 36),
            ("H−", self.processor.crop_height_smaller, 100, 36),
            ("H+", self.processor.crop_height_bigger, 148, 36),
            ("◀", self.processor.crop_move_left, 4, 72),
            ("▲", self.processor.crop_move_up, 52, 72),
            ("▼", self.processor.crop_move_down, 100, 72),
            ("▶", self.processor.crop_move_right, 148, 72),
        )
        for text, command, x, y in actions:
            self.cbtn(text, lambda cmd=command: self.apply_edit(cmd), x, y, 44, 30)

        self.cbtn(
            "Reset All", lambda: self.apply_edit(self.processor.reset_all),
            205, 36, 105, 30, DANGER, "reset"
        )
        self.cbtn("Home", self.show_home, 315, 72, 110, 30, BUTTON_BG, "home")

    # =====================================================
    # STEP 2: ROTATE / ZOOM
    # =====================================================

    def draw_rotate_zoom_controls(self):
        actions = (
            ("↶ 90°", self.processor.rotate_left, 4, 36, 67),
            ("90° ↷", self.processor.rotate_right, 75, 36, 67),
            ("Zoom +", self.processor.final_zoom_in, 150, 36, 70),
            ("Zoom −", self.processor.final_zoom_out, 224, 36, 70),
            ("◀", self.processor.final_move_left, 4, 72, 44),
            ("▲", self.processor.final_move_up, 52, 72, 44),
            ("▼", self.processor.final_move_down, 100, 72, 44),
            ("▶", self.processor.final_move_right, 148, 72, 44),
        )
        for text, command, x, y, width in actions:
            self.cbtn(
                text, lambda cmd=command: self.apply_edit(cmd),
                x, y, width, 30
            )
        self.cbtn("Home", self.show_home, 315, 72, 110, 30, BUTTON_BG, "home")

    # =====================================================
    # STEP 3: PICTURE SETTINGS
    # =====================================================

    def draw_picture_controls(self):
        actions = (
            ("Exp −", self.processor.exposure_down, 4),
            ("Exp +", self.processor.exposure_up, 61),
            ("Sharp −", self.processor.sharpness_down, 118),
            ("Sharp +", self.processor.sharpness_up, 183),
            ("Tint −", self.processor.tint_down, 248),
            ("Tint +", self.processor.tint_up, 307),
        )
        widths = (53, 53, 61, 61, 55, 55)
        for (text, command, x), width in zip(actions, widths):
            self.cbtn(
                text, lambda cmd=command: self.apply_edit(cmd),
                x, 36, width, 30
            )
        self.cbtn(
            "Reset Color", lambda: self.apply_edit(self.processor.reset_picture),
            4, 72, 120, 30, DANGER, "reset"
        )
        self.cbtn("Home", self.show_home, 315, 72, 110, 30, BUTTON_BG, "home")

    # =====================================================
    # STEP 4: FINAL CAPTURE
    # =====================================================

    def draw_final_controls(self):
        if self.encoding:
            self.cbtn("SAVING…", lambda: None, 4, 44, 188, 50, WARNING, "save")
        elif self.capturing:
            self.cbtn("STOP", self.stop_capturing, 4, 44, 95, 50, DANGER, "stop")
        else:
            self.cbtn("START", self.start_capturing, 4, 44, 95, 50, ACCENT, "play")

        if not self.encoding:
            self.cbtn("Frame", self.capture_once, 104, 44, 88, 50, BUTTON_BG, "save")

        self.cbtn("Forward", self.motor_forward, 197, 36, 96, 30, BUTTON_BG, "forward")
        self.cbtn("Reverse", self.motor_backward, 298, 36, 96, 30, BUTTON_BG, "rewind")
        self.cbtn("Motor Stop", self.motor_stop, 197, 72, 197, 30, DANGER, "stop")

        self.cbtn("", self.show_home, 399, 54, 29, 38, BUTTON_BG, "home")

    # =====================================================
    # STEP NAVIGATION
    # =====================================================

    def set_capture_tab(self, tab):
        self.capture_step = tab
        self.settings.capture_tab = tab
        self.settings.save()
        self.draw_capture_controls()

    # =====================================================
    # MENU PAGE
    # =====================================================

    def show_menu(self):
        if not self.navigation_allowed():
            return
        self.page = "menu"
        self.clear_content()
        self.show_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="MENU")
        self.status_label.configure(text="READY", text_color=SUCCESS)

        panel = ctk.CTkFrame(
            self.content,
            width=400,
            height=246,
            fg_color=PANEL_BG,
            corner_radius=14
        )
        panel.place(x=16, y=8)

        self.btn(panel, "Recordings", self.show_recordings, 40, 20, 320, 38,
                 ACCENT, "film")
        self.btn(panel, "Frames", self.show_frames, 40, 68, 320, 38,
                 BUTTON_BG, "frame")
        self.btn(panel, "Rewind", self.motor_backward, 40, 116, 320, 38,
                 BUTTON_BG, "rewind")
        self.btn(panel, "Fast Forward", self.motor_forward, 40, 164, 320, 38,
                 BUTTON_BG, "forward")
        self.btn(panel, "Motor Stop", self.motor_stop, 40, 206, 320, 36,
                 DANGER, "stop")

        self.btn(self.content, "Back", self.show_home, 166, 258, 100, 26,
                 BUTTON_BG, "back")

    def show_recordings(self):
        if not self.navigation_allowed():
            return
        self.page = "recordings"
        self.clear_content()
        self.show_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="RECORDINGS")
        self.status_label.configure(text="READY", text_color=SUCCESS)

        recordings = list_recordings(self.settings)

        if not recordings:
            label = ctk.CTkLabel(
                self.content,
                text="No MP4 recordings yet",
                image=self.icons["film"],
                compound="top",
                font=("Arial", 14, "bold"),
                text_color=TEXT
            )
            label.place(x=130, y=90)
        else:
            for index, path in enumerate(recordings[:5]):
                row = ctk.CTkFrame(
                    self.content, width=400, height=39,
                    fg_color=PANEL_BG, corner_radius=8
                )
                row.place(x=16, y=12 + index * 44)

                name = os.path.basename(path)
                size_mb = os.path.getsize(path) / (1024 * 1024)
                ctk.CTkLabel(
                    row,
                    text=f"{name[:20]}  -  {size_mb:.1f} MB",
                    width=220,
                    anchor="w",
                    font=("Arial", 10, "bold"),
                    text_color=TEXT,
                ).place(x=10, y=7)

                self.btn(
                    row, "", lambda p=path: self.play_recording(p),
                    278, 5, 34, 29, ACCENT, "play"
                )
                self.btn(
                    row, "", lambda p=path: self.save_recording_to_usb(p),
                    315, 5, 34, 29, BUTTON_BG, "save"
                )
                self.btn(
                    row, "", lambda p=path: self.delete_recording_item(p),
                    352, 5, 34, 29, DANGER, "delete"
                )

        self.btn(self.content, "Back", self.show_menu, 166, 235, 100, 35,
                 BUTTON_BG, "back")

    def show_frames(self):
        if not self.navigation_allowed():
            return
        self.page = "frames"
        self.clear_content()
        self.show_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="FRAMES")
        self.status_label.configure(text="READY", text_color=SUCCESS)

        sessions = list_frame_sessions(self.settings)

        if not sessions:
            label = ctk.CTkLabel(
                self.content,
                text="No frame sessions yet",
                image=self.icons["frame"],
                compound="top",
                font=("Arial", 14, "bold"),
                text_color=TEXT
            )
            label.place(x=135, y=90)
        else:
            for index, path in enumerate(sessions[:5]):
                row = ctk.CTkFrame(
                    self.content, width=400, height=39,
                    fg_color=PANEL_BG, corner_radius=8
                )
                row.place(x=16, y=12 + index * 44)

                frame_count = len([
                    name for name in os.listdir(path)
                    if name.lower().endswith(".jpg")
                ])
                name = os.path.basename(path)
                ctk.CTkLabel(
                    row,
                    text=f"{name[:18]}  -  {frame_count} frames",
                    width=220,
                    anchor="w",
                    font=("Arial", 10, "bold"),
                    text_color=TEXT,
                ).place(x=10, y=7)

                self.btn(
                    row, "", lambda p=path: self.show_frame_session(p),
                    278, 5, 34, 29, ACCENT, "frame"
                )
                self.btn(
                    row, "", lambda p=path: self.save_frame_session_to_usb(p),
                    315, 5, 34, 29, BUTTON_BG, "save"
                )
                self.btn(
                    row, "", lambda p=path: self.delete_frame_session_item(p),
                    352, 5, 34, 29, DANGER, "delete"
                )

        self.btn(self.content, "Back", self.show_menu, 166, 235, 100, 35,
                 BUTTON_BG, "back")

    def save_recording_to_usb(self, path):
        saved_path = copy_recording_to_usb(path)
        if saved_path:
            print("Recording copied to USB:", saved_path)
            self.status_label.configure(text="USB SAVED", text_color=SUCCESS)
            self.after(
                900,
                lambda: self.status_label.configure(text="READY", text_color=SUCCESS)
            )
        else:
            self.status_label.configure(text="NO USB", text_color=DANGER)
            self.after(
                900,
                lambda: self.status_label.configure(text="READY", text_color=SUCCESS)
            )

    def delete_recording_item(self, path):
        if delete_recording(path):
            self.status_label.configure(text="DELETED", text_color=WARNING)
            self.show_recordings()
        else:
            self.status_label.configure(text="DELETE ERR", text_color=DANGER)

    def save_frame_session_to_usb(self, path):
        saved_path = copy_frame_session_to_usb(path)
        if saved_path:
            print("Frame session copied to USB:", saved_path)
            self.status_label.configure(text="USB SAVED", text_color=SUCCESS)
            self.after(
                900,
                lambda: self.status_label.configure(text="READY", text_color=SUCCESS)
            )
        else:
            self.status_label.configure(text="NO USB", text_color=DANGER)
            self.after(
                900,
                lambda: self.status_label.configure(text="READY", text_color=SUCCESS)
            )

    def delete_frame_session_item(self, path):
        if delete_frame_session(path):
            self.status_label.configure(text="DELETED", text_color=WARNING)
            self.show_frames()
        else:
            self.status_label.configure(text="DELETE ERR", text_color=DANGER)

    # =====================================================
    # SETTINGS PAGE
    # =====================================================

    def show_settings(self):
        if not self.navigation_allowed():
            return
        self.page = "settings"
        self.clear_content()
        self.show_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="SETTINGS")
        self.status_label.configure(text="READY", text_color=SUCCESS)

        panel = ctk.CTkFrame(
            self.content,
            width=400,
            height=235,
            fg_color=PANEL_BG,
            corner_radius=14
        )
        panel.place(x=16, y=14)

        self.btn(
            panel,
            f"Film Type: {self.settings.film_type}",
            self.change_film_type,
            40,
            15,
            320,
            34,
            ACCENT,
            "film"
        )

        self.btn(
            panel,
            f"Video FPS: {self.settings.video_fps}",
            self.change_fps,
            40,
            58,
            320,
            34,
            BUTTON_BG
        )

        output_text = "High Definition MP4" if self.settings.output_mode == "MP4" else "Frames Only"

        self.btn(
            panel,
            f"Output: {output_text}",
            self.change_output_mode,
            40,
            101,
            320,
            34,
            BUTTON_BG
        )

        save_text = "USB Drive" if self.settings.save_location == "USB" else "Internal Storage"

        self.btn(
            panel,
            f"Save To: {save_text}",
            self.change_save_location,
            40,
            144,
            320,
            34,
            BUTTON_BG
        )

        self.btn(
            panel,
            "Reset Edit Settings",
            self.reset_edit_settings,
            40,
            187,
            150,
            34,
            DANGER,
            "reset"
        )

        self.btn(
            panel,
            "Back",
            self.show_home,
            210,
            187,
            150,
            34,
            BUTTON_BG,
            "back"
        )

    def change_film_type(self):
        self.settings.toggle_film_type()
        self.show_settings()

    def change_fps(self):
        self.settings.cycle_fps()
        self.show_settings()

    def change_output_mode(self):
        self.settings.toggle_output_mode()
        self.show_settings()

    def change_save_location(self):
        self.settings.toggle_save_location()
        self.show_settings()

    def reset_edit_settings(self):
        self.processor.reset_all()
        self.settings.save_processor_settings(self.processor)
        self.status_label.configure(text="RESET", text_color=WARNING)

        self.after(
            800,
            lambda: self.status_label.configure(text="READY", text_color=SUCCESS)
        )

        self.show_settings()

    # =====================================================
    # PLAYBACK + FRAME VIEWER
    # =====================================================

    def play_recording(self, path):
        if self.capturing or self.encoding:
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            self.status_label.configure(text="NO FFMPEG", text_color=DANGER)
            return

        self.stop_video_playback()
        self.video_current_path = path
        self.page = "player"
        self.clear_content()
        self.show_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="PLAYER")
        self.status_label.configure(text="PLAYING", text_color=WARNING)

        self.preview_label = tk.Label(
            self.content,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        self.preview_label.pack()

        panel = ctk.CTkFrame(
            self.content,
            height=116,
            fg_color=PANEL_ALT,
            corner_radius=0
        )
        panel.pack(fill="x")

        name = os.path.basename(path)
        ctk.CTkLabel(
            panel,
            text=name[:34],
            width=300,
            anchor="w",
            font=("Arial", 10, "bold"),
            text_color=TEXT,
        ).place(x=10, y=10)

        self.btn(panel, "Stop", self.stop_video_and_return, 10, 52, 94, 36, DANGER, "stop")
        self.btn(panel, "Recordings", self.stop_video_and_show_recordings, 112, 52, 100, 36, BUTTON_BG, "film")
        self.btn(panel, "Menu", self.stop_video_and_show_menu, 220, 52, 94, 36, BUTTON_BG, "menu")
        self.btn(panel, "Home", self.stop_video_and_show_home, 322, 52, 94, 36, BUTTON_BG, "home")

        self.status_label.configure(text="LOADING", text_color=WARNING)
        self.update_idletasks()
        self.after(40, lambda p=path: self.start_video_playback(p))

    def start_video_playback(self, path):
        if self.page != "player" or self.video_current_path != path:
            return

        self.video_stop_event.clear()
        self.video_thread = threading.Thread(
            target=self.video_playback_loop,
            args=(path,),
            daemon=True,
        )
        self.video_thread.start()

    def video_playback_loop(self, path):
        ffmpeg = find_ffmpeg()
        frame_size = self.PREVIEW_SIZE[0] * self.PREVIEW_SIZE[1] * 3
        cmd = [
            ffmpeg,
            "-i", path,
            "-vf",
            (
                f"scale={self.PREVIEW_SIZE[0]}:{self.PREVIEW_SIZE[1]}"
                ":force_original_aspect_ratio=decrease,"
                f"pad={self.PREVIEW_SIZE[0]}:{self.PREVIEW_SIZE[1]}"
                ":(ow-iw)/2:(oh-ih)/2:black"
            ),
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-loglevel", "error",
            "-"
        ]

        try:
            self.video_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            while not self.video_stop_event.is_set():
                chunk = self.video_process.stdout.read(frame_size)
                if len(chunk) < frame_size:
                    break

                image = Image.frombytes("RGB", self.PREVIEW_SIZE, chunk)
                try:
                    self.video_frame_queue.put_nowait(image)
                except queue.Full:
                    try:
                        self.video_frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self.video_frame_queue.put_nowait(image)
        except OSError as error:
            print("Video playback failed:", error)
        finally:
            if self.video_process is not None:
                try:
                    self.video_process.kill()
                except OSError:
                    pass
                for stream in (self.video_process.stdout, self.video_process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except OSError:
                            pass
                try:
                    self.video_process.wait(timeout=1)
                except (subprocess.TimeoutExpired, OSError):
                    pass
                self.video_process = None

    def stop_video_playback(self):
        self.video_stop_event.set()
        process = self.video_process
        if process is not None:
            try:
                process.kill()
            except OSError:
                pass
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
            try:
                process.wait(timeout=1)
            except (subprocess.TimeoutExpired, OSError):
                pass
            self.video_process = None
        self.video_current_path = None

        while not self.video_frame_queue.empty():
            try:
                self.video_frame_queue.get_nowait()
            except queue.Empty:
                break

    def stop_video_and_return(self):
        self.stop_video_playback()
        self.status_label.configure(text="READY", text_color=SUCCESS)

    def stop_video_and_show_recordings(self):
        self.stop_video_playback()
        self.show_recordings()

    def stop_video_and_show_menu(self):
        self.stop_video_playback()
        self.show_menu()

    def stop_video_and_show_frames(self):
        self.stop_video_playback()
        self.show_frames()

    def stop_video_and_show_home(self):
        self.stop_video_playback()
        self.show_home()

    def show_frame_session(self, path):
        if self.capturing or self.encoding:
            return

        images = sorted([
            os.path.join(path, name)
            for name in os.listdir(path)
            if name.lower().endswith(".jpg")
        ])
        if not images:
            self.status_label.configure(text="NO FRAMES", text_color=DANGER)
            return

        self.frame_session_images = images
        self.frame_session_index = 0
        self.page = "frame_viewer"
        self.clear_content()
        self.show_standard_brand()
        self.refresh_hardware_status()

        self.mid_label.configure(text="FRAMES")
        self.status_label.configure(text="VIEW", text_color=WARNING)

        self.preview_label = tk.Label(
            self.content,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        self.preview_label.pack()

        panel = ctk.CTkFrame(
            self.content,
            height=116,
            fg_color=PANEL_ALT,
            corner_radius=0
        )
        panel.pack(fill="x")

        self.btn(panel, "Prev", self.show_previous_frame, 10, 52, 90, 36, BUTTON_BG, "rewind")
        self.btn(panel, "Next", self.show_next_frame, 110, 52, 90, 36, BUTTON_BG, "forward")
        self.btn(panel, "Frames", self.show_frames, 210, 52, 90, 36, BUTTON_BG, "frame")
        self.btn(panel, "Home", self.show_home, 310, 52, 90, 36, BUTTON_BG, "home")

        self.render_frame_session_image()

    def render_frame_session_image(self):
        if not self.frame_session_images or self.preview_label is None:
            return

        path = self.frame_session_images[self.frame_session_index]
        image = Image.open(path).convert("RGB")
        image = self.fit_image_to_preview(image)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo)

        total = len(self.frame_session_images)
        self.status_label.configure(
            text=f"{self.frame_session_index + 1}/{total}",
            text_color=WARNING,
        )

    def show_previous_frame(self):
        if not self.frame_session_images:
            return
        self.frame_session_index = (self.frame_session_index - 1) % len(self.frame_session_images)
        self.render_frame_session_image()

    def show_next_frame(self):
        if not self.frame_session_images:
            return
        self.frame_session_index = (self.frame_session_index + 1) % len(self.frame_session_images)
        self.render_frame_session_image()

    # =====================================================
    # STREAM UPDATE
    # =====================================================

    def update_stream(self):
        if not self.running:
            return

        self.check_encode_result()
        self.check_save_result()
        self.check_progress_updates()

        if self.page == "player" and self.preview_label is not None:
            try:
                image = self.video_frame_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                self.preview_photo = ImageTk.PhotoImage(image)
                self.preview_label.configure(image=self.preview_photo)

                if self.video_process is None and self.video_frame_queue.empty():
                    self.status_label.configure(text="DONE", text_color=SUCCESS)

        if self.page == "capture" and self.preview_label is not None:
            frame = self.camera.get_frame()

            if self.capture_step == 1:
                preview = self.processor.make_crop_preview(frame, (432, 166))
                p = self.processor
                self.mid_label.configure(text="CROP")

            elif self.capture_step == 2:
                preview = self.processor.make_rotate_zoom_preview(frame, (432, 166))
                p = self.processor
                self.mid_label.configure(text="FRAME")

            elif self.capture_step == 3:
                preview = self.processor.make_picture_preview(frame, (432, 166))
                p = self.processor
                self.mid_label.configure(text="COLOR")

            else:
                preview = self.processor.make_picture_preview(frame, (432, 166))
                self.mid_label.configure(text="CAPTURE")

            self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview_photo)

            if self.capturing:
                self.fake_capture_loop()

        self.stream_after_id = self.after(80, self.update_stream)

    # =====================================================
    # CAPTURE + MOTOR
    # =====================================================

    def capture_once(self):
        if self.encoding or self.busy_active:
            return

        frame = self.camera.get_frame()
        final_img = self.processor.make_final_image(frame)
        self.show_busy_overlay("SAVING FRAME", "Please wait...", 0)
        threading.Thread(
            target=self.save_single_frame_task,
            args=(final_img,),
            daemon=True,
        ).start()

    def start_capturing(self):
        if self.encoding or self.busy_active:
            return

        prefix = "recording" if self.settings.output_mode == "MP4" else "frames"
        self.capture_session = start_session(self.settings, prefix=prefix)
        self.capturing = True
        self.last_auto_capture = 0

        self.status_label.configure(text="CAPTURE", text_color=WARNING)
        self.draw_capture_controls()

        print("START CAPTURING")
        print("Film type:", self.settings.film_type)
        print("Output mode:", self.settings.output_mode)
        print("FPS:", self.settings.video_fps)
        print("Save location:", self.settings.save_location)
        print("Session:", self.capture_session["name"])

    def stop_capturing(self):
        if self.encoding or self.busy_active:
            return

        self.capturing = False
        self.status_label.configure(text="SAVING", text_color=WARNING)

        print("STOP CAPTURING")

        session = self.capture_session
        self.capture_session = None

        if session is None or session["frame_count"] <= 0:
            self.status_label.configure(text="ERROR", text_color=DANGER)
            self.draw_capture_controls()
        elif self.settings.output_mode == "MP4":
            self.encoding = True
            self.show_busy_overlay("CREATING VIDEO", "Encoding MP4...", 0)
            self.draw_capture_controls()
            threading.Thread(
                target=self.encode_session,
                args=(session, self.settings.video_fps),
                daemon=True,
            ).start()
        else:
            print("Frames saved in:", session["frames_dir"])
            self.status_label.configure(text="SAVED", text_color=SUCCESS)
            self.draw_capture_controls()

    def encode_session(self, session, fps):
        output_path = make_mp4_from_session(
            session,
            fps,
            progress_callback=lambda percent: self.progress_updates.put(
                ("video", percent, "Encoding MP4...")
            ),
        )
        self.encode_results.put(output_path)

    def save_single_frame_task(self, final_img):
        self.progress_updates.put(("frame", 10, "Preparing frame..."))
        path = save_single_frame(
            final_img,
            self.settings,
            prefix="frame",
            progress_callback=lambda percent: self.progress_updates.put(
                ("frame", percent, "Writing frame...")
            ),
        )
        self.progress_updates.put(("frame", 100, "Frame saved"))
        self.save_results.put(path)

    def check_encode_result(self):
        try:
            output_path = self.encode_results.get_nowait()
        except queue.Empty:
            return

        self.encoding = False
        self.hide_busy_overlay()
        if output_path:
            self.status_label.configure(text="SAVED", text_color=SUCCESS)
        else:
            self.status_label.configure(text="ERROR", text_color=DANGER)

        if self.page == "capture":
            self.draw_capture_controls()

    def check_save_result(self):
        try:
            path = self.save_results.get_nowait()
        except queue.Empty:
            return

        self.hide_busy_overlay()
        print("Single frame saved:", path)
        self.status_label.configure(text="SAVED", text_color=WARNING)
        self.after(
            800,
            lambda: self.status_label.configure(text="STREAM", text_color=SUCCESS)
        )

    def check_progress_updates(self):
        latest = None
        while True:
            try:
                latest = self.progress_updates.get_nowait()
            except queue.Empty:
                break

        if latest is None or not self.busy_active:
            return

        job_type, percent, detail = latest
        title = "CREATING VIDEO" if job_type == "video" else "SAVING FRAME"
        self.busy_title_label.configure(text=title)
        self.update_busy_progress(percent, detail)

    def fake_capture_loop(self):
        now = time.time()

        # Dummy auto capture every 0.5 second.
        # Later this becomes:
        # move stepper -> wait -> capture camera frame -> save frame
        if now - self.last_auto_capture < 0.5:
            return

        self.last_auto_capture = now

        if self.capture_session is None:
            return

        frame = self.camera.get_frame()
        final_img = self.processor.make_final_image(frame)

        save_frame_to_session(final_img, self.capture_session)

        print("Auto captured frame:", self.capture_session["frame_count"])

    def motor_forward(self):
        self.motor_status = "Forward"
        print("Stepper command: forward one frame")

    def motor_backward(self):
        self.motor_status = "Backward"
        print("Stepper command: backward one frame")

    def motor_stop(self):
        self.motor_status = "Stopped"
        print("Stepper command: stop")


if __name__ == "__main__":
    app = FilmDigitizerApp()
    app.mainloop()
