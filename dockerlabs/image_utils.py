"""
Conversión y optimización de imágenes a WebP.

Uso:
    from dockerlabs.image_utils import to_webp, PROFILES

    webp_bytes = to_webp(raw_bytes, profile='logo')
    webp_bytes = to_webp(raw_bytes, profile='perfil')
    webp_bytes = to_webp(raw_bytes, profile='equipo')
"""
from __future__ import annotations

import io
from typing import Literal

from PIL import Image, ImageOps

# Perfiles de conversión: (max_w, max_h, quality)
PROFILES: dict[str, tuple[int, int, int]] = {
    "logo":   (512, 512, 87),
    "perfil": (400, 400, 85),
    "equipo": (800, 400, 85),
}

ProfileName = Literal["logo", "perfil", "equipo"]


def to_webp(
    file_bytes: bytes,
    profile: ProfileName = "logo",
) -> bytes:
    """
    Convierte cualquier imagen a WebP con las dimensiones y calidad
    apropiadas para el contexto indicado.

    - Respeta la transparencia (RGBA).
    - Corrige la orientación EXIF antes de redimensionar.
    - GIF animado → WebP animado.
    - No amplía imágenes que ya sean más pequeñas que el máximo.

    Devuelve los bytes WebP resultantes.
    """
    max_w, max_h, quality = PROFILES[profile]

    img = Image.open(io.BytesIO(file_bytes))

    # ── GIF animado → WebP animado ─────────────────────────────────────────
    is_animated = getattr(img, "is_animated", False) and img.n_frames > 1
    if is_animated:
        return _convert_animated(img, max_w, max_h, quality)

    # ── Imagen estática ────────────────────────────────────────────────────
    img = ImageOps.exif_transpose(img)  # corregir rotación EXIF

    img = _normalize_mode(img)
    img.thumbnail((max_w, max_h), Image.LANCZOS)  # reduce, nunca amplía

    out = io.BytesIO()
    img.save(out, format="WEBP", quality=quality, method=6)
    return out.getvalue()


# ── Privados ────────────────────────────────────────────────────────────────

def _normalize_mode(img: Image.Image) -> Image.Image:
    """Convierte modos poco comunes a RGB/RGBA para WebP."""
    if img.mode == "P":
        img = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA" if img.mode.endswith("A") else "RGB")
    return img


def _convert_animated(img: Image.Image, max_w: int, max_h: int, quality: int) -> bytes:
    frames: list[Image.Image] = []
    durations: list[int] = []

    for i in range(img.n_frames):
        img.seek(i)
        frame = img.copy()
        frame = ImageOps.exif_transpose(frame)
        frame = _normalize_mode(frame)
        frame.thumbnail((max_w, max_h), Image.LANCZOS)
        frames.append(frame)
        durations.append(img.info.get("duration", 100))

    out = io.BytesIO()
    frames[0].save(
        out,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        quality=quality,
        method=4,
    )
    return out.getvalue()
