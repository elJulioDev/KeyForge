"""
Manager for real (PNG) icons, replacing the emojis of the UI.

The files in assets/icons/ are masks: an opaque shape on a transparent
background (with no color of their own). This module tints them to the
requested color and caches the result, because Tkinter needs to keep a
live reference to the PhotoImage or the garbage collector destroys it.
"""
from pathlib import Path
from PIL import Image, ImageTk

try:
    from .logger import get_logger
    _logger = get_logger()
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)

_ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"
_cache = {}


def get_icon(name: str, size: int = 16, color: str = "#FFFFFF") -> ImageTk.PhotoImage:
    """
    Load assets/icons/<name>.png, scale it to size x size and tint it with
    'color', preserving the original alpha channel (the icon outline).

    Cached by (name, size, color): calling it repeatedly with the same
    parameters does not re-decode the file nor create new references for
    the garbage collector.

    If the icon file is missing (corrupted install) it returns a plain
    colored square instead of crashing the whole UI.
    """
    key = (name, size, color)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    path = _ICONS_DIR / f"{name}.png"
    if not path.exists():
        _logger.warning(f"Icon not found: {path}; using fallback")
        photo = _fallback_icon(size, color)
        _cache[key] = photo
        return photo

    try:
        source = Image.open(path).convert("RGBA")
    except Exception as e:
        _logger.warning(f"Could not open icon {path}: {e}; using fallback")
        photo = _fallback_icon(size, color)
        _cache[key] = photo
        return photo

    if source.size != (size, size):
        source = source.resize((size, size), Image.LANCZOS)

    alpha = source.split()[-1]
    r, g, b = _hex_to_rgb(color)
    tinted = Image.new("RGBA", (size, size), (r, g, b, 0))
    tinted.putalpha(alpha)

    photo = ImageTk.PhotoImage(tinted)
    _cache[key] = photo

    # ImageTk.PhotoImage embeds the pixels into Tk; the PIL images and their
    # file descriptors can be released right away.
    source.close()
    alpha.close()
    tinted.close()
    return photo


def _fallback_icon(size: int, color: str) -> ImageTk.PhotoImage:
    """Solid square placeholder used when an icon PNG is missing."""
    r, g, b = _hex_to_rgb(color)
    img = Image.new("RGBA", (size, size), (r, g, b, 255))
    photo = ImageTk.PhotoImage(img)
    img.close()
    return photo


def _hex_to_rgb(color: str):
    color = (color or "#FFFFFF").lstrip("#")
    if len(color) != 6:
        color = "#FFFFFF".lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
