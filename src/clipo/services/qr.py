"""Offline QR encoding. Payloads are validated, never truncated."""
from dataclasses import dataclass
from io import BytesIO
import re

import qrcode
from qrcode.exceptions import DataOverflowError
from qrcode.image.svg import SvgPathImage


def shareable_text(item):
    """QR codes share text, including code snippets and extracted image text."""
    if item.content_type == "files":
        return ""
    text = item.ocr_text if item.content_type == "image" else item.content_text
    return text if text.strip() else ""


@dataclass(frozen=True)
class QROptions:
    correction: str = "M"
    size: int = 512
    foreground: str = "#000000"
    background: str = "#ffffff"


def split_payload(text: str, max_bytes=500) -> list[str]:
    if max_bytes < 4:
        raise ValueError("Chunk size must be at least 4 bytes")
    chunks, chunk, size = [], [], 0
    for character in text:
        width = len(character.encode("utf-8"))
        if size + width > max_bytes:
            chunks.append("".join(chunk))
            chunk, size = [], 0
        chunk.append(character)
        size += width
    if chunk:
        chunks.append("".join(chunk))
    return chunks


def generate_qr(text: str, options=QROptions()):
    if not text:
        raise ValueError("Enter text to encode")
    if len(text.encode("utf-8")) > 2000:
        raise ValueError("Payload is too large for a practical QR. Use Split into parts or a URL you explicitly choose.")
    if options.correction not in ("L", "M", "Q", "H") or not 128 <= options.size <= 2048:
        raise ValueError("Invalid QR correction or size")
    for color in (options.foreground, options.background):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Colors must use #RRGGBB")
    def luminance(color):
        channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    foreground, background = luminance(options.foreground), luminance(options.background)
    if background <= foreground or (background + .05) / (foreground + .05) < 4.5:
        raise ValueError("Use a dark foreground and a light background with stronger contrast")
    qr = qrcode.QRCode(error_correction=getattr(qrcode.constants, "ERROR_CORRECT_" + options.correction), border=4, box_size=8)
    qr.add_data(text.encode("utf-8"), optimize=0)
    try:
        qr.make(fit=True)
    except DataOverflowError:
        raise ValueError("Payload does not fit at this correction level. Split it into parts.") from None
    matrix_size = len(qr.get_matrix())
    if options.size < matrix_size * 3:
        raise ValueError("Increase the image size for this payload (at least 3 pixels per module)")
    # Integer pixel modules preserve scan quality; output may be smaller than the chosen maximum.
    qr.box_size = max(3, options.size // matrix_size)
    png = BytesIO()
    qr.make_image(fill_color=options.foreground, back_color=options.background).save(png, format="PNG")
    svg = qr.make_image(image_factory=SvgPathImage).to_string().decode()
    svg = svg.replace('fill="#000000"', f'fill="{options.foreground}"')
    svg = svg.replace('>', f'><rect width="100%" height="100%" fill="{options.background}"/>', 1)
    return png.getvalue(), svg.encode()
