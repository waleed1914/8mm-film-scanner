from PIL import Image, ImageEnhance, ImageDraw


class ImageProcessor:
    def __init__(self):
        # STEP 1: crop box values
        self.crop_zoom_w = 1.5
        self.crop_zoom_h = 1.5
        self.crop_offset_x = 0
        self.crop_offset_y = 0

        # Smaller movement for accurate crop adjustment
        self.crop_move_step = 20
        self.final_move_step = 20

        # STEP 2: rotation and zoom after crop
        self.rotation = 0
        self.final_zoom = 1.0
        self.final_offset_x = 0
        self.final_offset_y = 0

        # STEP 3: picture settings
        self.exposure = 0
        self.sharpness = 0
        self.tint = 0

    def reset_all(self):
        self.crop_zoom_w = 1.5
        self.crop_zoom_h = 1.5
        self.crop_offset_x = 0
        self.crop_offset_y = 0

        self.rotation = 0
        self.final_zoom = 1.0
        self.final_offset_x = 0
        self.final_offset_y = 0

        self.exposure = 0
        self.sharpness = 0
        self.tint = 0

    def reset_picture(self):
        self.exposure = 0
        self.sharpness = 0
        self.tint = 0

    # =====================================================
    # STEP 1: CROP BOX
    # =====================================================

    def crop_width_smaller(self):
        self.crop_zoom_w = min(8.0, self.crop_zoom_w + 0.05)

    def crop_width_bigger(self):
        self.crop_zoom_w = max(1.0, self.crop_zoom_w - 0.05)

    def crop_height_smaller(self):
        self.crop_zoom_h = min(8.0, self.crop_zoom_h + 0.05)

    def crop_height_bigger(self):
        self.crop_zoom_h = max(1.0, self.crop_zoom_h - 0.05)

    def crop_move_left(self):
        self.crop_offset_x -= self.crop_move_step

    def crop_move_right(self):
        self.crop_offset_x += self.crop_move_step

    def crop_move_up(self):
        self.crop_offset_y -= self.crop_move_step

    def crop_move_down(self):
        self.crop_offset_y += self.crop_move_step

    def get_crop_box(self, img):
        img_w, img_h = img.size

        crop_w = int(img_w / self.crop_zoom_w)
        crop_h = int(img_h / self.crop_zoom_h)

        crop_w = max(20, min(crop_w, img_w))
        crop_h = max(20, min(crop_h, img_h))

        cx = img_w // 2 + self.crop_offset_x
        cy = img_h // 2 + self.crop_offset_y

        x1 = cx - crop_w // 2
        y1 = cy - crop_h // 2

        x1 = max(0, min(img_w - crop_w, x1))
        y1 = max(0, min(img_h - crop_h, y1))

        x2 = x1 + crop_w
        y2 = y1 + crop_h

        return x1, y1, x2, y2

    def make_crop_preview(self, img, preview_size):
        img = img.copy()
        x1, y1, x2, y2 = self.get_crop_box(img)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 110))
        clear = Image.new("RGBA", (x2 - x1, y2 - y1), (0, 0, 0, 0))
        overlay.paste(clear, (x1, y1))

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        line_w = max(5, int(img.size[0] / 700))

        for i in range(line_w):
            draw.rectangle(
                (x1 + i, y1 + i, x2 - i, y2 - i),
                outline=(255, 210, 0)
            )

        return self.fit_to_preview(img, preview_size)

    def get_cropped_image(self, img):
        img = img.copy()
        x1, y1, x2, y2 = self.get_crop_box(img)
        return img.crop((x1, y1, x2, y2))

    # =====================================================
    # STEP 2: ROTATE + ZOOM AFTER CROP
    # =====================================================

    def rotate_right(self):
        self.rotation += 90
        if self.rotation >= 360:
            self.rotation = 0

    def rotate_left(self):
        self.rotation -= 90
        if self.rotation < 0:
            self.rotation = 270

    def final_zoom_in(self):
        self.final_zoom = min(5.0, self.final_zoom + 0.05)

    def final_zoom_out(self):
        self.final_zoom = max(1.0, self.final_zoom - 0.05)

    def final_move_left(self):
        self.final_offset_x -= self.final_move_step

    def final_move_right(self):
        self.final_offset_x += self.final_move_step

    def final_move_up(self):
        self.final_offset_y -= self.final_move_step

    def final_move_down(self):
        self.final_offset_y += self.final_move_step

    def apply_rotation_and_zoom(self, img):
        img = img.copy()

        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)

        if self.final_zoom > 1.0:
            img_w, img_h = img.size

            crop_w = int(img_w / self.final_zoom)
            crop_h = int(img_h / self.final_zoom)

            crop_w = max(20, min(crop_w, img_w))
            crop_h = max(20, min(crop_h, img_h))

            cx = img_w // 2 + self.final_offset_x
            cy = img_h // 2 + self.final_offset_y

            x1 = cx - crop_w // 2
            y1 = cy - crop_h // 2

            x1 = max(0, min(img_w - crop_w, x1))
            y1 = max(0, min(img_h - crop_h, y1))

            x2 = x1 + crop_w
            y2 = y1 + crop_h

            img = img.crop((x1, y1, x2, y2))

        return img

    def make_rotate_zoom_preview(self, img, preview_size):
        cropped = self.get_cropped_image(img)
        adjusted = self.apply_rotation_and_zoom(cropped)
        return self.fit_to_preview(adjusted, preview_size)

    # =====================================================
    # STEP 3: EXPOSURE / SHARPNESS / TINT
    # =====================================================

    def exposure_up(self):
        self.exposure = min(30, self.exposure + 1)

    def exposure_down(self):
        self.exposure = max(-30, self.exposure - 1)

    def sharpness_up(self):
        self.sharpness = min(30, self.sharpness + 1)

    def sharpness_down(self):
        self.sharpness = max(-30, self.sharpness - 1)

    def tint_up(self):
        self.tint = min(30, self.tint + 1)

    def tint_down(self):
        self.tint = max(-30, self.tint - 1)

    def apply_tint(self, img):
        if self.tint == 0:
            return img

        img = img.convert("RGB")
        r, g, b = img.split()

        if self.tint > 0:
            # Warmer tint: more red, less blue
            r = ImageEnhance.Brightness(r).enhance(1.0 + self.tint / 50.0)
            b = ImageEnhance.Brightness(b).enhance(max(0.1, 1.0 - self.tint / 70.0))
        else:
            # Cooler tint: more blue, less red
            value = abs(self.tint)
            b = ImageEnhance.Brightness(b).enhance(1.0 + value / 50.0)
            r = ImageEnhance.Brightness(r).enhance(max(0.1, 1.0 - value / 70.0))

        return Image.merge("RGB", (r, g, b))

    def apply_picture_settings(self, img):
        img = img.copy()

        exposure_factor = max(0.1, 1.0 + self.exposure / 20.0)
        sharpness_factor = max(0.1, 1.0 + self.sharpness / 10.0)

        img = ImageEnhance.Brightness(img).enhance(exposure_factor)
        img = ImageEnhance.Sharpness(img).enhance(sharpness_factor)
        img = self.apply_tint(img)

        return img

    def make_picture_preview(self, img, preview_size):
        cropped = self.get_cropped_image(img)
        rotated = self.apply_rotation_and_zoom(cropped)
        final = self.apply_picture_settings(rotated)
        return self.fit_to_preview(final, preview_size)

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    def make_final_image(self, img):
        cropped = self.get_cropped_image(img)
        rotated = self.apply_rotation_and_zoom(cropped)
        final = self.apply_picture_settings(rotated)
        return final

    def fit_to_preview(self, img, preview_size):
        img = img.copy()
        img.thumbnail(preview_size, Image.LANCZOS)

        bg = Image.new("RGB", preview_size, (0, 0, 0))
        x = (preview_size[0] - img.size[0]) // 2
        y = (preview_size[1] - img.size[1]) // 2
        bg.paste(img, (x, y))

        return bg
