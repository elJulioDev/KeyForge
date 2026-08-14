"""
Manager for real (PNG) icons, replacing the emojis of the UI.

The files in assets/icons/ are masks: an opaque shape on a transparent
background (with no color of their own). This module tints them to the
requested color and caches the result, because Tkinter needs to keep a
live reference to the PhotoImage or the garbage collector destroys it.
"""
from pathlib import Path
from PIL import Image, ImageTk

_ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"
_cache = {}


def get_icon(name: str, size: int = 16, color: str = "#FFFFFF") -> ImageTk.PhotoImage:
    """
    Load assets/icons/<name>.png, scale it to size x size and tint it with
    'color', preserving the original alpha channel (the icon outline).

    Cached by (name, size, color): calling it repeatedly with the same
    parameters does not re-decode the file nor create new references for
    the garbage collector.
    """
    key = (name, size, color)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    path = _ICONS_DIR / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"Icon not found: {path}")

    source = Image.open(path).convert("RGBA")
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


def _hex_to_rgb(color: str):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
