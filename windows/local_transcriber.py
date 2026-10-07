import os
import re
import sys
import json
import time
import queue
import shutil
import zipfile
import tempfile
import threading
import subprocess
import signal
import ctypes
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except Exception:
    BaseTk = tk.Tk
    DND_FILES = None
    DND_AVAILABLE = False

APP_NAME = "Local Transcriber"
APP_VERSION = "1.0.0"
SUPPORT_URL = "https://paypal.me/gottschn"
SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR / "assets"
APP_ICON_PNG = ASSETS_DIR / "localtranscriber_icon_256.png"
APP_ICON_ICO = ASSETS_DIR / "localtranscriber_icon.ico"
BRAND_MARK_PNG = ASSETS_DIR / "idealvisual_mark_small.png"
APPDATA = Path(os.getenv("LOCALAPPDATA", Path.home())) / "LocalTranscriber"
APPDATA.mkdir(parents=True, exist_ok=True)
BIN_DIR = APPDATA / "bin"
MODEL_DIR = APPDATA / "models"
TEMP_DIR = APPDATA / "temp"
CFG_FILE = APPDATA / "config.json"
MODEL_META_FILE = APPDATA / "model_metadata.json"
for d in (BIN_DIR, MODEL_DIR, TEMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

MODEL_SPECS = {
    "Base": {
        "file": "ggml-base.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
        "size_mb": 142,
        "kind": "Standard",
    },
    "Small": {
        "file": "ggml-small.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
        "size_mb": 466,
        "kind": "Standard",
    },
    "Medium Q5_0": {
        "file": "ggml-medium-q5_0.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin",
        "size_mb": 514,
        "kind": "Quantisiert",
    },
    "Medium": {
        "file": "ggml-medium.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
        "size_mb": 1536,
        "kind": "Standard",
    },
    "Large V3 Turbo Q5_0": {
        "file": "ggml-large-v3-turbo-q5_0.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin",
        "size_mb": 547,
        "kind": "Quantisiert",
    },
    "Large V3 Turbo Q8_0": {
        "file": "ggml-large-v3-turbo-q8_0.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q8_0.bin",
        "size_mb": 834,
        "kind": "Quantisiert",
    },
    "Large V3 Turbo": {
        "file": "ggml-large-v3-turbo.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin",
        "size_mb": 1536,
        "kind": "Standard",
    },
    "Large V3 Q5_0": {
        "file": "ggml-large-v3-q5_0.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-q5_0.bin",
        "size_mb": 1126,
        "kind": "Quantisiert",
    },
    "Large V3": {
        "file": "ggml-large-v3.bin",
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
        "size_mb": 2970,
        "kind": "Standard",
    },
}

RESOURCE_PROFILES = {
    "Schonend": {"threads": 2, "priority": 0x00004000},
    "Ausgeglichen": {"threads": 4, "priority": 0x00004000},
    "Maximal": {"threads": 6, "priority": 0x00000020},
}

AUDIO_EXTS = {
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wma",
    ".mp4", ".mkv", ".mov", ".webm", ".3gp", ".amr"
}
PRECONVERT_EXTS = {".ogg", ".opus", ".amr", ".3gp"}

TS_RE = re.compile(
    r"\[(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+"
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\]"
)

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def cfg_load():
    try:
        return json.loads(CFG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def cfg_save(data):
    try:
        CFG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def model_meta_load():
    try:
        return json.loads(MODEL_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def model_meta_save(data):
    try:
        MODEL_META_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def fmt_time(sec):
    if sec is None:
        return "--:--"
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def ts_seconds(g):
    h, m, s, ms = map(int, g)
    return h * 3600 + m * 60 + s + ms / 1000


def run_hidden(cmd, **kwargs):
    kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)


def detect_hardware():
    data = {
        "nvidia": False,
        "gpu": "Keine unterstützte GPU erkannt",
        "backend": "CPU",
        "cpu": os.environ.get("PROCESSOR_IDENTIFIER", "CPU"),
    }
    try:
        r = run_hidden(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0 and r.stdout.strip():
            data["nvidia"] = True
            data["gpu"] = r.stdout.strip().splitlines()[0]
            data["backend"] = "NVIDIA CUDA empfohlen"
            return data
    except Exception:
        pass
    try:
        ps = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object -ExpandProperty Name"
        )
        r = run_hidden(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=8
        )
        names = [x.strip() for x in r.stdout.splitlines() if x.strip()]
        if names:
            data["gpu"] = " / ".join(names)
    except Exception:
        pass
    return data


def _find_winget_tool(filename):
    roots = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
    ]
    for root in roots:
        if not root.exists():
            continue
        direct = root / filename
        if direct.exists():
            return direct
        try:
            for p in root.rglob(filename):
                if p.is_file():
                    return p
        except Exception:
            pass
    return None


def find_ffmpeg():
    x = shutil.which("ffmpeg.exe") or shutil.which("ffmpeg")
    if x:
        return Path(x)
    x = _find_winget_tool("ffmpeg.exe")
    if x:
        return x
    candidates = list(APPDATA.glob("ffmpeg*/**/ffmpeg.exe"))
    return candidates[0] if candidates else None


def find_ffprobe():
    x = shutil.which("ffprobe.exe") or shutil.which("ffprobe")
    if x:
        return Path(x)
    x = _find_winget_tool("ffprobe.exe")
    if x:
        return x
    candidates = list(APPDATA.glob("ffmpeg*/**/ffprobe.exe"))
    return candidates[0] if candidates else None


def find_whisper(prefer_cuda=False):
    candidates_cuda = [
        BIN_DIR / "cuda" / "whisper-cli.exe",
        BIN_DIR / "cuda" / "Release" / "whisper-cli.exe",
        BIN_DIR / "cuda" / "bin" / "whisper-cli.exe",
    ]
    candidates_cpu = [
        BIN_DIR / "cpu" / "whisper-cli.exe",
        BIN_DIR / "cpu" / "Release" / "whisper-cli.exe",
        BIN_DIR / "cpu" / "bin" / "whisper-cli.exe",
    ]

    ordered = (candidates_cuda + candidates_cpu) if prefer_cuda else (candidates_cpu + candidates_cuda)
    for p in ordered:
        if p.exists():
            return p

    # Fallback recursive scan, still honoring preferred backend.
    preferred_dir = BIN_DIR / ("cuda" if prefer_cuda else "cpu")
    other_dir = BIN_DIR / ("cpu" if prefer_cuda else "cuda")
    for root in (preferred_dir, other_dir):
        if root.exists():
            hits = list(root.rglob("whisper-cli.exe"))
            if hits:
                return hits[0]

    return None



def whisper_build_backend(path):
    if not path:
        return "FEHLT"
    p = str(path).lower().replace("/", "\\")
    return "CUDA" if "\\cuda\\" in p else "CPU"


def cuda_whisper_installed():
    cuda_dir = BIN_DIR / "cuda"
    return cuda_dir.exists() and any(cuda_dir.rglob("whisper-cli.exe"))


def parse_vram_mb(hw):
    try:
        m = re.search(r"(\d+)\s*MiB", hw.get("gpu", ""))
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def recommendation_map(hw):
    vram = parse_vram_mb(hw)
    if hw.get("nvidia") and vram >= 12000:
        return {
            "Large V3 Turbo": "★ Empfohlen",
            "Large V3": "Max. Qualität",
            "Large V3 Q5_0": "Effizient",
            "Large V3 Turbo Q8_0": "Schnell + kompakt",
        }
    if hw.get("nvidia") and vram >= 6000:
        return {
            "Large V3 Turbo Q8_0": "★ Empfohlen",
            "Large V3 Turbo Q5_0": "Effizient",
            "Medium": "Solider Allrounder",
        }
    return {
        "Small": "★ Empfohlen",
        "Medium Q5_0": "Effizient",
        "Medium": "Mehr Qualität / langsamer",
    }


def recommended_models(hw):
    rec = recommendation_map(hw)
    # keep the main recommended choices compact
    preferred = [name for name, label in rec.items() if "Empfohlen" in label or label in ("Max. Qualität", "Effizient")]
    return [name for name in MODEL_SPECS if name in preferred]


def primary_recommended_model(hw):
    rec = recommendation_map(hw)
    for name, label in rec.items():
        if "★ Empfohlen" in label:
            return name
    for name in rec:
        return name
    return "Medium"


class DownloadDialog(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        box = ttk.Frame(self, padding=16)
        box.pack(fill="both", expand=True)

        self.label = ttk.Label(box, text="Bitte warten …", width=62)
        self.label.pack(fill="x")

        self.progress = ttk.Progressbar(box, maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(10, 6))

        self.detail = ttk.Label(box, text="", foreground="#666")
        self.detail.pack(fill="x")

        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self.grab_set()

    def update_progress(self, label, percent=None, detail=""):
        if not self.winfo_exists():
            return
        self.label.config(text=label)
        self.detail.config(text=detail or "")

        if percent is None:
            self.progress.config(mode="indeterminate")
            try:
                self.progress.start(12)
            except Exception:
                pass
        else:
            try:
                self.progress.stop()
            except Exception:
                pass
            self.progress.config(mode="determinate")
            self.progress["value"] = max(0, min(100, float(percent)))

        self.update_idletasks()



class App(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.theme_name = cfg_load().get("theme", "dark")  # fresh install default: dark
        if self.theme_name not in ("dark", "light"):
            self.theme_name = "dark"
        self.setup_brand_theme()
        self.load_brand_assets()
        self.protocol("WM_DELETE_WINDOW", self.on_close_request)
        self.geometry("1140x820")
        self.minsize(980, 700)

        self.cfg = cfg_load()
        if self.cfg.get("audio_mode") in ("Automatisch (M4A/AAC)", "Automatisch (AAC/M4A)"):
            self.cfg["audio_mode"] = "Automatisch (FLAC)"
            cfg_save(self.cfg)

        self.hw = detect_hardware()
        self.whisper = find_whisper(prefer_cuda=self.hw.get("nvidia", False))
        self.ffmpeg = find_ffmpeg()
        self.ffprobe = find_ffprobe()
        self.items = []
        self.proc = None
        self.worker = None
        self.cancel = False
        self.paused = False
        self.custom_output = Path(self.cfg["custom_output"]) if self.cfg.get("custom_output") else None

        self.build_ui()
        self.refresh_models()
        self.refresh_component_status()

        self.after(500, self.first_run_check)


    def load_brand_assets(self):
        self.app_icon_img = None
        self.brand_mark_img = None
        try:
            if APP_ICON_PNG.exists():
                self.app_icon_img = tk.PhotoImage(file=str(APP_ICON_PNG))
                self.iconphoto(True, self.app_icon_img)
        except Exception:
            pass
        try:
            if sys.platform.startswith("win") and APP_ICON_ICO.exists():
                self.iconbitmap(str(APP_ICON_ICO))
        except Exception:
            pass
        try:
            if BRAND_MARK_PNG.exists():
                _brand_src = tk.PhotoImage(file=str(BRAND_MARK_PNG))
                # Compact header mark: approximately the visual height of
                # "Local Transcriber" + "by IDEALVISUAL", without changing
                # the underlying approved artwork.
                self.brand_mark_img = _brand_src.subsample(2, 2)
                self._brand_src_img = _brand_src
        except Exception:
            self.brand_mark_img = None

    def setup_brand_theme(self):
        if getattr(self, "theme_name", "dark") == "light":
            self.colors = {
                "bg": "#f4f7fa",
                "panel": "#ffffff",
                "panel_2": "#e8eef4",
                "line": "#c8d3de",
                "text": "#182330",
                "muted": "#64778a",
                "accent": "#00aeef",
                "accent_2": "#007db2",
            }
            disabled = "#98a5b2"
            accent_text = "#ffffff"
        else:
            self.colors = {
                "bg": "#121821",
                "panel": "#1a2230",
                "panel_2": "#202b3c",
                "line": "#2c3a4d",
                "text": "#edf2f7",
                "muted": "#8fa3b8",
                "accent": "#00aeef",
                "accent_2": "#48d4ff",
            }
            disabled = "#66788b"
            accent_text = "#0d141d"

        try:
            self.configure(bg=self.colors["bg"])
        except Exception:
            pass

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"])
        style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 22, "bold"))
        style.configure("BrandTag.TLabel", background=self.colors["bg"], foreground=self.colors["accent_2"], font=("Segoe UI", 9, "bold"))
        style.configure("HeaderIcon.TLabel", background=self.colors["bg"])
        style.configure("Main.Horizontal.TProgressbar", thickness=14)

        style.configure(
            "TLabelframe",
            background=self.colors["bg"],
            bordercolor=self.colors["line"],
            relief="solid",
        )
        style.configure(
            "TLabelframe.Label",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "TButton",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            bordercolor=self.colors["line"],
            focusthickness=1,
            focuscolor=self.colors["accent"],
        )
        style.map(
            "TButton",
            background=[("active", self.colors["panel_2"])],
            foreground=[("disabled", disabled)],
        )

        style.configure(
            "Accent.TButton",
            background=self.colors["accent"],
            foreground=accent_text,
            bordercolor=self.colors["accent"],
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.colors["accent_2"])],
            foreground=[("active", accent_text)],
        )

        style.configure("TRadiobutton", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TCheckbutton", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure(
            "TEntry",
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            bordercolor=self.colors["line"],
            insertcolor=self.colors["text"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=self.colors["panel"],
            background=self.colors["panel"],
            foreground=self.colors["text"],
            arrowsize=14,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["panel"])],
            foreground=[("readonly", self.colors["text"])],
            selectbackground=[("readonly", self.colors["panel"])],
            selectforeground=[("readonly", self.colors["text"])],
        )

        style.configure(
            "Treeview",
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            bordercolor=self.colors["line"],
            rowheight=26,
        )
        style.map(
            "Treeview",
            background=[("selected", self.colors["accent"])],
            foreground=[("selected", accent_text)],
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["panel_2"],
            foreground=self.colors["text"],
            bordercolor=self.colors["line"],
            font=("Segoe UI", 9, "bold"),
        )

        style.configure(
            "TScrollbar",
            background=self.colors["panel"],
            troughcolor=self.colors["bg"],
            bordercolor=self.colors["line"],
            arrowcolor=self.colors["text"],
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=self.colors["accent"],
            troughcolor=self.colors["panel"],
            bordercolor=self.colors["line"],
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
        )
        style.configure("TSeparator", background=self.colors["line"])

        # Native text area needs direct recoloring.
        if hasattr(self, "log"):
            try:
                self.log.configure(
                    bg=self.colors["panel"],
                    fg=self.colors["text"],
                    insertbackground=self.colors["text"],
                    selectbackground=self.colors["accent"],
                    selectforeground=accent_text,
                    highlightbackground=self.colors["line"],
                    highlightcolor=self.colors["accent"],
                )
            except Exception:
                pass

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        current = cfg_load()
        current["theme"] = self.theme_name
        cfg_save(current)
        self.setup_brand_theme()
        if hasattr(self, "theme_btn"):
            self.theme_btn.configure(
                text="🌙 Dunkel" if self.theme_name == "light" else "☀ Hell"
            )


    def build_ui(self):
        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        hdr = ttk.Frame(main)
        hdr.pack(fill="x")

        left_hdr = ttk.Frame(hdr)
        left_hdr.pack(side="left", fill="x", expand=True)

        if getattr(self, "brand_mark_img", None):
            ttk.Label(left_hdr, image=self.brand_mark_img, style="HeaderIcon.TLabel").pack(side="left", padx=(2, 10), pady=(2, 2))

        text_hdr = ttk.Frame(left_hdr)
        text_hdr.pack(side="left", fill="x", expand=True)
        ttk.Label(text_hdr, text="Local Transcriber", style="Title.TLabel").pack(anchor="w")
        ttk.Label(text_hdr, text="by IDEALVISUAL", style="BrandTag.TLabel").pack(anchor="w", pady=(1, 0))

        self.hw_label = ttk.Label(
            hdr,
            text=f"{self.hw['gpu']} • {self.hw['backend']}",
            style="Muted.TLabel"
        )
        self.hw_label.pack(side="right")

        ttk.Button(
            hdr,
            text="♥ Projekt unterstützen",
            command=self.open_support
        ).pack(side="right", padx=(0, 10))
        ttk.Button(
            hdr,
            text="Über",
            command=self.show_about
        ).pack(side="right", padx=(0, 6))

        self.theme_btn = ttk.Button(
            hdr,
            text="🌙 Dunkel" if self.theme_name == "light" else "☀ Hell",
            command=self.toggle_theme
        )
        self.theme_btn.pack(side="right", padx=(0, 6))

        ttk.Label(
            main,
            text="Lokale Stapeltranskription • Drag & Drop • whisper.cpp • automatische Audioaufbereitung",
            style="Muted.TLabel"
        ).pack(fill="x", pady=(4, 12))


        # Always-visible action bar. It is packed first from the bottom so
        # expandable content above cannot push the buttons off-screen.
        action_bar = ttk.Frame(main, padding=(0, 8, 0, 0))
        action_bar.pack(side="bottom", fill="x")
        ttk.Separator(action_bar, orient="horizontal").pack(fill="x", pady=(0, 8))

        self.start_btn = ttk.Button(
            action_bar,
            text="▶ Transkribieren",
            command=self.start,
            style="Accent.TButton"
        )
        self.start_btn.pack(side="left")

        self.pause_btn = ttk.Button(
            action_bar,
            text="⏸ Pause",
            command=self.toggle_pause,
            state="disabled"
        )
        self.pause_btn.pack(side="left", padx=(8, 0))

        self.stop_btn = ttk.Button(
            action_bar,
            text="Abbrechen",
            command=self.stop,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=8)

        self.footer_model = ttk.Label(action_bar, text="")
        self.footer_model.pack(side="right")

        # Always-visible progress area. It is outside the resizable queue/log
        # panes so it can never disappear when the queue is made smaller.
        progress_area = ttk.Frame(main)
        progress_area.pack(side="bottom", fill="x", pady=(5, 3))
        self.progress = ttk.Progressbar(
            progress_area,
            maximum=100,
            mode="determinate",
            style="Main.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x")
        self.status = ttk.Label(progress_area, text="Bereit")
        self.status.pack(fill="x", pady=(3, 0))

        # Setup/component area
        setup = ttk.LabelFrame(main, text="System & Modelle")
        setup.pack(fill="x", pady=(0, 9))
        sr = ttk.Frame(setup, padding=8)
        sr.pack(fill="x")
        self.whisper_status = ttk.Label(sr)
        self.whisper_status.pack(side="left", padx=(0, 18))
        self.ffmpeg_status = ttk.Label(sr)
        self.ffmpeg_status.pack(side="left", padx=(0, 18))
        self.backend_status = ttk.Label(sr, text="")
        self.backend_status.pack(side="left", padx=(0, 18))
        self.runtime_status = ttk.Label(sr, text="Laufzeit: noch nicht gestartet")
        self.runtime_status.pack(side="left", padx=(0, 18))
        ttk.Button(sr, text="Alles automatisch einrichten", command=self.auto_setup).pack(side="right")
        ttk.Button(sr, text="Komponenten prüfen", command=self.refresh_component_status).pack(side="right", padx=6)

        # file area
        fbox = ttk.LabelFrame(main, text="Dateien")
        fbox.pack(fill="x", pady=(0, 9))
        fi = ttk.Frame(fbox, padding=15)
        fi.pack(fill="x")
        ttk.Label(
            fi,
            text="Audio-/Videodateien hier hineinziehen oder über „Dateien hinzufügen“ auswählen",
            anchor="center"
        ).pack(fill="x")
        ttk.Button(fi, text="Dateien hinzufügen", command=self.add_files_dialog).pack(pady=(8, 0))

        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Modell:").pack(side="left")
        saved_model = self.cfg.get("model")
        recommended_model = primary_recommended_model(self.hw)
        if not self.cfg.get("recommendation_initialized_v26"):
            initial_model = recommended_model
            self.cfg["model"] = initial_model
            self.cfg["recommendation_initialized_v26"] = True
            cfg_save(self.cfg)
        else:
            initial_model = saved_model or recommended_model
        self.model_var = tk.StringVar(value=initial_model)
        self.model_combo = ttk.Combobox(row, textvariable=self.model_var, state="readonly", width=24)
        self.model_combo.pack(side="left", padx=(5, 5))
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)
        self.model_hint = ttk.Label(row, text="")
        self.model_hint.pack(side="left", padx=(0, 6))
        ttk.Button(
            row,
            text="Empfohlen verwenden",
            command=self.select_recommended_model
        ).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Modell verwalten…", command=self.model_manager).pack(side="left", padx=(0, 12))

        ttk.Label(row, text="Sprache:").pack(side="left")
        self.lang_var = tk.StringVar(value=self.cfg.get("language", "Deutsch"))
        ttk.Combobox(
            row, textvariable=self.lang_var,
            values=["Deutsch", "Auto", "Englisch"],
            state="readonly", width=12
        ).pack(side="left", padx=(5, 12))

        ttk.Label(row, text="Leistungsmodus:").pack(side="left")
        self.profile_var = tk.StringVar(value=self.cfg.get("profile", "Ausgeglichen"))
        self.profile_combo = ttk.Combobox(
            row, textvariable=self.profile_var,
            values=list(RESOURCE_PROFILES), state="readonly", width=16
        )
        self.profile_combo.pack(side="left", padx=(5, 5))
        self.profile_info = ttk.Label(row, text="")
        self.profile_info.pack(side="left")
        self.profile_combo.bind("<<ComboboxSelected>>", lambda e: self.profile_changed())
        self.profile_changed()

        # Output location
        ob = ttk.LabelFrame(main, text="Speicherort")
        ob.pack(fill="x", pady=(0, 8))
        orow = ttk.Frame(ob, padding=8)
        orow.pack(fill="x")
        self.dest_var = tk.StringVar(value=self.cfg.get("dest_mode", "subfolder"))
        ttk.Radiobutton(orow, text="Gleicher Ordner", variable=self.dest_var, value="same").pack(side="left")
        ttk.Radiobutton(orow, text="Unterordner „transkripte“", variable=self.dest_var, value="subfolder").pack(side="left", padx=8)
        ttk.Radiobutton(orow, text="Benutzerdefiniert", variable=self.dest_var, value="custom").pack(side="left")
        ttk.Button(orow, text="Ordner wählen…", command=self.choose_output).pack(side="left", padx=(12, 6))
        self.out_label = ttk.Label(orow, text=str(self.custom_output) if self.custom_output else "Noch kein Zielordner gewählt")
        self.out_label.pack(side="left", fill="x", expand=True)

        # Audio preparation
        ab = ttk.LabelFrame(main, text="Audioaufbereitung")
        ab.pack(fill="x", pady=(0, 8))
        ar = ttk.Frame(ab, padding=8)
        ar.pack(fill="x")

        ttk.Label(ar, text="Modus:").pack(side="left")

        saved_audio_mode = self.cfg.get("audio_mode", "Automatisch (FLAC)")
        if saved_audio_mode not in (
            "Automatisch (FLAC)",
            "WAV verlustfrei",
            "MP3 kompatibel",
            "Original verwenden",
        ):
            saved_audio_mode = "Automatisch (FLAC)"
            self.cfg["audio_mode"] = saved_audio_mode
            cfg_save(self.cfg)
        self.audio_mode_var = tk.StringVar(value=saved_audio_mode)
        self.audio_mode_combo = ttk.Combobox(
            ar,
            textvariable=self.audio_mode_var,
            values=[
                "Automatisch (FLAC)",
                "WAV verlustfrei",
                "MP3 kompatibel",
                "Original verwenden"
            ],
            state="readonly",
            width=22
        )
        self.audio_mode_combo.pack(side="left", padx=(6, 14))

        self.keep_converted_var = tk.BooleanVar(
            value=self.cfg.get("keep_converted", False)
        )
        ttk.Checkbutton(
            ar,
            text="Konvertierte Audiodatei behalten",
            variable=self.keep_converted_var
        ).pack(side="left")

        self.audio_info_label = ttk.Label(
            ar,
            text="Auto: problematische Formate → FLAC, danach temporäre Datei löschen"
        )
        self.audio_info_label.pack(side="left", padx=(14, 0))

        self.audio_mode_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.update_audio_mode_info()
        )

        # Flexible queue / live-output split.
        # The divider can be dragged vertically so the live log remains visible
        # on smaller screens, while the queue can be reduced as needed.
        self.main_paned = ttk.Panedwindow(main, orient="vertical")
        self.main_paned.pack(fill="both", expand=True, pady=(0, 8))

        queue_panel = ttk.Frame(self.main_paned)
        live_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(queue_panel, weight=3)
        self.main_paned.add(live_panel, weight=2)

        # Queue
        table = ttk.Frame(queue_panel)
        table.pack(fill="both", expand=True)
        cols = ("file", "duration", "status", "output")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=7)
        for c, t, w in [
            ("file", "Datei", 340),
            ("duration", "Dauer", 80),
            ("status", "Status", 130),
            ("output", "Ausgabe", 390),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center" if c in ("duration", "status") else "w")
        ys = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ys.pack(side="right", fill="y")

        act = ttk.Frame(queue_panel)
        act.pack(fill="x", pady=(6, 8))
        ttk.Button(act, text="Ausgewählte entfernen", command=self.remove_selected).pack(side="left")
        ttk.Button(act, text="Liste leeren", command=self.clear_list).pack(side="left", padx=6)
        ttk.Label(act, text="Ausgabe:").pack(side="left", padx=(16, 4))
        self.txt = tk.BooleanVar(value=True)
        self.srt = tk.BooleanVar(value=True)
        self.vtt = tk.BooleanVar(value=True)
        ttk.Checkbutton(act, text="TXT", variable=self.txt).pack(side="left")
        ttk.Checkbutton(act, text="SRT", variable=self.srt).pack(side="left")
        ttk.Checkbutton(act, text="VTT", variable=self.vtt).pack(side="left")

        logbox = ttk.LabelFrame(live_panel, text="Live-Ausgabe")
        logbox.pack(fill="both", expand=True)
        self.log = tk.Text(
            logbox,
            height=6,
            state="disabled",
            wrap="word",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground=self.colors["accent"],
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
            relief="flat",
        )
        log_scroll = ttk.Scrollbar(logbox, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        log_scroll.pack(side="right", fill="y", padx=(0, 6), pady=6)

        # Give both panes useful space initially; the user can drag the divider.
        self.after(350, self.set_initial_split)

        self.enable_dnd()

    def set_initial_split(self):
        try:
            h = self.main_paned.winfo_height()
            if h > 160:
                self.main_paned.sashpos(0, max(90, int(h * 0.58)))
        except Exception:
            pass

    def _suspend_process(self):
        if not self.proc or self.proc.poll() is not None:
            return False
        try:
            if os.name == "nt":
                PROCESS_SUSPEND_RESUME = 0x0800
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_SUSPEND_RESUME, False, self.proc.pid
                )
                if not handle:
                    return False
                try:
                    status = ctypes.windll.ntdll.NtSuspendProcess(handle)
                    return status == 0
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(self.proc.pid, signal.SIGSTOP)
                return True
        except Exception as e:
            self.log_line(f"Pause fehlgeschlagen: {e}\n")
            return False

    def _resume_process(self):
        if not self.proc or self.proc.poll() is not None:
            return False
        try:
            if os.name == "nt":
                PROCESS_SUSPEND_RESUME = 0x0800
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_SUSPEND_RESUME, False, self.proc.pid
                )
                if not handle:
                    return False
                try:
                    status = ctypes.windll.ntdll.NtResumeProcess(handle)
                    return status == 0
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(self.proc.pid, signal.SIGCONT)
                return True
        except Exception as e:
            self.log_line(f"Fortsetzen fehlgeschlagen: {e}\n")
            return False

    def toggle_pause(self):
        if not self.proc or self.proc.poll() is not None:
            return

        if self.paused:
            if self._resume_process():
                self.paused = False
                self.pause_btn.config(text="⏸ Pause")
                self.ui_status("Transkription läuft weiter …")
                self.log_line("\n--- Fortgesetzt ---\n")
        else:
            if self._suspend_process():
                self.paused = True
                self.pause_btn.config(text="▶ Fortsetzen")
                self.ui_status("Pausiert.")
                self.log_line("\n--- Pausiert ---\n")

    def open_support(self):
        try:
            webbrowser.open(SUPPORT_URL, new=2)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Support-Link konnte nicht geöffnet werden:\n{e}")

    def show_about(self):
        backend = whisper_build_backend(self.whisper)
        messagebox.showinfo(
            f"Über {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\n"
            "by IDEALVISUAL\n\n"
            "Lokale Audio-/Video-Transkription mit whisper.cpp.\n"
            f"Aktiver Build: {backend}\n"
            f"Hardware: {self.hw.get('gpu', 'Unbekannt')}\n\n"
            "Alle Transkriptionen erfolgen lokal auf diesem Computer.\n\n"
            "Local Transcriber ist kostenlos. Wenn dir das Tool hilft,\n"
            "kannst du die Weiterentwicklung freiwillig unterstützen.\n\n"
            "Projekt unterstützen:\n"
            f"{SUPPORT_URL}"
        )

    def on_close_request(self):
        running = bool(getattr(self, "proc", None) and self.proc.poll() is None)

        if running:
            msg = (
                "Es läuft gerade eine Transkription.\n\n"
                "Wenn du Local Transcriber jetzt schließt, wird der laufende Vorgang abgebrochen.\n\n"
                "Wirklich beenden?"
            )
        else:
            msg = "Local Transcriber wirklich beenden?"

        if not messagebox.askyesno(APP_NAME, msg):
            return

        if running:
            try:
                self.cancel = True
                if self.paused:
                    self._resume_process()
                    self.paused = False
                self.proc.terminate()
            except Exception:
                pass

        try:
            self.destroy()
        except Exception:
            pass

    def enable_dnd(self):
        if not DND_AVAILABLE:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self.on_drop)
        except Exception as e:
            self.log_line(f"Drag & Drop konnte nicht aktiviert werden: {e}\n")

    def first_run_check(self):
        cuda_missing = (
            self.hw.get("nvidia", False)
            and (not self.whisper or "cuda" not in str(self.whisper).lower())
        )
        if not self.whisper or not self.ffmpeg or cuda_missing:
            if messagebox.askyesno(
                APP_NAME,
                "Die benötigten Komponenten sind noch nicht vollständig eingerichtet.\n\n"
                "Soll Local Transcriber whisper.cpp und FFmpeg jetzt automatisch einrichten?"
            ):
                self.auto_setup()

    def refresh_component_status(self):
        self.whisper = find_whisper(prefer_cuda=self.hw.get("nvidia", False))
        self.ffmpeg = find_ffmpeg()
        self.ffprobe = find_ffprobe()
        if self.whisper:
            backend_name = whisper_build_backend(self.whisper)
            self.whisper_status.config(text=f"Whisper: ✓ installiert ({backend_name})")
        else:
            backend_name = "FEHLT"
            self.whisper_status.config(text="Whisper: ✗ fehlt")

        self.ffmpeg_status.config(text="FFmpeg: ✓ installiert" if self.ffmpeg else "FFmpeg: ✗ fehlt")

        if self.hw.get("nvidia"):
            if backend_name == "CUDA":
                self.backend_status.config(text="Backend gewählt: CUDA ✓")
            else:
                self.backend_status.config(text="Backend gewählt: CPU ⚠ CUDA verfügbar")
        else:
            self.backend_status.config(text="Backend gewählt: CPU")

        self.refresh_models()
        self.profile_changed()

    def github_releases(self):
        url = "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=20"
        last_error = None

        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "LocalTranscriber/2.4.1",
                        "Accept": "application/vnd.github+json",
                        "Accept-Encoding": "identity",
                        "Connection": "close",
                    }
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)
            except Exception as e:
                last_error = e
                time.sleep(attempt * 2)

        curl = shutil.which("curl.exe") or shutil.which("curl")
        if curl:
            r = run_hidden(
                [
                    curl, "-L", "--fail", "--silent", "--show-error",
                    "--retry", "4", "--retry-delay", "2",
                    "-H", "User-Agent: LocalTranscriber/2.4.1",
                    "-H", "Accept: application/vnd.github+json",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=180
            )
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout)
            last_error = RuntimeError(r.stderr.strip() or "curl lieferte keine Daten")

        raise RuntimeError(
            "GitHub konnte nach mehreren Versuchen nicht erreicht werden.\\n\\n"
            f"Letzter Fehler: {last_error}"
        )

    def choose_whisper_release_asset(self):
        releases = self.github_releases()
        want_cuda = bool(self.hw.get("nvidia"))

        cpu_patterns = [
            re.compile(r"^whisper-bin-x64\.zip$", re.I),
            re.compile(r"^whisper-bin-win-(?:cpu-)?x64\.zip$", re.I),
        ]

        cuda_patterns = [
            # Current release naming, e.g. whisper-bin-win-cuda-12.4-x64.zip
            re.compile(r"^whisper-bin-win-cuda-.*-x64\.zip$", re.I),
            # Older official naming, e.g. whisper-cublas-12.4.0-bin-x64.zip
            re.compile(r"^whisper-cublas-.*-bin-x64\.zip$", re.I),
        ]

        candidates = []

        for rel in releases:
            tag = rel.get("tag_name") or rel.get("name") or "unknown"
            assets = rel.get("assets") or []

            for asset in assets:
                name = asset.get("name", "")
                url = asset.get("browser_download_url")
                if not url:
                    continue

                if want_cuda:
                    for p in cuda_patterns:
                        if p.match(name):
                            # Prefer stable releases, then newer naming.
                            score = 0
                            if not rel.get("prerelease"):
                                score += 100
                            if name.lower().startswith("whisper-bin-win-cuda-"):
                                score += 20

                            # Prefer CUDA 12.x for broad RTX 30 compatibility.
                            if re.search(r"cuda[-_]?12", name, re.I) or re.search(r"cublas[-_]?12", name, re.I):
                                score += 10

                            candidates.append((score, tag, asset, "CUDA"))
                            break
                else:
                    for p in cpu_patterns:
                        if p.match(name):
                            score = 100 if not rel.get("prerelease") else 0
                            candidates.append((score, tag, asset, "CPU"))
                            break

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, tag, asset, backend = candidates[0]
            return tag, asset, backend

        # Helpful diagnostic showing what x64 ZIP assets were actually found.
        found = []
        for rel in releases[:8]:
            for asset in (rel.get("assets") or []):
                name = asset.get("name", "")
                if name.lower().endswith("x64.zip"):
                    found.append(name)

        expected = "CUDA" if want_cuda else "CPU"
        details = "\n".join(found[:20]) if found else "(keine x64-ZIP-Assets gefunden)"

        raise RuntimeError(
            f"NVIDIA-GPU erkannt, aber aktuell wurde kein passender {expected}-Build "
            f"von whisper.cpp gefunden.\n\n"
            f"Gefundene x64-Assets:\n{details}"
        )


    def download_url(self, url, target, dlg, label):
        target = Path(target)
        last_error = None

        for attempt in range(1, 4):
            try:
                if target.exists():
                    target.unlink()

                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "LocalTranscriber/2.4.1",
                        "Accept-Encoding": "identity",
                        "Connection": "close",
                    }
                )
                with urllib.request.urlopen(req, timeout=90) as r, open(target, "wb") as f:
                    total = int(r.headers.get("Content-Length", 0) or 0)
                    done = 0
                    while True:
                        chunk = r.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        pct = (done / total * 100) if total else None
                        detail = (
                            f"{done/1024/1024:.0f} MB / {total/1024/1024:.0f} MB"
                            if total else f"{done/1024/1024:.0f} MB"
                        )
                        self.after(0, dlg.update_progress, label, pct, detail)

                if target.exists() and target.stat().st_size > 0:
                    return

            except Exception as e:
                last_error = e
                try:
                    if target.exists():
                        target.unlink()
                except Exception:
                    pass
                self.after(
                    0, dlg.update_progress,
                    f"{label} – neuer Versuch {attempt}/3 …",
                    None,
                    str(e)[:140]
                )
                time.sleep(attempt * 2)

        curl = shutil.which("curl.exe") or shutil.which("curl")
        if curl:
            self.after(0, dlg.update_progress, f"{label} – Windows-curl Fallback …", None, "")
            r = run_hidden(
                [
                    curl, "-L", "--fail", "--show-error",
                    "--retry", "5", "--retry-all-errors",
                    "--retry-delay", "2",
                    "-A", "LocalTranscriber/2.4.1",
                    "-o", str(target),
                    url
                ],
                capture_output=True,
                text=True,
                timeout=1800
            )
            if r.returncode == 0 and target.exists() and target.stat().st_size > 0:
                self.after(0, dlg.update_progress, label, 100, "Download abgeschlossen")
                return
            last_error = RuntimeError(r.stderr.strip() or "curl-Download fehlgeschlagen")

        raise RuntimeError(
            "Download nach mehreren Versuchen fehlgeschlagen.\\n\\n"
            f"Quelle: {url}\\n"
            f"Letzter Fehler: {last_error}"
        )

    def auto_setup(self):
        dlg = DownloadDialog(self, "Automatische Einrichtung")
        self.runtime_status.config(text="Einrichtung: Komponenten werden geprüft …")

        def worker():
            try:
                want_cuda = bool(self.hw.get("nvidia"))
                current = find_whisper(prefer_cuda=want_cuda)

                need_whisper = current is None
                if want_cuda and not cuda_whisper_installed():
                    need_whisper = True

                if need_whisper:
                    self.after(0, dlg.update_progress, "Prüfe whisper.cpp Releases…", None, "")
                    tag, asset, backend = self.choose_whisper_release_asset()

                    if want_cuda and backend != "CUDA":
                        raise RuntimeError(
                            "NVIDIA-GPU erkannt, aber aktuell wurde kein passender "
                            "CUDA-Build von whisper.cpp gefunden."
                        )

                    z = TEMP_DIR / "whisper.zip"
                    self.download_url(
                        asset["browser_download_url"],
                        z,
                        dlg,
                        f"whisper.cpp {tag} ({backend}) wird geladen…"
                    )

                    dest = BIN_DIR / backend.lower()
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    dest.mkdir(parents=True, exist_ok=True)

                    with zipfile.ZipFile(z, "r") as zz:
                        zz.extractall(dest)

                    try:
                        z.unlink()
                    except Exception:
                        pass

                    current = find_whisper(prefer_cuda=want_cuda)
                    if not current:
                        raise RuntimeError(
                            "whisper.cpp wurde geladen, aber whisper-cli.exe wurde nicht gefunden."
                        )

                    if want_cuda and whisper_build_backend(current) != "CUDA":
                        raise RuntimeError(
                            "CUDA-Build wurde angefordert, aber Local Transcriber findet "
                            "weiterhin nur den CPU-Build."
                        )

                if not find_ffmpeg():
                    self.after(0, dlg.update_progress, "Installiere FFmpeg…", None, "Winget wird verwendet")
                    winget = shutil.which("winget.exe") or shutil.which("winget")
                    if winget:
                        r = run_hidden(
                            [winget, "install", "--id", "Gyan.FFmpeg", "-e",
                             "--accept-source-agreements", "--accept-package-agreements",
                             "--silent"],
                            capture_output=True, text=True
                        )
                        if r.returncode not in (0,) and not find_ffmpeg():
                            raise RuntimeError(
                                "FFmpeg konnte über Winget nicht eingerichtet werden.\n\n"
                                + (r.stdout or "")[-1500:]
                                + "\n"
                                + (r.stderr or "")[-1500:]
                            )
                    else:
                        raise RuntimeError("FFmpeg fehlt und Winget wurde nicht gefunden.")

                self.whisper = find_whisper(prefer_cuda=want_cuda)
                self.ffmpeg = find_ffmpeg()
                self.ffprobe = find_ffprobe()

                selected_backend = whisper_build_backend(self.whisper)
                self.after(0, dlg.destroy)
                self.after(0, self.refresh_component_status)
                self.after(
                    0,
                    lambda b=selected_backend: self.runtime_status.config(
                        text=f"Einrichtung fertig: {b}"
                    )
                )
                self.after(0, self.setup_done_message)

            except Exception as e:
                err = str(e)
                self.after(0, dlg.destroy)
                self.after(
                    0,
                    lambda: self.runtime_status.config(text="Einrichtung fehlgeschlagen")
                )
                self.after(0, lambda err=err: messagebox.showerror(
                    APP_NAME,
                    f"Automatische Einrichtung fehlgeschlagen:\n\n{err}"
                ))

        threading.Thread(target=worker, daemon=True).start()

    def setup_done_message(self):
        self.refresh_component_status()
        msg = "Komponenten wurden eingerichtet."
        if self.hw["nvidia"]:
            msg += "\n\nNVIDIA-GPU erkannt: ein CUDA-Build wird bevorzugt, sofern verfügbar."
        else:
            msg += "\n\nCPU-Build ist aktiv."
        if not self.ffmpeg:
            msg += "\n\nHinweis: FFmpeg wurde installiert, aber noch nicht gefunden. "
            msg += "In diesem Fall Local Transcriber einmal neu starten."
        messagebox.showinfo(APP_NAME, msg)

    def remote_model_info(self, url):
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "LocalTranscriber"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            headers = r.headers
            size = headers.get("Content-Length")
            etag = headers.get("ETag")
            modified = headers.get("Last-Modified")
            return {
                "size": int(size) if size and str(size).isdigit() else None,
                "etag": etag,
                "last_modified": modified,
                "final_url": r.geturl(),
            }

    def check_model_update(self, name, spec, status_label=None, button=None):
        target = MODEL_DIR / spec["file"]
        if not target.exists():
            if status_label:
                status_label.config(text="nicht installiert")
            return

        if status_label:
            status_label.config(text="prüfe…")
        if button:
            button.config(state="disabled")

        def worker():
            try:
                remote = self.remote_model_info(spec["url"])
                local_size = target.stat().st_size
                meta = model_meta_load().get(name, {})

                update_available = False
                reason = ""

                if remote.get("size") and remote["size"] != local_size:
                    update_available = True
                    reason = "Dateigröße geändert"
                elif remote.get("etag") and meta.get("etag") and remote["etag"] != meta["etag"]:
                    update_available = True
                    reason = "Remote-Version geändert"
                elif remote.get("last_modified") and meta.get("last_modified") and remote["last_modified"] != meta["last_modified"]:
                    update_available = True
                    reason = "Remote-Datum geändert"

                if not meta:
                    # Older installs have no metadata; matching size is the best safe signal.
                    if remote.get("size") and remote["size"] == local_size:
                        status = "✓ installiert / wahrscheinlich aktuell"
                    else:
                        status = "✓ installiert / Update-Status unbekannt"
                elif update_available:
                    status = f"⬆ Update verfügbar ({reason})"
                else:
                    status = "✓ aktuell"

                self.after(0, lambda s=status: status_label.config(text=s) if status_label else None)
            except Exception as e:
                err = str(e)
                if status_label:
                    self.after(0, lambda err=err: status_label.config(text=f"Prüfung fehlgeschlagen"))
            finally:
                if button:
                    self.after(0, lambda: button.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def uninstall_model(self, name, spec, parent=None):
        target = MODEL_DIR / spec["file"]
        if not target.exists():
            messagebox.showinfo(APP_NAME, f"{name} ist nicht installiert.")
            return

        if not messagebox.askyesno(
            APP_NAME,
            f"{name} wirklich deinstallieren?\n\n"
            f"Datei:\n{target}"
        ):
            return

        try:
            target.unlink()
            meta = model_meta_load()
            meta.pop(name, None)
            model_meta_save(meta)
            self.refresh_models()
            if parent:
                parent.destroy()
                self.model_manager()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Deinstallation fehlgeschlagen:\n{e}")

    def update_model(self, name, spec, parent=None):
        target = MODEL_DIR / spec["file"]
        dlg = DownloadDialog(self, f"Modell aktualisieren: {name}")
        tmp = target.with_suffix(target.suffix + ".update")

        def worker():
            try:
                remote = self.remote_model_info(spec["url"])
                self.download_url(spec["url"], tmp, dlg, f"{name} wird aktualisiert…")

                # Basic integrity sanity check
                if not tmp.exists() or tmp.stat().st_size < 1024 * 1024:
                    raise RuntimeError("Die heruntergeladene Modelldatei ist unvollständig.")

                tmp.replace(target)

                meta = model_meta_load()
                meta[name] = {
                    "etag": remote.get("etag"),
                    "last_modified": remote.get("last_modified"),
                    "size": target.stat().st_size,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                model_meta_save(meta)

                self.after(0, dlg.destroy)
                self.after(0, self.refresh_models)
                if parent:
                    self.after(0, parent.destroy)
                self.after(0, lambda: messagebox.showinfo(APP_NAME, f"{name} wurde aktualisiert."))
            except Exception as e:
                err = str(e)
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
                self.after(0, dlg.destroy)
                self.after(0, lambda err=err: messagebox.showerror(
                    APP_NAME, f"Modell-Update fehlgeschlagen:\n{err}"
                ))

        threading.Thread(target=worker, daemon=True).start()

    def model_manager(self):
        win = tk.Toplevel(self)
        win.title("Modelle verwalten")
        win.geometry("900x590")
        win.transient(self)

        frm = ttk.Frame(win, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Whisper-Modelle", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            frm,
            text=f"Hardware: {self.hw['gpu']} • Empfehlungen werden automatisch angepasst."
        ).pack(anchor="w")
        ttk.Label(
            frm,
            text="Das Fenster bleibt beim Installieren, Aktualisieren und Deinstallieren geöffnet."
        ).pack(anchor="w", pady=(0, 10))

        bulk = ttk.Frame(frm)
        bulk.pack(fill="x", pady=(0, 10))

        ttk.Button(
            bulk,
            text="Empfohlene Modelle installieren",
            command=lambda: self.install_model_group(
                recommended_models(self.hw),
                "Empfohlene Modelle",
                rebuild
            )
        ).pack(side="left")

        ttk.Button(
            bulk,
            text="Alle Modelle installieren",
            command=lambda: self.install_model_group(
                list(MODEL_SPECS.keys()),
                "Alle Modelle",
                rebuild
            )
        ).pack(side="left", padx=8)

        rec_names = recommended_models(self.hw)
        rec_size = sum(MODEL_SPECS[n]["size_mb"] for n in rec_names) / 1024
        all_size = sum(v["size_mb"] for v in MODEL_SPECS.values()) / 1024
        ttk.Label(
            bulk,
            text=f"Empfohlen: ca. {rec_size:.1f} GB • alle: ca. {all_size:.1f} GB"
        ).pack(side="right")

        ttk.Separator(frm).pack(fill="x", pady=(0, 8))

        canvas = tk.Canvas(frm, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frm, orient="vertical", command=canvas.yview)
        list_frame = ttk.Frame(canvas)

        list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(canvas_window, width=e.width)
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def rebuild():
            if not win.winfo_exists():
                return
            for child in list_frame.winfo_children():
                child.destroy()

            rows_for_update = []
            rec = recommendation_map(self.hw)

            for name, spec in MODEL_SPECS.items():
                row = ttk.Frame(list_frame)
                row.pack(fill="x", pady=5)

                target = MODEL_DIR / spec["file"]
                size_text = (
                    f"{spec['size_mb']/1024:.1f} GB"
                    if spec["size_mb"] >= 1024
                    else f"{spec['size_mb']} MB"
                )

                ttk.Label(row, text=name, width=24).pack(side="left")
                ttk.Label(row, text=size_text, width=10).pack(side="left")
                ttk.Label(row, text=spec.get("kind", ""), width=12).pack(side="left")

                recommendation = rec.get(name, "")
                ttk.Label(row, text=recommendation, width=18).pack(side="left")

                if target.exists():
                    size_mb = target.stat().st_size / 1024 / 1024
                    status = ttk.Label(
                        row,
                        text=f"✓ installiert ({size_mb:.0f} MB)",
                        width=28
                    )
                    status.pack(side="left")

                    ttk.Button(
                        row,
                        text="Deinstallieren",
                        command=lambda n=name, s=spec: self.uninstall_model_live(
                            n, s, None, rebuild
                        )
                    ).pack(side="right", padx=(6, 0))

                    ttk.Button(
                        row,
                        text="Aktualisieren",
                        command=lambda n=name, s=spec: self.update_model_live(
                            n, s, None, rebuild
                        )
                    ).pack(side="right", padx=(6, 0))

                    check_btn = ttk.Button(row, text="Update prüfen")
                    check_btn.config(
                        command=lambda n=name, s=spec, st=status, b=check_btn:
                            self.check_model_update(n, s, st, b)
                    )
                    check_btn.pack(side="right")
                    rows_for_update.append((name, spec, status, check_btn))
                else:
                    ttk.Label(row, text="nicht installiert", width=28).pack(side="left")
                    ttk.Button(
                        row,
                        text="Herunterladen",
                        command=lambda n=name, s=spec: self.download_model_live(
                            n, s, rebuild
                        )
                    ).pack(side="right")

            ttk.Separator(list_frame).pack(fill="x", pady=12)

            def check_all():
                for n, s, st, b in rows_for_update:
                    self.check_model_update(n, s, st, b)

            if rows_for_update:
                ttk.Button(
                    list_frame,
                    text="Alle installierten Modelle auf Updates prüfen",
                    command=check_all
                ).pack(anchor="e")

        rebuild()

    def install_model_group(self, names, group_title, rebuild):
        missing = [n for n in names if not (MODEL_DIR / MODEL_SPECS[n]["file"]).exists()]
        if not missing:
            messagebox.showinfo(APP_NAME, f"{group_title}: Alle zugehörigen Modelle sind bereits installiert.")
            return

        total_mb = sum(MODEL_SPECS[n]["size_mb"] for n in missing)
        free_bytes = shutil.disk_usage(MODEL_DIR).free
        free_gb = free_bytes / (1024**3)
        total_gb = total_mb / 1024

        details = "\n".join(
            f"• {n} ({MODEL_SPECS[n]['size_mb']/1024:.1f} GB)"
            if MODEL_SPECS[n]["size_mb"] >= 1024
            else f"• {n} ({MODEL_SPECS[n]['size_mb']} MB)"
            for n in missing
        )

        warning = (
            f"{group_title} installieren?\n\n"
            f"Es werden {len(missing)} Modell(e) heruntergeladen.\n"
            f"Geschätzter zusätzlicher Speicherbedarf: ca. {total_gb:.1f} GB\n"
            f"Freier Speicher auf dem Ziellaufwerk: ca. {free_gb:.1f} GB\n\n"
            f"{details}\n\n"
            "Der Download kann je nach Internetverbindung längere Zeit dauern."
        )

        if free_gb < total_gb + 1:
            warning += "\n\n⚠ Der freie Speicher könnte dafür nicht ausreichen."

        if not messagebox.askokcancel(APP_NAME, warning):
            return

        dlg = DownloadDialog(self, group_title)

        def worker():
            installed = 0
            try:
                for index, name in enumerate(missing, start=1):
                    spec = MODEL_SPECS[name]
                    target = MODEL_DIR / spec["file"]
                    tmp = target.with_suffix(target.suffix + ".part")

                    self.after(
                        0, dlg.update_progress,
                        f"{name} ({index}/{len(missing)}) wird geladen…",
                        0,
                        ""
                    )

                    remote = self.remote_model_info(spec["url"]) if hasattr(self, "remote_model_info") else {}
                    self.download_url(
                        spec["url"],
                        tmp,
                        dlg,
                        f"{name} ({index}/{len(missing)}) wird geladen…"
                    )

                    if not tmp.exists() or tmp.stat().st_size < 1024 * 1024:
                        raise RuntimeError(f"{name}: heruntergeladene Datei ist unvollständig.")

                    tmp.replace(target)
                    installed += 1

                    meta = model_meta_load()
                    meta[name] = {
                        "etag": remote.get("etag"),
                        "last_modified": remote.get("last_modified"),
                        "size": target.stat().st_size,
                        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    model_meta_save(meta)

                    self.after(0, self.refresh_models)
                    self.after(0, rebuild)

                self.after(0, dlg.destroy)
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        APP_NAME,
                        f"{group_title}: {installed} Modell(e) wurden installiert."
                    )
                )
            except Exception as e:
                err = str(e)
                self.after(0, dlg.destroy)
                self.after(
                    0,
                    lambda err=err, installed=installed: messagebox.showerror(
                        APP_NAME,
                        f"Stapelinstallation abgebrochen.\n\n"
                        f"Erfolgreich installiert: {installed}\n"
                        f"Fehler: {err}\n\n"
                        "Bereits vollständig installierte Modelle bleiben erhalten."
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

    def download_model_live(self, name, spec, rebuild):
        dlg = DownloadDialog(self, f"Modell: {name}")
        target = MODEL_DIR / spec["file"]
        tmp = target.with_suffix(target.suffix + ".part")

        def worker():
            try:
                remote = self.remote_model_info(spec["url"]) if hasattr(self, "remote_model_info") else {}
                self.download_url(spec["url"], tmp, dlg, f"{name} wird heruntergeladen…")

                if not tmp.exists() or tmp.stat().st_size < 1024 * 1024:
                    raise RuntimeError("Die heruntergeladene Modelldatei ist unvollständig.")

                tmp.replace(target)

                meta = model_meta_load()
                meta[name] = {
                    "etag": remote.get("etag"),
                    "last_modified": remote.get("last_modified"),
                    "size": target.stat().st_size,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                model_meta_save(meta)

                self.after(0, dlg.destroy)
                self.after(0, self.refresh_models)
                self.after(0, rebuild)
            except Exception as e:
                err = str(e)
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
                self.after(0, dlg.destroy)
                self.after(0, lambda err=err: messagebox.showerror(
                    APP_NAME, f"Modelldownload fehlgeschlagen:\n{err}"
                ))

        threading.Thread(target=worker, daemon=True).start()

    def uninstall_model_live(self, name, spec, status_label, rebuild):
        target = MODEL_DIR / spec["file"]
        if not target.exists():
            rebuild()
            return

        if not messagebox.askyesno(
            APP_NAME,
            f"{name} wirklich deinstallieren?\n\nDatei:\n{target}"
        ):
            return

        try:
            target.unlink()
            meta = model_meta_load()
            meta.pop(name, None)
            model_meta_save(meta)
            self.refresh_models()
            rebuild()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Deinstallation fehlgeschlagen:\n{e}")

    def update_model_live(self, name, spec, status_label, rebuild):
        target = MODEL_DIR / spec["file"]
        dlg = DownloadDialog(self, f"Modell aktualisieren: {name}")
        tmp = target.with_suffix(target.suffix + ".update")

        def worker():
            try:
                remote = self.remote_model_info(spec["url"]) if hasattr(self, "remote_model_info") else {}
                self.download_url(spec["url"], tmp, dlg, f"{name} wird aktualisiert…")

                if not tmp.exists() or tmp.stat().st_size < 1024 * 1024:
                    raise RuntimeError("Die heruntergeladene Modelldatei ist unvollständig.")

                tmp.replace(target)

                meta = model_meta_load()
                meta[name] = {
                    "etag": remote.get("etag"),
                    "last_modified": remote.get("last_modified"),
                    "size": target.stat().st_size,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                model_meta_save(meta)

                self.after(0, dlg.destroy)
                self.after(0, self.refresh_models)
                self.after(0, rebuild)
            except Exception as e:
                err = str(e)
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
                self.after(0, dlg.destroy)
                self.after(0, lambda err=err: messagebox.showerror(
                    APP_NAME, f"Modell-Update fehlgeschlagen:\n{err}"
                ))

        threading.Thread(target=worker, daemon=True).start()

    def download_model(self, name, spec, parent=None):
        dlg = DownloadDialog(self, f"Modell: {name}")
        target = MODEL_DIR / spec["file"]
        tmp = target.with_suffix(target.suffix + ".part")
        def worker():
            try:
                remote = self.remote_model_info(spec["url"])
                self.download_url(spec["url"], tmp, dlg, f"{name} wird heruntergeladen…")

                if not tmp.exists() or tmp.stat().st_size < 1024 * 1024:
                    raise RuntimeError("Die heruntergeladene Modelldatei ist unvollständig.")

                tmp.replace(target)

                meta = model_meta_load()
                meta[name] = {
                    "etag": remote.get("etag"),
                    "last_modified": remote.get("last_modified"),
                    "size": target.stat().st_size,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                model_meta_save(meta)

                self.after(0, dlg.destroy)
                self.after(0, self.refresh_models)
                if parent:
                    self.after(0, parent.destroy)
                self.after(0, lambda: messagebox.showinfo(APP_NAME, f"{name} wurde installiert."))
            except Exception as e:
                err = str(e)
                try:
                    if tmp.exists():
                        tmp.unlink()
                except Exception:
                    pass
                self.after(0, dlg.destroy)
                self.after(0, lambda err=err: messagebox.showerror(
                    APP_NAME,
                    f"Modelldownload fehlgeschlagen:\n{err}"
                ))
        threading.Thread(target=worker, daemon=True).start()

    def refresh_models(self):
        vals = []
        for name, spec in MODEL_SPECS.items():
            vals.append(name if (MODEL_DIR/spec["file"]).exists() else f"{name} (fehlt)")
        self.model_combo["values"] = vals

        base = self.model_var.get().replace(" (fehlt)", "")
        if base not in MODEL_SPECS:
            base = primary_recommended_model(self.hw)

        matched = False
        for v in vals:
            if v.replace(" (fehlt)", "") == base:
                self.model_var.set(v)
                matched = True
                break

        if not matched and vals:
            self.model_var.set(vals[0])

        self.update_model_hint()

    def on_model_selected(self, event=None):
        self.update_model_hint()
        selected = self.model_var.get().replace(" (fehlt)", "")
        if selected in MODEL_SPECS:
            self.cfg["model"] = selected
            cfg_save(self.cfg)

    def select_recommended_model(self):
        recommended = primary_recommended_model(self.hw)
        for value in self.model_combo["values"]:
            if value.replace(" (fehlt)", "") == recommended:
                self.model_var.set(value)
                break
        else:
            self.model_var.set(recommended)

        self.cfg["model"] = recommended
        cfg_save(self.cfg)
        self.update_model_hint()

    def update_model_hint(self):
        name = self.model_var.get().replace(" (fehlt)", "")
        hint = recommendation_map(self.hw).get(name, "")
        self.model_hint.config(text=hint)

        if hasattr(self, "footer_model"):
            recommended = primary_recommended_model(self.hw)
            if name == recommended:
                self.footer_model.config(text=f"★ Empfohlenes Modell: {recommended}")
            else:
                self.footer_model.config(text=f"Empfohlen für diese Hardware: {recommended}")

    def update_audio_mode_info(self):
        mode = self.audio_mode_var.get()
        mapping = {
            "Automatisch (FLAC)": "Auto: problematische Formate → FLAC (16 kHz, Mono, verlustfrei komprimiert)",
            "WAV verlustfrei": "Alle Dateien → WAV 16 kHz Mono PCM",
            "MP3 kompatibel": "Alle Dateien → MP3 64 kbit/s Mono",
            "Original verwenden": "Keine Vorab-Konvertierung"
        }
        self.audio_info_label.config(text=mapping.get(mode, ""))

    def profile_changed(self):
        p = RESOURCE_PROFILES[self.profile_var.get()]
        backend = whisper_build_backend(getattr(self, "whisper", None))
        if backend == "CUDA":
            self.profile_info.config(text=f"CUDA + {p['threads']} CPU-Threads")
        else:
            self.profile_info.config(text=f"CPU: {p['threads']} Threads")

    def choose_output(self):
        p = filedialog.askdirectory(title="Zielordner auswählen")
        if p:
            self.custom_output = Path(p)
            self.out_label.config(text=p)
            self.dest_var.set("custom")

    def add_files_dialog(self):
        files = filedialog.askopenfilenames(
            title="Audio-/Videodateien auswählen",
            filetypes=[
                ("Audio/Video", "*.mp3 *.wav *.m4a *.flac *.ogg *.opus *.aac *.wma *.mp4 *.mkv *.mov *.webm *.3gp *.amr"),
                ("Alle Dateien", "*.*")
            ]
        )
        self.add_files(files)

    def on_drop(self, event):
        try:
            self.add_files(self.tk.splitlist(event.data))
        except Exception:
            pass

    def duration(self, p):
        if not self.ffprobe:
            return None
        try:
            r = run_hidden(
                [str(self.ffprobe), "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                capture_output=True, text=True, timeout=20
            )
            return float(r.stdout.strip())
        except Exception:
            return None

    def output_dir(self, p):
        m = self.dest_var.get()
        if m == "same":
            return p.parent
        if m == "custom" and self.custom_output:
            return self.custom_output
        return p.parent / "transkripte"

    def add_files(self, files):
        have = {str(i["path"]).lower() for i in self.items}
        for raw in files:
            p = Path(raw)
            if not p.exists() or p.suffix.lower() not in AUDIO_EXTS or str(p).lower() in have:
                continue
            d = self.duration(p)
            self.items.append({"path": p, "duration": d})
            self.tree.insert("", "end", values=(p.name, fmt_time(d), "Wartend", str(self.output_dir(p))))
            have.add(str(p).lower())

    def remove_selected(self):
        rows = list(self.tree.selection())
        inds = sorted([self.tree.index(r) for r in rows], reverse=True)
        for i in inds:
            del self.items[i]
        for r in rows:
            self.tree.delete(r)

    def clear_list(self):
        if self.worker and self.worker.is_alive():
            return
        self.items.clear()
        for r in self.tree.get_children():
            self.tree.delete(r)

    def selected_model(self):
        name = self.model_var.get().replace(" (fehlt)", "")
        spec = MODEL_SPECS.get(name, MODEL_SPECS["Medium"])
        return name, MODEL_DIR / spec["file"]

    def preprocess(self, p):
        mode = self.audio_mode_var.get()

        if mode == "Original verwenden":
            return p, None

        if not self.ffmpeg:
            raise RuntimeError("FFmpeg fehlt.")

        # Auto mode converts only formats that are known to be less reliable.
        if mode == "Automatisch (FLAC)" and p.suffix.lower() not in PRECONVERT_EXTS:
            return p, None

        safe_stem = re.sub(r'[^A-Za-z0-9._-]+', '_', p.stem)

        if mode == "WAV verlustfrei":
            out = TEMP_DIR / f"{safe_stem}_whisper.wav"
            cmd = [
                str(self.ffmpeg), "-y", "-i", str(p),
                "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(out)
            ]
        elif mode == "MP3 kompatibel":
            out = TEMP_DIR / f"{safe_stem}_whisper.mp3"
            cmd = [
                str(self.ffmpeg), "-y", "-i", str(p),
                "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "libmp3lame", "-b:a", "64k", str(out)
            ]
        else:
            # Default / automatic: FLAC is lossless, compressed and reliably
            # supported by whisper.cpp/miniaudio on Windows.
            out = TEMP_DIR / f"{safe_stem}_whisper.flac"
            cmd = [
                str(self.ffmpeg), "-y", "-i", str(p),
                "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "flac", "-compression_level", "5", str(out)
            ]

        r = run_hidden(
            cmd,
            capture_output=True,
            text=True
        )
        if r.returncode != 0 or not out.exists():
            details = (r.stdout or "")[-2500:] + "\n" + (r.stderr or "")[-2500:]
            raise RuntimeError("Audio-Konvertierung fehlgeschlagen.\n" + details)

        return out, out

    def start(self):
        self.refresh_component_status()
        if not self.whisper or not self.ffmpeg:
            messagebox.showwarning(APP_NAME, "Bitte zuerst „Alles automatisch einrichten“ ausführen.")
            return
        if not self.items:
            messagebox.showwarning(APP_NAME, "Bitte zuerst Dateien hinzufügen.")
            return
        if self.dest_var.get() == "custom" and not self.custom_output:
            messagebox.showwarning(APP_NAME, "Bitte einen benutzerdefinierten Zielordner wählen.")
            return

        if self.hw.get("nvidia") and whisper_build_backend(self.whisper) != "CUDA":
            if messagebox.askyesno(
                APP_NAME,
                "Eine NVIDIA-GPU wurde erkannt, aber aktuell ist der CPU-Build aktiv.\n\n"
                "Soll die automatische Einrichtung jetzt versuchen, den CUDA-Build zu installieren?"
            ):
                self.auto_setup()
                return

        model_name, model_path = self.selected_model()
        if not model_path.exists():
            if messagebox.askyesno(APP_NAME, f"{model_name} ist noch nicht installiert.\nJetzt herunterladen?"):
                self.download_model(model_name, MODEL_SPECS[model_name])
            return

        p = RESOURCE_PROFILES[self.profile_var.get()]
        selected_backend = whisper_build_backend(self.whisper)
        if not messagebox.askokcancel(
            APP_NAME,
            f"Transkription starten?\n\n"
            f"Backend: {selected_backend}\n"
            f"Hardware: {self.hw.get('gpu', 'Unbekannt')}\n"
            f"Modell: {model_name}\n"
            f"Leistungsmodus: {self.profile_var.get()} ({p['threads']} Threads)\n\n"
            "Während der Verarbeitung kann das System träger reagieren."
        ):
            return

        self.cfg.update({
            "model": model_name,
            "language": self.lang_var.get(),
            "profile": self.profile_var.get(),
            "dest_mode": self.dest_var.get(),
            "custom_output": str(self.custom_output) if self.custom_output else "",
            "audio_mode": self.audio_mode_var.get(),
            "keep_converted": self.keep_converted_var.get(),
        })
        cfg_save(self.cfg)

        self.cancel = False
        self.paused = False
        self.pause_btn.config(text="⏸ Pause", state="normal")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.worker = threading.Thread(target=self.run_queue, daemon=True)
        self.worker.start()

    def run_queue(self):
        model_name, model_path = self.selected_model()
        profile = RESOURCE_PROFILES[self.profile_var.get()]
        lang = {"Deutsch":"de", "Englisch":"en", "Auto":None}[self.lang_var.get()]
        rows = list(self.tree.get_children())
        total = len(self.items)

        for idx, item in enumerate(self.items):
            if self.cancel:
                break
            src = item["path"]
            dur = item["duration"]
            row = rows[idx]

            self.ui_status(f"Datei {idx+1}/{total}: {src.name}")
            self.ui_row(row, "Vorbereitung")
            converted = None
            try:
                inp, converted = self.preprocess(src)
            except Exception as e:
                self.ui_row(row, "Konvertierungsfehler")
                self.log_line(f"{src.name}: {e}\n")
                continue

            outdir = self.output_dir(src)
            outdir.mkdir(parents=True, exist_ok=True)
            outbase = outdir / src.stem

            cmd = [
                str(self.whisper),
                "-t", str(profile["threads"]),
                "-m", str(model_path),
                "-f", str(inp),
            ]
            if lang:
                cmd += ["-l", lang]
            if self.txt.get():
                cmd.append("--output-txt")
            if self.srt.get():
                cmd.append("--output-srt")
            if self.vtt.get():
                cmd.append("--output-vtt")
            cmd += ["-of", str(outbase)]

            self.ui_row(row, "Transkribiert")
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.whisper.parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=CREATE_NO_WINDOW | profile["priority"]
                )
                self.after(0, lambda: self.runtime_status.config(text="Laufzeit: wird erkannt …"))

                for line in self.proc.stdout:
                    if self.cancel:
                        break

                    self.log_line(line)
                    lower_line = line.lower()

                    if "no gpu found" in lower_line:
                        self.after(
                            0,
                            lambda: self.runtime_status.config(text="Laufzeit: CPU ⚠ keine GPU aktiv")
                        )
                    elif (
                        ("cuda" in lower_line and "backend" in lower_line)
                        or "ggml_cuda" in lower_line
                        or "cuda0" in lower_line
                    ):
                        self.after(
                            0,
                            lambda: self.runtime_status.config(text="Laufzeit: CUDA ✓ GPU aktiv")
                        )

                    m = TS_RE.search(line)
                    if m and dur:
                        cur = ts_seconds(m.groups()[4:8])
                        frac = max(0, min(1, cur/dur))
                        self.ui_progress(
                            frac*100,
                            f"{int(frac*100)} % • {fmt_time(cur)} / {fmt_time(dur)} • Datei {idx+1}/{total}"
                        )
                rc = self.proc.wait()
                self.proc = None
                self.paused = False
                self.after(0, lambda: self.pause_btn.config(text="⏸ Pause"))
                self.ui_row(row, "Fertig" if rc == 0 else f"Fehler ({rc})")
            except Exception as e:
                self.ui_row(row, "Fehler")
                self.log_line(f"\nFEHLER: {e}\n")

            if converted and converted.exists() and not self.keep_converted_var.get():
                try:
                    converted.unlink()
                except Exception:
                    pass

            time.sleep(1)

        self.after(0, self.finish)

    def stop(self):
        self.cancel = True
        self.ui_status("Abbruch wird ausgeführt…")
        if self.proc and self.proc.poll() is None:
            if self.paused:
                self._resume_process()
                self.paused = False
            try:
                self.proc.terminate()
            except Exception:
                pass

    def finish(self):
        self.paused = False
        self.start_btn.config(state="normal")
        self.pause_btn.config(text="⏸ Pause", state="disabled")
        self.stop_btn.config(state="disabled")
        self.status.config(text="Abgebrochen." if self.cancel else "Stapelverarbeitung abgeschlossen.")

    def ui_row(self, row, text):
        self.after(0, lambda: self.tree.set(row, "status", text))

    def ui_status(self, text):
        self.after(0, lambda: self.status.config(text=text))

    def ui_progress(self, value, text):
        def f():
            self.progress["value"] = value
            self.status.config(text=text)
        self.after(0, f)

    def log_line(self, text):
        def f():
            self.log.config(state="normal")
            self.log.insert("end", text)
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, f)


if __name__ == "__main__":
    App().mainloop()
