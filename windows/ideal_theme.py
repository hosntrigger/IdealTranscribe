"""IDEALVISUAL UI tokens and scalable Tk button artwork, no dependencies."""
import tkinter as tk
from tkinter import ttk
import math

THEMES = {
    "dark": ("Material Dark", "#15191e", "#20272e", "#2a353e", "#54636e", "#eef4f8", "#aebecb", "#00aeef", "#69d8ff", "#53616d", "#071b26", "#323f49", 9),
    "light": ("Material Light", "#edf3f7", "#ffffff", "#e0eaf0", "#8499a8", "#172b39", "#456174", "#007cac", "#00628a", "#a6b3bd", "#ffffff", "#ffffff", 9),
    "studio": ("Studio Dark", "#121821", "#1a2230", "#202b3c", "#526479", "#edf2f7", "#a3b5c8", "#00aeef", "#48d4ff", "#66788b", "#0d141d", "#29384b", 5),
    "expressive": ("Android Expressive", "#151c22", "#25303a", "#374956", "#687e90", "#eff7fc", "#b6cad8", "#75d9ff", "#b3ebff", "#596c77", "#102c3b", "#354958", 12),
}
KEYS = ("bg", "panel", "panel_2", "line", "text", "muted", "accent", "accent_2", "disabled", "accent_text", "dialog", "radius")


def palette(name):
    return dict(zip(KEYS, THEMES.get(name, THEMES["dark"])[1:]))


def _rounded(img, radius, fill, border, scale):
    n = img.width()
    r = radius * scale
    thickness = max(1, round(scale))
    img.blank()
    for y in range(n):
        for x in range(n):
            dx = max(r-x-.5, x+.5-(n-r), 0)
            dy = max(r-y-.5, y+.5-(n-r), 0)
            distance = math.hypot(dx, dy)
            if distance <= r:
                outline = distance > r-thickness or min(x, y, n-1-x, n-1-y) < thickness
                img.put(border if outline else fill, (x, y))


def install_material(root, style, c):
    scale = max(1.0, min(2.0, float(root.tk.call("tk", "scaling"))/1.333))
    if not hasattr(root, "_material_images"):
        root._material_images = {}
        root._material_scale = scale
    scale = root._material_scale
    n = 2 * math.ceil(12*scale) + 3
    edge = (n-1)//2
    radius = c["radius"]
    for prefix, accent in (("Material", False), ("MaterialAccent", True)):
        fg = c["accent_text"] if accent else c["text"]
        normal = c["accent"] if accent else c["panel"]
        hover = c["accent_2"] if accent else c["panel_2"]
        border = c["accent"] if accent else c["line"]
        states = {
            "normal": (normal, border), "active": (hover, border),
            "pressed": (hover, c["text"]), "focus": (normal, c["accent_2"] if not accent else c["text"]),
            "disabled": (c["panel_2"], c["line"]),
        }
        for state, (fill, outline) in states.items():
            key = (prefix, state)
            if key not in root._material_images:
                root._material_images[key] = tk.PhotoImage(master=root, width=n, height=n)
            img = root._material_images[key]
            _rounded(img, radius, fill, outline, scale)
        images = root._material_images
        element = prefix + ".border"
        if element not in style.element_names():
            style.element_create(element, "image", images[prefix, "normal"],
                ("disabled", images[prefix, "disabled"]), ("pressed", images[prefix, "pressed"]),
                ("focus", images[prefix, "focus"]), ("active", images[prefix, "active"]),
                border=edge, padding=0, sticky="nswe")
        name = "Accent.TButton" if accent else "TButton"
        style.layout(name, [(element, {"sticky": "nswe", "children": [
            ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
        style.configure(name, foreground=fg, padding=(8, 3), anchor="center")
        style.map(name, foreground=[("disabled", c["muted"])], relief=[])
    style.configure("Dialog.TFrame", background=c["dialog"])
    style.configure("Dialog.TLabel", background=c["dialog"], foreground=c["text"])
    style.configure("DialogMuted.TLabel", background=c["dialog"], foreground=c["muted"])
    style.configure("DialogTitle.TLabel", background=c["dialog"], foreground=c["text"], font=("TkDefaultFont", 14, "bold"))
    style.configure("DialogAccent.TLabel", background=c["dialog"], foreground=c["accent_2"])
    style.configure("Card.TFrame", background=c["panel"])
    style.configure("Card.TLabel", background=c["panel"], foreground=c["text"])


def dialog_surface(win, c):
    win.configure(background=c["dialog"], highlightbackground=c["line"], highlightcolor=c["accent"], highlightthickness=2)
    def walk(w):
        for child in w.winfo_children():
            if isinstance(child, tk.Toplevel):
                continue
            if isinstance(child, ttk.Frame) and not child.cget("style"):
                child.configure(style="Dialog.TFrame")
            elif isinstance(child, ttk.Label) and not child.cget("style"):
                child.configure(style="Dialog.TLabel")
            elif isinstance(child, tk.Canvas):
                child.configure(background=c["dialog"])
            walk(child)
    walk(win)


def card_surface(frame):
    frame.configure(style="Card.TFrame")
    for child in frame.winfo_children():
        if isinstance(child, ttk.Label) and not child.cget("style"):
            child.configure(style="Card.TLabel")
