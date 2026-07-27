"""
Gestor de íconos reales (PNG) para reemplazar los emojis de la interfaz.

Los archivos en assets/icons/ son máscaras: forma opaca sobre fondo
transparente (sin color propio). Este módulo las tiñe al color pedido
y cachea el resultado, porque Tkinter necesita mantener una referencia
viva al PhotoImage o el recolector de basura lo destruye.
"""
from pathlib import Path
from PIL import Image, ImageTk

_ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"
_cache = {}


def get_icon(name: str, size: int = 16, color: str = "#FFFFFF") -> ImageTk.PhotoImage:
    """
    Carga assets/icons/<name>.png, lo escala a size x size y lo tiñe de
    'color', preservando el canal alpha original (el contorno del ícono).

    Cachea por (name, size, color): llamar varias veces con los mismos
    parámetros no vuelve a decodificar el archivo ni crea referencias
    nuevas para el garbage collector.
    """
    key = (name, size, color)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    path = _ICONS_DIR / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"Ícono no encontrado: {path}")

    source = Image.open(path).convert("RGBA")
    if source.size != (size, size):
        source = source.resize((size, size), Image.LANCZOS)

    alpha = source.split()[-1]
    r, g, b = _hex_to_rgb(color)
    tinted = Image.new("RGBA", (size, size), (r, g, b, 0))
    tinted.putalpha(alpha)

    photo = ImageTk.PhotoImage(tinted)
    _cache[key] = photo
    return photo


def _hex_to_rgb(color: str):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
