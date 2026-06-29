"""Antialiased line icons for the CARRERO-8 touchscreen."""

from PIL import Image, ImageDraw
import customtkinter as ctk

from ui.theme import ACCENT


def make_icon(name, size=20, color=None):
    """Draw a crisp icon without relying on emoji or platform fonts."""
    color = color or ACCENT
    scale = 4
    canvas = 24 * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def point(x, y):
        return int(x * scale), int(y * scale)

    def line(points, width=1.8, fill=color):
        draw.line([point(x, y) for x, y in points], fill=fill,
                  width=max(1, int(width * scale)), joint="curve")

    def box(coords, width=1.8, radius=2.5, fill=None):
        draw.rounded_rectangle(tuple(int(v * scale) for v in coords),
                               radius=int(radius * scale), outline=color,
                               fill=fill, width=max(1, int(width * scale)))

    def ellipse(coords, width=1.8, fill=None):
        draw.ellipse(tuple(int(v * scale) for v in coords), outline=color,
                     fill=fill, width=max(1, int(width * scale)))

    if name == "logo":
        # A compact film-reel "8" mark for CARRERO-8.
        ellipse((5, 2, 19, 12), width=2.2)
        ellipse((5, 12, 19, 22), width=2.2)
        ellipse((10, 6, 14, 10), width=1.4)
        ellipse((10, 14, 14, 18), width=1.4)
    elif name == "home":
        line(((3, 11), (12, 3), (21, 11)), width=2.1)
        line(((6, 10), (6, 21), (18, 21), (18, 10)))
        line(((10, 21), (10, 15), (14, 15), (14, 21)))
    elif name == "camera":
        box((2.5, 7, 21.5, 20), radius=3)
        ellipse((8, 10, 16, 18), width=2)
        line(((7, 7), (9, 4), (15, 4), (17, 7)))
    elif name == "menu":
        for y in (6, 12, 18):
            line(((4, y), (20, y)), width=2.1)
    elif name == "settings":
        ellipse((7, 7, 17, 17), width=2)
        ellipse((10, 10, 14, 14), fill=color, width=1)
        for a, b in (((12, 2), (12, 7)), ((12, 17), (12, 22)),
                     ((2, 12), (7, 12)), ((17, 12), (22, 12)),
                     ((5, 5), (8, 8)), ((16, 16), (19, 19)),
                     ((19, 5), (16, 8)), ((8, 16), (5, 19))):
            line((a, b), width=2)
    elif name == "crop":
        line(((7, 2), (7, 17), (22, 17)), width=2.2)
        line(((2, 7), (17, 7), (17, 22)), width=2.2)
    elif name == "frame":
        box((3, 3, 21, 21), radius=2)
        line(((8, 3), (8, 21)))
        line(((16, 3), (16, 21)))
    elif name == "color":
        ellipse((3, 3, 21, 21), width=2)
        draw.pieslice((3*scale, 3*scale, 21*scale, 21*scale),
                      270, 90, fill=color)
        ellipse((8, 8, 16, 16), width=1.5)
    elif name in ("back", "rewind"):
        line(((16, 4), (7, 12), (16, 20)), width=2.4)
        if name == "rewind":
            line(((10, 4), (1, 12), (10, 20)), width=2.4)
    elif name in ("next", "forward"):
        line(((8, 4), (17, 12), (8, 20)), width=2.4)
        if name == "forward":
            line(((14, 4), (23, 12), (14, 20)), width=2.4)
    elif name == "stop":
        box((5, 5, 19, 19), width=2, radius=2, fill=color)
    elif name == "play":
        draw.polygon((point(7, 4), point(20, 12), point(7, 20)),
                     fill=color)
    elif name == "save":
        box((4, 3, 20, 21), radius=2)
        box((7, 3, 17, 10), width=1.4, radius=1)
        ellipse((9, 14, 15, 20), fill=color, width=1)
    elif name == "delete":
        line(((8, 6), (16, 6)), width=2.2)
        line(((10, 4), (14, 4)), width=1.8)
        box((6, 6, 18, 21), radius=1.5)
        line(((10, 9), (10, 18)), width=1.7)
        line(((14, 9), (14, 18)), width=1.7)
    elif name == "edit":
        line(((4, 20), (7, 14), (17, 4), (21, 8), (11, 18), (4, 20)),
             width=2)
    elif name == "reset":
        draw.arc((3*scale, 3*scale, 21*scale, 21*scale), 35, 320,
                 fill=color, width=int(2.2*scale))
        draw.polygon((point(2, 5), point(8, 5), point(4, 10)), fill=color)
    elif name == "film":
        box((2, 5, 22, 19), radius=2)
        for x in (4, 10, 16):
            draw.rounded_rectangle((x*scale, 6*scale, (x+3)*scale, 9*scale),
                                   radius=scale//2, fill=color)
            draw.rounded_rectangle((x*scale, 15*scale, (x+3)*scale, 18*scale),
                                   radius=scale//2, fill=color)
    else:
        ellipse((5, 5, 19, 19), width=2)

    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
