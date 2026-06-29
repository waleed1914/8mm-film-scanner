import os
import time
import pygame
from datetime import datetime

# =====================================================
# FILM DIGITIZER SOFTWARE
# Dummy image version
# Mouse/touch + keyboard supported
# Camera streaming will be added later
# =====================================================

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

# ---------------- APP STATE ----------------
page = "home"
selected = 0

recording = False
frame_count = 0
session_name = ""

film_type = "8mm"
output_fps = 20

zoom = 1.0
offset_x = 0
offset_y = 0

brightness = 0
contrast = 0
sharpness = 0
tint = 0

motor_status = "Stopped"

# ---------------- PYGAME INIT ----------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Film Digitizer")
clock = pygame.time.Clock()

font_title = pygame.font.SysFont("Arial", 32, bold=True)
font_big = pygame.font.SysFont("Arial", 26, bold=True)
font_med = pygame.font.SysFont("Arial", 21, bold=True)
font_small = pygame.font.SysFont("Arial", 16)
font_tiny = pygame.font.SysFont("Arial", 13)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (20, 20, 20)
GRAY = (70, 70, 70)
LIGHT_GRAY = (150, 150, 150)
RED = (220, 40, 40)
GREEN = (35, 180, 80)
BLUE = (45, 120, 220)
YELLOW = (230, 190, 40)

# ---------------- CREATE DUMMY IMAGE IF MISSING ----------------
if not os.path.exists(DUMMY_IMAGE):
    dummy = pygame.Surface((4056, 3040))
    dummy.fill((25, 25, 25))

    pygame.draw.rect(dummy, WHITE, (400, 300, 3250, 2400), 20)
    pygame.draw.rect(dummy, YELLOW, (700, 600, 2650, 1800), 12)

    big_font = pygame.font.SysFont("Arial", 160, bold=True)
    small_font = pygame.font.SysFont("Arial", 90)

    text1 = big_font.render("DUMMY FILM FRAME", True, WHITE)
    text2 = small_font.render("Camera will be added later", True, LIGHT_GRAY)

    dummy.blit(text1, (1100, 1350))
    dummy.blit(text2, (1200, 1550))

    pygame.image.save(dummy, DUMMY_IMAGE)

# ---------------- LOAD DUMMY IMAGE ----------------
try:
    original_img = pygame.image.load(DUMMY_IMAGE).convert()
except Exception:
    original_img = pygame.Surface((4056, 3040))
    original_img.fill((40, 40, 40))


# =====================================================
# UI HELPERS
# =====================================================

def draw_text(text, x, y, font, color=WHITE):
    img = font.render(str(text), True, color)
    screen.blit(img, (x, y))


def center_text(text, y, font, color=WHITE):
    img = font.render(str(text), True, color)
    rect = img.get_rect(center=(SCREEN_W // 2, y))
    screen.blit(img, rect)


def draw_button(text, x, y, w, h, active=False, color=None):
    if color is None:
        color = BLUE if active else GRAY

    pygame.draw.rect(screen, color, (x, y, w, h), border_radius=8)
    pygame.draw.rect(screen, WHITE, (x, y, w, h), 2, border_radius=8)

    txt = font_small.render(text, True, WHITE)
    rect = txt.get_rect(center=(x + w // 2, y + h // 2))
    screen.blit(txt, rect)


def draw_top_bar(title):
    pygame.draw.rect(screen, BLACK, (0, 0, SCREEN_W, 36))
    draw_text(title, 10, 8, font_small, WHITE)

    if recording:
        pygame.draw.circle(screen, RED, (410, 18), 7)
        draw_text("REC", 425, 9, font_small, RED)


def draw_bottom_hint(text="Enter=OK  Arrows=Move  Backspace=Back"):
    pygame.draw.rect(screen, BLACK, (0, 292, SCREEN_W, 28))
    center_text(text, 306, font_tiny, LIGHT_GRAY)


def hit(mx, my, x, y, w, h):
    return x <= mx <= x + w and y <= my <= y + h


def get_preview_surface():
    global zoom, offset_x, offset_y

    img_w, img_h = original_img.get_size()

    crop_w = int(img_w / zoom)
    crop_h = int(img_h / zoom)

    cx = img_w // 2 + offset_x
    cy = img_h // 2 + offset_y

    x1 = max(0, min(img_w - crop_w, cx - crop_w // 2))
    y1 = max(0, min(img_h - crop_h, cy - crop_h // 2))

    crop_rect = pygame.Rect(x1, y1, crop_w, crop_h)
    cropped = original_img.subsurface(crop_rect).copy()

    preview = pygame.transform.smoothscale(cropped, (SCREEN_W, 240))
    return preview


def save_dummy_frame():
    global frame_count, session_name

    session_dir = os.path.join(FRAMES_DIR, session_name)
    os.makedirs(session_dir, exist_ok=True)

    preview = get_preview_surface()
    file_path = os.path.join(session_dir, f"frame_{frame_count:06d}.jpg")
    pygame.image.save(preview, file_path)

    frame_count += 1


def start_recording():
    global recording, frame_count, session_name

    session_name = datetime.now().strftime("scan_%Y%m%d_%H%M%S")
    frame_count = 0
    recording = True


def stop_recording():
    global recording, session_name

    recording = False

    fake_recording = os.path.join(RECORDINGS_DIR, session_name + "_dummy_recording.txt")

    with open(fake_recording, "w") as f:
        f.write("Dummy recording created.\n")
        f.write(f"Session: {session_name}\n")
        f.write(f"Frames captured: {frame_count}\n")
        f.write("Camera and MP4 export will be added later.\n")

    session_name = ""


def get_recordings():
    files = []
    for f in os.listdir(RECORDINGS_DIR):
        if f.endswith(".txt") or f.endswith(".mp4"):
            files.append(f)
    return sorted(files, reverse=True)


# =====================================================
# CLICK / TOUCH HANDLER
# =====================================================

def handle_click(mx, my):
    global page, selected
    global recording, motor_status
    global film_type, output_fps
    global brightness, contrast, sharpness, tint

    # HOME PAGE
    if page == "home":
        if hit(mx, my, 30, 135, 130, 75):
            page = "capture"
            selected = 0

        elif hit(mx, my, 175, 135, 130, 75):
            page = "menu"
            selected = 0

        elif hit(mx, my, 320, 135, 130, 75):
            page = "settings"
            selected = 0

    # CAPTURE PAGE
    elif page == "capture":
        if hit(mx, my, 5, 281, 90, 34):
            selected = 0
            if recording:
                stop_recording()
            else:
                start_recording()

        elif hit(mx, my, 100, 281, 80, 34):
            page = "frame_adjust"
            selected = 1

        elif hit(mx, my, 185, 281, 90, 34):
            page = "picture"
            selected = 0

        elif hit(mx, my, 380, 281, 90, 34):
            page = "home"
            selected = 0

    # FRAME ADJUST PAGE
    elif page == "frame_adjust":
        # Touch zones for frame movement
        global zoom, offset_x, offset_y

        if my > 275:
            page = "capture"
            selected = 1

        elif mx < 120:
            offset_x -= 40

        elif mx > 360:
            offset_x += 40

        elif my < 120:
            offset_y -= 40

        elif my > 190:
            offset_y += 40

        else:
            zoom += 0.1
            if zoom > 4.0:
                zoom = 1.0

    # PICTURE PAGE
    elif page == "picture":
        if hit(mx, my, 45, 60, 390, 35):
            selected = 0
            brightness += 1

        elif hit(mx, my, 45, 105, 390, 35):
            selected = 1
            contrast += 1

        elif hit(mx, my, 45, 150, 390, 35):
            selected = 2
            sharpness += 1

        elif hit(mx, my, 45, 195, 390, 35):
            selected = 3
            tint += 1

        elif hit(mx, my, 45, 240, 390, 35):
            selected = 4
            brightness = 0
            contrast = 0
            sharpness = 0
            tint = 0

        elif my > 290:
            page = "capture"
            selected = 2

    # MENU PAGE
    elif page == "menu":
        if hit(mx, my, 80, 62, 320, 36):
            page = "recordings"
            selected = 0

        elif hit(mx, my, 80, 107, 320, 36):
            motor_status = "Rewinding"

        elif hit(mx, my, 80, 152, 320, 36):
            motor_status = "Fast Forward"

        elif hit(mx, my, 80, 197, 320, 36):
            motor_status = "Stopped"

        elif hit(mx, my, 80, 242, 320, 36):
            page = "home"
            selected = 1

    # RECORDINGS PAGE
    elif page == "recordings":
        if my > 285:
            page = "menu"
            selected = 0

    # SETTINGS PAGE
    elif page == "settings":
        if hit(mx, my, 35, 54, 410, 34):
            selected = 0
            film_type = "Super 8" if film_type == "8mm" else "8mm"

        elif hit(mx, my, 35, 93, 410, 34):
            selected = 1
            output_fps += 1
            if output_fps > 30:
                output_fps = 10

        elif hit(mx, my, 35, 171, 410, 34):
            selected = 3
            page = "confirm_erase"

        elif hit(mx, my, 35, 210, 410, 34):
            selected = 4
            film_type = "8mm"
            output_fps = 20
            brightness = 0
            contrast = 0
            sharpness = 0
            tint = 0

        elif hit(mx, my, 35, 249, 410, 34):
            page = "home"
            selected = 2

    # CONFIRM ERASE PAGE
    elif page == "confirm_erase":
        if hit(mx, my, 80, 200, 130, 45):
            page = "settings"
            selected = 3

        elif hit(mx, my, 270, 200, 130, 45):
            for f in os.listdir(RECORDINGS_DIR):
                path = os.path.join(RECORDINGS_DIR, f)
                if os.path.isfile(path):
                    os.remove(path)

            page = "settings"
            selected = 3


# =====================================================
# PAGES
# =====================================================

def page_home():
    screen.fill((10, 10, 10))

    center_text("FILM DIGITIZER", 55, font_title, WHITE)
    center_text("Raspberry Pi Edition", 88, font_small, LIGHT_GRAY)

    buttons = [
        ("Capture", 30, 135, 130, 75),
        ("Menu", 175, 135, 130, 75),
        ("Settings", 320, 135, 130, 75),
    ]

    for i, (txt, x, y, w, h) in enumerate(buttons):
        draw_button(txt, x, y, w, h, selected == i)

    draw_text("Dummy image mode", 15, 260, font_tiny, YELLOW)
    draw_text("Camera streaming will be added later", 15, 276, font_tiny, LIGHT_GRAY)


def page_capture():
    screen.fill(BLACK)

    preview = get_preview_surface()
    screen.blit(preview, (0, 36))

    draw_top_bar("Capture")

    pygame.draw.rect(screen, DARK, (0, 276, SCREEN_W, 44))

    buttons = [
        ("STOP" if recording else "RECORD", 5, 281, 90, 34),
        ("Frame", 100, 281, 80, 34),
        ("Picture", 185, 281, 90, 34),
        ("Back", 380, 281, 90, 34),
    ]

    for i, (txt, x, y, w, h) in enumerate(buttons):
        if txt == "STOP":
            color = RED if selected == i else GRAY
        else:
            color = BLUE if selected == i else GRAY

        draw_button(txt, x, y, w, h, selected == i, color=color)

    if recording:
        draw_text(f"Frames: {frame_count}", 10, 45, font_small, RED)

    draw_text(f"Zoom {zoom:.1f}x", 350, 45, font_tiny, YELLOW)


def page_frame_adjust():
    screen.fill(BLACK)

    preview = get_preview_surface()
    screen.blit(preview, (0, 36))

    draw_top_bar("Frame Adjust")

    draw_text("Tap left/right/up/down to move", 20, 45, font_tiny, YELLOW)
    draw_text("Tap center to zoom", 20, 62, font_tiny, YELLOW)

    pygame.draw.rect(screen, DARK, (0, 276, SCREEN_W, 44))
    draw_text(f"Zoom: {zoom:.1f}x", 10, 282, font_tiny, WHITE)
    draw_text(f"X: {offset_x}  Y: {offset_y}", 120, 282, font_tiny, WHITE)
    draw_text("Tap bottom / Enter / Backspace = Back", 10, 300, font_tiny, LIGHT_GRAY)


def page_picture():
    screen.fill((15, 15, 15))
    draw_top_bar("Picture Settings")

    items = [
        ("Brightness", brightness),
        ("Contrast", contrast),
        ("Sharpness", sharpness),
        ("Tint", tint),
        ("Reset Picture", ""),
    ]

    y = 60
    for i, (name, value) in enumerate(items):
        color = BLUE if selected == i else GRAY
        pygame.draw.rect(screen, color, (45, y, 390, 35), border_radius=8)
        pygame.draw.rect(screen, WHITE, (45, y, 390, 35), 1, border_radius=8)

        draw_text(name, 60, y + 8, font_small, WHITE)
        draw_text(value, 340, y + 8, font_small, YELLOW)

        y += 45

    draw_bottom_hint("Touch item to increase  Backspace=Back")


def page_menu():
    screen.fill((15, 15, 15))
    draw_top_bar("Menu")

    items = [
        "My Recordings",
        "Rewind",
        "Fast Forward",
        "Motor Stop",
        "Back",
    ]

    y = 62
    for i, item in enumerate(items):
        draw_button(item, 80, y, 320, 36, selected == i)
        y += 45

    draw_text(f"Motor: {motor_status}", 15, 268, font_tiny, YELLOW)
    draw_bottom_hint()


def page_recordings():
    screen.fill((15, 15, 15))
    draw_top_bar("My Recordings")

    files = get_recordings()

    if not files:
        center_text("No recordings yet", 145, font_med, LIGHT_GRAY)
    else:
        y = 55
        for i, f in enumerate(files[:7]):
            color = BLUE if selected == i else GRAY
            pygame.draw.rect(screen, color, (20, y, 440, 28), border_radius=5)
            draw_text(f, 30, y + 6, font_tiny, WHITE)
            y += 33

    draw_bottom_hint("Backspace or tap bottom = Back")


def page_settings():
    screen.fill((15, 15, 15))
    draw_top_bar("Settings")

    items = [
        ("Film Type", film_type),
        ("Output FPS", output_fps),
        ("Save Location", "SD Card"),
        ("Erase Recordings", ""),
        ("Factory Reset", ""),
        ("Back", ""),
    ]

    y = 54
    for i, (name, value) in enumerate(items):
        color = BLUE if selected == i else GRAY
        pygame.draw.rect(screen, color, (35, y, 410, 34), border_radius=8)
        pygame.draw.rect(screen, WHITE, (35, y, 410, 34), 1, border_radius=8)

        draw_text(name, 50, y + 8, font_tiny, WHITE)
        draw_text(value, 320, y + 8, font_tiny, YELLOW)

        y += 39

    draw_bottom_hint("Touch item or use keyboard")


def page_confirm_erase():
    screen.fill((20, 0, 0))
    center_text("Erase all recordings?", 100, font_big, WHITE)
    center_text("This will delete dummy recordings", 135, font_small, LIGHT_GRAY)

    draw_button("Cancel", 80, 200, 130, 45, selected == 0)
    draw_button("Erase", 270, 200, 130, 45, selected == 1, color=RED if selected == 1 else GRAY)


# =====================================================
# MAIN LOOP
# =====================================================

last_dummy_capture = 0
running = True

while running:
    clock.tick(30)

    # Dummy recording captures 2 frames per second
    if recording:
        now = time.time()
        if now - last_dummy_capture >= 0.5:
            save_dummy_frame()
            last_dummy_capture = now

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # Mouse / touch
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            handle_click(mx, my)

        # Keyboard
        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                running = False

            # HOME
            if page == "home":
                if event.key == pygame.K_LEFT:
                    selected = max(0, selected - 1)

                elif event.key == pygame.K_RIGHT:
                    selected = min(2, selected + 1)

                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if selected == 0:
                        page = "capture"
                        selected = 0
                    elif selected == 1:
                        page = "menu"
                        selected = 0
                    elif selected == 2:
                        page = "settings"
                        selected = 0

            # CAPTURE
            elif page == "capture":
                if event.key == pygame.K_LEFT:
                    selected = max(0, selected - 1)

                elif event.key == pygame.K_RIGHT:
                    selected = min(3, selected + 1)

                elif event.key == pygame.K_BACKSPACE:
                    page = "home"
                    selected = 0

                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if selected == 0:
                        if recording:
                            stop_recording()
                        else:
                            start_recording()

                    elif selected == 1:
                        page = "frame_adjust"

                    elif selected == 2:
                        page = "picture"
                        selected = 0

                    elif selected == 3:
                        page = "home"
                        selected = 0

            # FRAME ADJUST
            elif page == "frame_adjust":
                if event.key == pygame.K_BACKSPACE or event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    page = "capture"
                    selected = 1

                elif event.key == pygame.K_UP:
                    offset_y -= 40

                elif event.key == pygame.K_DOWN:
                    offset_y += 40

                elif event.key == pygame.K_LEFT:
                    offset_x -= 40

                elif event.key == pygame.K_RIGHT:
                    offset_x += 40

                elif event.key in [pygame.K_PLUS, pygame.K_EQUALS]:
                    zoom = min(4.0, zoom + 0.1)

                elif event.key == pygame.K_MINUS:
                    zoom = max(1.0, zoom - 0.1)

            # PICTURE
            elif page == "picture":
                if event.key == pygame.K_BACKSPACE:
                    page = "capture"
                    selected = 2

                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)

                elif event.key == pygame.K_DOWN:
                    selected = min(4, selected + 1)

                elif event.key in [pygame.K_PLUS, pygame.K_EQUALS, pygame.K_RIGHT]:
                    if selected == 0:
                        brightness += 1
                    elif selected == 1:
                        contrast += 1
                    elif selected == 2:
                        sharpness += 1
                    elif selected == 3:
                        tint += 1

                elif event.key in [pygame.K_MINUS, pygame.K_LEFT]:
                    if selected == 0:
                        brightness -= 1
                    elif selected == 1:
                        contrast -= 1
                    elif selected == 2:
                        sharpness -= 1
                    elif selected == 3:
                        tint -= 1

                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if selected == 4:
                        brightness = 0
                        contrast = 0
                        sharpness = 0
                        tint = 0

            # MENU
            elif page == "menu":
                if event.key == pygame.K_BACKSPACE:
                    page = "home"
                    selected = 1

                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)

                elif event.key == pygame.K_DOWN:
                    selected = min(4, selected + 1)

                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if selected == 0:
                        page = "recordings"
                        selected = 0

                    elif selected == 1:
                        motor_status = "Rewinding"

                    elif selected == 2:
                        motor_status = "Fast Forward"

                    elif selected == 3:
                        motor_status = "Stopped"

                    elif selected == 4:
                        page = "home"
                        selected = 1

            # RECORDINGS
            elif page == "recordings":
                files = get_recordings()

                if event.key == pygame.K_BACKSPACE:
                    page = "menu"
                    selected = 0

                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)

                elif event.key == pygame.K_DOWN:
                    selected = min(max(0, len(files) - 1), selected + 1)

            # SETTINGS
            elif page == "settings":
                if event.key == pygame.K_BACKSPACE:
                    page = "home"
                    selected = 2

                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)

                elif event.key == pygame.K_DOWN:
                    selected = min(5, selected + 1)

                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if selected == 0:
                        film_type = "Super 8" if film_type == "8mm" else "8mm"

                    elif selected == 1:
                        output_fps += 1
                        if output_fps > 30:
                            output_fps = 10

                    elif selected == 3:
                        page = "confirm_erase"
                        selected = 0

                    elif selected == 4:
                        film_type = "8mm"
                        output_fps = 20
                        brightness = 0
                        contrast = 0
                        sharpness = 0
                        tint = 0

                    elif selected == 5:
                        page = "home"
                        selected = 2

            # CONFIRM ERASE
            elif page == "confirm_erase":
                if event.key == pygame.K_LEFT:
                    selected = 0

                elif event.key == pygame.K_RIGHT:
                    selected = 1

                elif event.key == pygame.K_BACKSPACE:
                    page = "settings"
                    selected = 3

                elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if selected == 0:
                        page = "settings"
                        selected = 3

                    elif selected == 1:
                        for f in os.listdir(RECORDINGS_DIR):
                            path = os.path.join(RECORDINGS_DIR, f)
                            if os.path.isfile(path):
                                os.remove(path)

                        page = "settings"
                        selected = 3

    # DRAW CURRENT PAGE
    if page == "home":
        page_home()

    elif page == "capture":
        page_capture()

    elif page == "frame_adjust":
        page_frame_adjust()

    elif page == "picture":
        page_picture()

    elif page == "menu":
        page_menu()

    elif page == "recordings":
        page_recordings()

    elif page == "settings":
        page_settings()

    elif page == "confirm_erase":
        page_confirm_erase()

    pygame.display.update()

# Clean exit
if recording:
    stop_recording()

pygame.quit()