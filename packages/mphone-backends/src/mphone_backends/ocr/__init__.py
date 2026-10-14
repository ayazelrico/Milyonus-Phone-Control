"""OCR engines (A2.06, ADR-0013). Registered under the `mphone.ocr` entry-point group."""

import struct


def png_size(png: bytes) -> tuple[int, int]:
    """Width and height from the IHDR chunk, without decoding the image."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", png[16:24])
    return width, height


LANG_CODES = {"tr": "tr-TR", "en": "en-US", "de": "de-DE", "fr": "fr-FR", "ar": "ar-SA", "ru": "ru-RU"}
