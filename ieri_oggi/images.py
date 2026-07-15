"""Elaborazione immagini con Pillow.

Le foto caricate (spesso pesanti, da smartphone) vengono corrette
nell'orientamento EXIF, convertite in RGB, ridimensionate e salvate come
JPEG compatto. Si genera anche una miniatura per una gallery veloce.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

LATO_MAX = 1600  # lato lungo massimo dell'immagine principale
LATO_THUMB = 400  # lato lungo massimo della miniatura
QUALITA = 85
MIME = "image/jpeg"


class ImmagineNonValida(ValueError):
    """Sollevata quando il file caricato non è un'immagine leggibile."""


def _prepara(img: Image.Image) -> Image.Image:
    """Applica orientamento EXIF e converte in RGB su sfondo bianco."""
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        sfondo = Image.new("RGB", img.size, (255, 255, 255))
        sfondo.paste(img, mask=img.split()[-1])
        return sfondo
    return img.convert("RGB")


def _to_jpeg(img: Image.Image, lato_max: int) -> bytes:
    img = img.copy()
    img.thumbnail((lato_max, lato_max), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=QUALITA, optimize=True)
    return buf.getvalue()


def processa(file_bytes: bytes) -> tuple[bytes, bytes]:
    """Da bytes grezzi ritorna (immagine, miniatura) come JPEG.

    Solleva ImmagineNonValida se il contenuto non è un'immagine.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        # DecompressionBombError: immagine con troppi pixel (possibile DoS).
        raise ImmagineNonValida(str(exc)) from exc

    img = _prepara(img)
    principale = _to_jpeg(img, LATO_MAX)
    thumb = _to_jpeg(img, LATO_THUMB)
    return principale, thumb
