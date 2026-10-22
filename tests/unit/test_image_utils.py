"""Tests puros de dockerlabs/image_utils.py — sin BD, sin red real.

Todas las imágenes de prueba se construyen en memoria con PIL; no se tocan
ficheros en disco.
"""
import io

import pytest
from PIL import Image

from dockerlabs.image_utils import PROFILES, to_webp

pytestmark = pytest.mark.unit


def _png_bytes(size, mode="RGB", color="red"):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


class TestProfiles:
    def test_known_profiles_have_expected_dimensions_and_quality(self):
        assert PROFILES["logo"] == (512, 512, 87)
        assert PROFILES["perfil"] == (400, 400, 85)
        assert PROFILES["equipo"] == (800, 400, 85)

    def test_unknown_profile_raises_key_error(self):
        with pytest.raises(KeyError):
            to_webp(_png_bytes((10, 10)), profile="no-existe")


class TestNoUpscale:
    @pytest.mark.parametrize("profile", ["logo", "perfil", "equipo"])
    def test_smaller_image_is_not_upscaled(self, profile):
        raw = _png_bytes((50, 30))
        out = to_webp(raw, profile=profile)
        img = Image.open(io.BytesIO(out))
        assert img.format == "WEBP"
        # Ni se amplía más allá del original...
        assert img.size[0] <= 50 and img.size[1] <= 30
        # ...ni se sale del máximo del perfil.
        max_w, max_h, _ = PROFILES[profile]
        assert img.size[0] <= max_w and img.size[1] <= max_h


class TestDownscale:
    def test_downscales_large_image_preserving_aspect_ratio(self):
        raw = _png_bytes((2000, 1000))  # ratio 2:1
        out = to_webp(raw, profile="logo")  # max 512x512
        img = Image.open(io.BytesIO(out))
        assert img.size == (512, 256)  # ratio preservada, nunca excede el máximo

    def test_downscales_portrait_image(self):
        raw = _png_bytes((1000, 2000))  # ratio 1:2
        out = to_webp(raw, profile="perfil")  # max 400x400
        img = Image.open(io.BytesIO(out))
        assert img.size == (200, 400)
        assert img.size[0] <= 400 and img.size[1] <= 400


class TestExifOrientation:
    def test_exif_rotation_is_corrected_before_resizing(self):
        # Imagen "apaisada" 600x300 con orientación EXIF 6 (rotada 90°): tras
        # corregirla debe quedar en vertical (300x600) antes de redimensionar.
        im = Image.new("RGB", (600, 300), "green")
        exif = im.getexif()
        exif[274] = 6  # Orientation
        buf = io.BytesIO()
        im.save(buf, format="JPEG", exif=exif)

        out = to_webp(buf.getvalue(), profile="logo")  # max 512x512
        img = Image.open(io.BytesIO(out))
        # Original corregido es 300x600 (vertical); escalado a max 512x512
        # conservando el ratio 1:2 da 256x512.
        assert img.size == (256, 512)


class TestPaletteMode:
    def test_palette_png_is_converted_without_error(self):
        im = Image.new("P", (100, 100))
        im.putpalette([i for i in range(256) for _ in range(3)])
        buf = io.BytesIO()
        im.save(buf, format="PNG")

        out = to_webp(buf.getvalue(), profile="perfil")
        img = Image.open(io.BytesIO(out))
        assert img.format == "WEBP"
        assert img.mode in ("RGB", "RGBA")


class TestRGBATransparency:
    def test_rgba_alpha_channel_is_preserved(self):
        im = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        buf = io.BytesIO()
        im.save(buf, format="PNG")

        out = to_webp(buf.getvalue(), profile="perfil")
        img = Image.open(io.BytesIO(out))
        assert img.mode == "RGBA"
        r, g, b, a = img.getpixel((0, 0))
        # WebP es lossy: tolerancia pequeña sobre el valor original.
        assert abs(a - 128) <= 3
        assert abs(r - 255) <= 3
        assert abs(g - 0) <= 3


class TestAnimatedGif:
    def test_animated_gif_becomes_animated_webp(self):
        frames = [Image.new("RGB", (50, 50), c) for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]]
        buf = io.BytesIO()
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)

        out = to_webp(buf.getvalue(), profile="logo")
        img = Image.open(io.BytesIO(out))
        assert img.format == "WEBP"
        assert getattr(img, "is_animated", False) is True
        assert img.n_frames >= 2
