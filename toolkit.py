import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk
import numpy as np
import os
import subprocess
import threading
import re
import sys

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ============================================================
#                    DARK THEME COLORS
# ============================================================
COLORS = {
    "bg_dark":           "#0d1117",
    "bg_card":           "#161b22",
    "bg_input":          "#0d1117",
    "border":            "#30363d",
    "text":              "#c9d1d9",
    "text_dim":          "#8b949e",
    "accent_blue":       "#58a6ff",
    "accent_green":      "#238636",
    "accent_green_light":"#2ea043",
    "accent_red":        "#da3633",
    "accent_orange":     "#f0883e",
    "accent_yellow":     "#ffcc44",
    "accent_purple":     "#8957e5",
    "success":           "#7ee787",
    "command_bg":        "#010409",
    "selected_bg":       "#1f3a5f",
    "hover_bg":          "#1c2128",
    "folder_color":      "#f0883e",
    "file_color":        "#58a6ff",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

APP_NAME    = "2D Asset Toolkit"
APP_VERSION = "v1.0.0"
APP_STUDIO  = "LilyxGames"

# Ordered model list used by both Install tab and BG Remover tab
REMBG_MODELS = [
    ("🚀 isnet-general-use — High Precision",   "isnet-general-use"),
    ("⚡ u2net — Standard All-Rounder",          "u2net"),
    ("💨 u2netp — Lite / Fast",                  "u2netp"),
    ("🎯 u2net_human_seg — Best for Characters", "u2net_human_seg"),
    ("🎌 isnet-anime — Anime / Cartoon",         "isnet-anime"),
    ("🖤 silueta — Silhouette Focused",          "silueta"),
    ("👕 u2net_cloth_seg — Clothing Only",        "u2net_cloth_seg"),
]

# rembg stores model weights here
REMBG_MODEL_DIR = Path.home() / ".u2net"

REMBG_MODEL_FILES = {
    "u2net_human_seg":   "u2net_human_seg.onnx",
    "isnet-general-use": "isnet-general-use.onnx",
    "isnet-anime":       "isnet-anime.onnx",
    "u2net":             "u2net.onnx",
    "silueta":           "silueta.onnx",
    "u2net_cloth_seg":   "u2net_cloth_seg.onnx",
    "u2netp":            "u2netp.onnx",
}


# ============================================================
#                    UTILITY FUNCTIONS
# ============================================================
def lighten_color(hex_color, factor=0.2):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def center_window(root, width, height):
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x  = (sw - width)  // 2
    y  = (sh - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_image_resolution(path):
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def make_hover_button(parent, text, color, command,
                      width=14, height=2, font_size=11):
    btn = tk.Button(
        parent, text=text,
        font=("Segoe UI", font_size, "bold"),
        bg=color, fg="white",
        activebackground=lighten_color(color),
        activeforeground="white",
        width=width, height=height,
        cursor="hand2", relief="flat", bd=0,
        command=command,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=lighten_color(color)))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn


def collect_images(root_path: Path, recursive: bool = True):
    if recursive:
        files = []
        for ext in IMAGE_EXTENSIONS:
            files += list(root_path.rglob(f"*{ext}"))
            files += list(root_path.rglob(f"*{ext.upper()}"))
    else:
        files = []
        for ext in IMAGE_EXTENSIONS:
            files += list(root_path.glob(f"*{ext}"))
            files += list(root_path.glob(f"*{ext.upper()}"))
    seen, unique = set(), []
    for f in files:
        key = str(f).lower()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return sorted(unique)


def make_drop_zone(parent, text,
                   on_drop_callback=None,
                   on_click_callback=None,
                   height=130):
    frame = tk.Frame(
        parent, bg=COLORS["bg_card"],
        highlightbackground=COLORS["border"],
        highlightthickness=2, height=height,
    )
    frame.pack(fill="x", padx=20, pady=(12, 8))
    frame.pack_propagate(False)

    label = tk.Label(
        frame, text=text,
        font=("Segoe UI", 12),
        bg=COLORS["bg_card"], fg=COLORS["text_dim"],
        justify="center",
    )
    label.pack(expand=True)

    if HAS_DND and on_drop_callback:
        frame.drop_target_register(DND_FILES)
        frame.dnd_bind("<<Drop>>", on_drop_callback)
        label.drop_target_register(DND_FILES)
        label.dnd_bind("<<Drop>>", on_drop_callback)

    if on_click_callback:
        frame.bind("<Button-1>", on_click_callback)
        label.bind("<Button-1>", on_click_callback)

    return frame, label


def parse_drop_data(raw: str):
    tokens = re.findall(r'\{([^}]+)\}|(\S+)', raw)
    paths  = [a or b for a, b in tokens]
    return paths


def set_children_state(widget, state):
    for w in widget.winfo_children():
        try:
            w.config(state=state)
        except Exception:
            pass
        set_children_state(w, state)


def is_model_installed(model_id: str) -> bool:
    fname = REMBG_MODEL_FILES.get(model_id)
    if fname and (REMBG_MODEL_DIR / fname).exists():
        return True
    return False


def is_rembg_installed() -> bool:
    try:
        import importlib
        importlib.import_module("rembg")
        return True
    except ImportError:
        return False


# ============================================================
#              SMART TRIM ALGORITHM
# ============================================================
def smart_trim(img: Image.Image,
               alpha_threshold: int = 10,
               color_trim: bool = False,
               color_target: tuple = (255, 255, 255),
               color_fuzz: int = 30,
               padding: int = 0) -> Image.Image:
    img = img.convert("RGBA")
    r_ch, g_ch, b_ch, a_ch = img.split()

    alpha_arr = np.array(a_ch)
    r_arr     = np.array(r_ch)
    g_arr     = np.array(g_ch)
    b_arr     = np.array(b_ch)

    mask = alpha_arr >= alpha_threshold

    if color_trim:
        cr, cg, cb = color_target
        color_match = (
            (np.abs(r_arr.astype(int) - cr) <= color_fuzz) &
            (np.abs(g_arr.astype(int) - cg) <= color_fuzz) &
            (np.abs(b_arr.astype(int) - cb) <= color_fuzz)
        )
        mask = mask & ~color_match

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any() or not cols.any():
        return img

    h, w   = alpha_arr.shape
    top    = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left   = int(np.argmax(cols))
    right  = int(len(cols) - np.argmax(cols[::-1]))

    top    = max(0, top    - padding)
    left   = max(0, left   - padding)
    bottom = min(h, bottom + padding)
    right  = min(w, right  + padding)

    return img.crop((left, top, right, bottom))


# ============================================================
#               TAB 0: FILE EXPLORER
# ============================================================
class FileExplorerTab:
    VIEW_MODES = ["details", "medium", "large"]
    SORT_MODES = [
        ("Name",          "name"),
        ("Size ↓",        "size_desc"),
        ("Size ↑",        "size_asc"),
        ("Resolution ↓",  "res_desc"),
        ("Resolution ↑",  "res_asc"),
    ]

    def __init__(self, parent, app_ref):
        self.frame         = tk.Frame(parent, bg=COLORS["bg_dark"])
        self.app           = app_ref
        self.root_path     = None
        self.current_path  = None
        self.selected_path = None
        self._history      = []
        self._entries      = []
        self._entry_cache  = {}
        self._thumb_refs   = []
        self._preview_ref  = None
        self._current_view = "details"
        self._current_sort = "name"

        self._build_ui()

    def _build_ui(self):
        f = self.frame

        tk.Label(f, text="📂  File Explorer",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["accent_blue"]
                 ).pack(pady=(14, 2))

        tk.Label(f,
                 text="Browse folders and select files  •  "
                      "Drag & drop a folder to open it",
                 font=("Segoe UI", 10),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(pady=(0, 8))

        self.drop_frame, self.drop_label = make_drop_zone(
            f,
            "📁  Drag & Drop a FOLDER here to open it\nor click to browse",
            on_drop_callback=self._on_drop_folder,
            on_click_callback=lambda e: self.open_root_folder(),
            height=70,
        )

        toolbar = tk.Frame(f, bg=COLORS["bg_dark"])
        toolbar.pack(fill="x", padx=20, pady=(4, 4))

        self.back_btn = make_hover_button(
            toolbar, "⬅ Back", "#30363d",
            self.go_back, width=7, height=1, font_size=9)
        self.back_btn.pack(side="left", padx=(0, 4))

        self.up_btn = make_hover_button(
            toolbar, "⬆ Up", "#30363d",
            self.go_up, width=5, height=1, font_size=9)
        self.up_btn.pack(side="left", padx=(0, 16))

        tk.Label(toolbar, text="Sort:", font=("Segoe UI", 9, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(side="left", padx=(0, 4))

        self.sort_var = tk.StringVar(value="Name")
        sort_menu = ttk.Combobox(
            toolbar, textvariable=self.sort_var,
            values=[s[0] for s in self.SORT_MODES],
            state="readonly", width=14, font=("Segoe UI", 9))
        sort_menu.pack(side="left", padx=(0, 16))
        sort_menu.bind("<<ComboboxSelected>>", self._on_sort_changed)

        tk.Label(toolbar, text="View:", font=("Segoe UI", 9, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(side="left", padx=(0, 4))

        self.view_var = tk.StringVar(value="Details")
        view_menu = ttk.Combobox(
            toolbar, textvariable=self.view_var,
            values=["Details", "Medium", "Large"],
            state="readonly", width=10, font=("Segoe UI", 9))
        view_menu.pack(side="left")
        view_menu.bind("<<ComboboxSelected>>", self._on_view_changed)

        self.breadcrumb_var = tk.StringVar(value="No folder opened")
        tk.Label(f, textvariable=self.breadcrumb_var,
                 font=("Segoe UI", 9), bg=COLORS["bg_dark"],
                 fg=COLORS["text_dim"], anchor="w"
                 ).pack(fill="x", padx=22, pady=(0, 4))

        pane = tk.PanedWindow(f, bg=COLORS["bg_dark"],
                              sashwidth=6, sashrelief="flat",
                              orient="horizontal")
        pane.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        left_frame = tk.Frame(pane, bg=COLORS["bg_card"],
                              highlightbackground=COLORS["border"],
                              highlightthickness=1)
        pane.add(left_frame, width=540, minsize=320)

        self.list_canvas = tk.Canvas(
            left_frame, bg=COLORS["bg_card"],
            highlightthickness=0, borderwidth=0)
        self.list_scrollbar = tk.Scrollbar(
            left_frame, orient="vertical",
            command=self.list_canvas.yview,
            bg=COLORS["bg_dark"], troughcolor=COLORS["bg_card"])
        self.list_canvas.configure(
            yscrollcommand=self.list_scrollbar.set)
        self.list_scrollbar.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)

        self.list_inner = tk.Frame(
            self.list_canvas, bg=COLORS["bg_card"])
        self._list_window = self.list_canvas.create_window(
            (0, 0), window=self.list_inner, anchor="nw")

        self.list_inner.bind("<Configure>", self._on_list_configure)
        self.list_canvas.bind("<Configure>", self._on_canvas_resize)
        self.list_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        if HAS_DND:
            self.list_canvas.drop_target_register(DND_FILES)
            self.list_canvas.dnd_bind("<<Drop>>", self._on_drop_folder)

        right_frame = tk.Frame(pane, bg=COLORS["bg_dark"])
        pane.add(right_frame, width=300, minsize=250)

        self._build_right_panel(right_frame)

    def _build_right_panel(self, parent):
        preview_pane = tk.PanedWindow(
            parent, orient="vertical",
            bg=COLORS["bg_dark"], sashwidth=5, sashrelief="flat")
        preview_pane.pack(fill="both", expand=True)

        preview_card = tk.Frame(
            preview_pane, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        preview_pane.add(preview_card, minsize=120)

        self.preview_canvas = tk.Canvas(
            preview_card, bg="#1a1a2e",
            highlightthickness=0, borderwidth=0)
        self.preview_canvas.pack(fill="both", expand=True,
                                 padx=4, pady=4)
        self.preview_canvas.bind(
            "<Configure>", self._on_preview_resize)

        bottom_frame = tk.Frame(
            preview_pane, bg=COLORS["bg_dark"])
        preview_pane.add(bottom_frame, minsize=160)

        parent.after(
            100,
            lambda: preview_pane.sash_place(0, 0, 300))

        info_card = tk.Frame(
            bottom_frame, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        info_card.pack(fill="x", pady=(0, 6))

        info_inner = tk.Frame(info_card, bg=COLORS["bg_card"])
        info_inner.pack(fill="x", padx=12, pady=8)

        tk.Label(info_inner, text="Selected:",
                 font=("Segoe UI", 9, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")

        self.sel_name_lbl = tk.Label(
            info_inner, text="—",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["accent_blue"],
            wraplength=240, justify="left")
        self.sel_name_lbl.pack(anchor="w")

        self.sel_type_lbl = tk.Label(
            info_inner, text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg_card"], fg=COLORS["text_dim"])
        self.sel_type_lbl.pack(anchor="w", pady=(2, 0))

        self.sel_size_lbl = tk.Label(
            info_inner, text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg_card"], fg=COLORS["text_dim"])
        self.sel_size_lbl.pack(anchor="w")

        self.sel_res_lbl = tk.Label(
            info_inner, text="",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["accent_yellow"])
        self.sel_res_lbl.pack(anchor="w", pady=(2, 0))

    def _on_list_configure(self, e=None):
        self.list_canvas.configure(
            scrollregion=self.list_canvas.bbox("all"))

    def _on_canvas_resize(self, e):
        self.list_canvas.itemconfig(
            self._list_window, width=e.width)

    def _on_mousewheel(self, e):
        try:
            self.list_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass

    def _on_preview_resize(self, e=None):
        if self.selected_path and self.selected_path.is_file():
            self._show_preview(self.selected_path)

    def _on_drop_folder(self, event):
        paths = parse_drop_data(event.data.strip())
        if not paths:
            return
        p = Path(paths[0])
        if p.is_dir():
            self._load_folder(p, clear_history=True)
            self.drop_label.config(
                text=f"✅  Opened: {p.name}",
                fg=COLORS["success"])
        elif p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            self._load_folder(p.parent, clear_history=True)
            self.drop_label.config(
                text=f"✅  Opened: {p.parent.name}",
                fg=COLORS["success"])
            self.frame.after(120, lambda: self._auto_select(p))
        else:
            messagebox.showwarning(
                "Unsupported", "Drop a folder or an image file.")

    def _auto_select(self, target: Path):
        for i, entry in enumerate(self._entries):
            if entry == target:
                self.selected_path = entry
                self._update_info(entry)
                self._show_preview(entry)
                break

    def open_root_folder(self):
        folder = filedialog.askdirectory(title="Open a folder")
        if folder:
            p = Path(folder)
            self._load_folder(p, clear_history=True)
            self.drop_label.config(
                text=f"✅  Opened: {p.name}",
                fg=COLORS["success"])

    def _load_folder(self, path: Path, clear_history=False):
        if not path.is_dir():
            return
        if clear_history:
            self._history.clear()
            self.root_path = path
        self.current_path  = path
        self.selected_path = None
        self._entry_cache.clear()
        self._clear_preview()
        self.breadcrumb_var.set(str(path))
        self._refresh_list()

    def go_back(self):
        if self._history:
            prev = self._history.pop()
            self.current_path  = prev
            self.selected_path = None
            self._entry_cache.clear()
            self._clear_preview()
            self.breadcrumb_var.set(str(prev))
            self._refresh_list()

    def go_up(self):
        if (self.current_path and
                self.current_path.parent != self.current_path):
            self._history.append(self.current_path)
            self._load_folder(self.current_path.parent)

    def _on_sort_changed(self, e=None):
        label = self.sort_var.get()
        for display, key in self.SORT_MODES:
            if display == label:
                self._current_sort = key
                break
        self._refresh_list()

    def _on_view_changed(self, e=None):
        self._current_view = self.view_var.get().lower()
        self._refresh_list()

    def _get_entry_info(self, path: Path):
        if path in self._entry_cache:
            return self._entry_cache[path]
        info = {"size": 0, "resolution": None}
        try:
            if path.is_file():
                info["size"] = path.stat().st_size
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    info["resolution"] = get_image_resolution(path)
        except Exception:
            pass
        self._entry_cache[path] = info
        return info

    def _sort_entries(self, entries):
        sort  = self._current_sort
        dirs  = [e for e in entries if e.is_dir()]
        files = [e for e in entries if e.is_file()]
        dirs.sort(key=lambda p: p.name.lower())

        if sort == "name":
            files.sort(key=lambda p: p.name.lower())
        elif sort == "size_desc":
            files.sort(
                key=lambda p: self._get_entry_info(p)["size"],
                reverse=True)
        elif sort == "size_asc":
            files.sort(
                key=lambda p: self._get_entry_info(p)["size"])
        elif sort == "res_desc":
            def _rp(p):
                r = self._get_entry_info(p)["resolution"]
                return (r[0] * r[1]) if r else 0
            files.sort(key=_rp, reverse=True)
        elif sort == "res_asc":
            def _rp2(p):
                r = self._get_entry_info(p)["resolution"]
                return (r[0] * r[1]) if r else 0
            files.sort(key=_rp2)

        return dirs + files

    def _refresh_list(self):
        for w in self.list_inner.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        if not self.current_path or not self.current_path.is_dir():
            return

        raw = list(self.current_path.iterdir())
        entries_all = []
        for entry in raw:
            if entry.is_dir():
                entries_all.append(entry)
            elif entry.suffix.lower() in IMAGE_EXTENSIONS:
                entries_all.append(entry)
            elif self._current_view == "details":
                entries_all.append(entry)

        for e in entries_all:
            if e.is_file() and e.suffix.lower() in IMAGE_EXTENSIONS:
                self._get_entry_info(e)

        self._entries = self._sort_entries(entries_all)

        view = self._current_view
        if view == "large":
            self._build_grid_view(thumb_size=288)
        elif view == "medium":
            self._build_grid_view(thumb_size=168)
        else:
            self._build_details_view()

        self._on_list_configure()

    def _build_details_view(self):
        header = tk.Frame(self.list_inner, bg=COLORS["bg_dark"])
        header.pack(fill="x", padx=2, pady=(2, 0))

        tk.Label(header, text="Name",
                 font=("Segoe UI", 8, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
                 anchor="w").pack(side="left", fill="x", expand=True)
        tk.Label(header, text="Resolution",
                 font=("Segoe UI", 8, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
                 width=12, anchor="e").pack(side="right", padx=(6, 0))
        tk.Label(header, text="Size",
                 font=("Segoe UI", 8, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
                 width=10, anchor="e").pack(side="right", padx=(6, 0))

        tk.Frame(self.list_inner, bg=COLORS["border"], height=1
                 ).pack(fill="x", padx=2, pady=2)

        for idx, entry in enumerate(self._entries):
            row = tk.Frame(self.list_inner, bg=COLORS["bg_card"],
                           cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)

            info = self._get_entry_info(entry)

            if entry.is_dir():
                icon       = "📁"
                name_color = COLORS["folder_color"]
            elif entry.suffix.lower() in IMAGE_EXTENSIONS:
                icon       = "🖼️"
                name_color = COLORS["file_color"]
            else:
                icon       = "  "
                name_color = COLORS["text_dim"]

            name_lbl = tk.Label(
                row, text=f" {icon}  {entry.name}",
                font=("Consolas", 10), bg=COLORS["bg_card"],
                fg=name_color, anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True)

            res_text = ""
            if info["resolution"]:
                rw, rh = info["resolution"]
                res_text = f"{rw}×{rh}"
            res_lbl = tk.Label(
                row, text=res_text,
                font=("Consolas", 9), bg=COLORS["bg_card"],
                fg=COLORS["accent_yellow"], width=12, anchor="e")
            res_lbl.pack(side="right", padx=(6, 4))

            size_text = ""
            if entry.is_file():
                size_text = format_size(info["size"])
            size_lbl = tk.Label(
                row, text=size_text,
                font=("Consolas", 9), bg=COLORS["bg_card"],
                fg=COLORS["text_dim"], width=10, anchor="e")
            size_lbl.pack(side="right", padx=(6, 0))

            for w in [row, name_lbl, res_lbl, size_lbl]:
                w.bind("<Button-1>",
                       lambda e, i=idx: self._on_row_click(i))
                w.bind("<Double-Button-1>",
                       lambda e, i=idx: self._on_row_dblclick(i))
                w.bind("<Enter>",
                       lambda e, r=row: self._row_hover(r, True))
                w.bind("<Leave>",
                       lambda e, r=row: self._row_hover(r, False))

    def _build_grid_view(self, thumb_size=168):
        container = self.list_inner
        row_frame = None
        col       = 0
        max_cols  = max(1, 500 // (thumb_size + 28))

        for idx, entry in enumerate(self._entries):
            if col % max_cols == 0:
                row_frame = tk.Frame(container, bg=COLORS["bg_card"])
                row_frame.pack(fill="x", padx=4, pady=3)
                col = 0

            cell_h = thumb_size + 60
            cell = tk.Frame(
                row_frame, bg=COLORS["bg_card"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
                cursor="hand2",
                width=thumb_size + 28,
                height=cell_h)
            cell.pack(side="left", padx=4, pady=4)
            cell.pack_propagate(False)

            if entry.is_dir():
                thumb_lbl = tk.Label(
                    cell, text="📁",
                    font=("Segoe UI", thumb_size // 3),
                    bg=COLORS["bg_card"],
                    fg=COLORS["folder_color"])
                thumb_lbl.pack(expand=True)

            elif entry.suffix.lower() in IMAGE_EXTENSIONS:
                try:
                    img = Image.open(entry)
                    img.thumbnail(
                        (thumb_size, thumb_size),
                        Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    self._thumb_refs.append(tk_img)
                    thumb_lbl = tk.Label(
                        cell, image=tk_img,
                        bg=COLORS["bg_card"])
                    thumb_lbl.pack(pady=(6, 0))
                except Exception:
                    thumb_lbl = tk.Label(
                        cell, text="🖼️",
                        font=("Segoe UI", thumb_size // 4),
                        bg=COLORS["bg_card"],
                        fg=COLORS["file_color"])
                    thumb_lbl.pack(expand=True)
            else:
                thumb_lbl = tk.Label(
                    cell, text="📄",
                    font=("Segoe UI", thumb_size // 4),
                    bg=COLORS["bg_card"],
                    fg=COLORS["text_dim"])
                thumb_lbl.pack(expand=True)

            display_name = entry.name
            max_chars    = max(6, (thumb_size + 20) // 7)
            if len(display_name) > max_chars:
                display_name = display_name[:max_chars - 2] + "…"

            name_lbl = tk.Label(
                cell, text=display_name,
                font=("Segoe UI", 8),
                bg=COLORS["bg_card"], fg=COLORS["text"],
                wraplength=thumb_size + 20)
            name_lbl.pack(pady=(3, 0))

            info = self._get_entry_info(entry)
            extra_widgets = []
            if entry.is_file() and info["resolution"]:
                rw, rh = info["resolution"]
                info_lbl = tk.Label(
                    cell, text=f"{rw}×{rh}",
                    font=("Segoe UI", 7),
                    bg=COLORS["bg_card"],
                    fg=COLORS["accent_yellow"])
                info_lbl.pack()
                extra_widgets.append(info_lbl)

            for w in [cell, thumb_lbl, name_lbl] + extra_widgets:
                w.bind("<Button-1>",
                       lambda e, i=idx: self._on_row_click(i))
                w.bind("<Double-Button-1>",
                       lambda e, i=idx: self._on_row_dblclick(i))

            col += 1

    def _row_hover(self, row, entering):
        color = COLORS["hover_bg"] if entering else COLORS["bg_card"]
        row.config(bg=color)
        for w in row.winfo_children():
            try:
                w.config(bg=color)
            except Exception:
                pass

    def _on_row_click(self, idx):
        if idx < 0 or idx >= len(self._entries):
            return
        path = self._entries[idx]
        self.selected_path = path
        self._update_info(path)
        self._show_preview(path)

    def _on_row_dblclick(self, idx):
        if idx < 0 or idx >= len(self._entries):
            return
        path = self._entries[idx]
        if path.is_dir():
            self._history.append(self.current_path)
            self._load_folder(path)

    def _clear_preview(self):
        self._preview_ref = None
        self.preview_canvas.delete("all")
        cw = self.preview_canvas.winfo_width()  or 280
        ch = self.preview_canvas.winfo_height() or 300
        self.preview_canvas.create_text(
            cw // 2, ch // 2,
            text="No preview",
            font=("Segoe UI", 12),
            fill=COLORS["text_dim"])
        self.sel_name_lbl.config(text="—")
        self.sel_type_lbl.config(text="")
        self.sel_size_lbl.config(text="")
        self.sel_res_lbl.config(text="")

    def _show_preview(self, path: Path):
        self.preview_canvas.delete("all")
        cw = self.preview_canvas.winfo_width()  or 280
        ch = self.preview_canvas.winfo_height() or 300

        if path.is_dir():
            self._preview_ref = None
            self.preview_canvas.create_text(
                cw // 2, ch // 2,
                text="📁",
                font=("Segoe UI", 52),
                fill=COLORS["folder_color"])
            return

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            self._preview_ref = None
            self.preview_canvas.create_text(
                cw // 2, ch // 2,
                text="📄\nNo preview",
                font=("Segoe UI", 14),
                fill=COLORS["text_dim"],
                justify="center")
            return

        try:
            img      = Image.open(path)
            img_copy = img.copy()
            img_copy.thumbnail(
                (max(40, cw - 10), max(40, ch - 10)),
                Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img_copy)
            self._preview_ref = tk_img
            self.preview_canvas.create_image(
                cw // 2, ch // 2,
                anchor="center", image=tk_img)
        except Exception:
            self._preview_ref = None
            self.preview_canvas.create_text(
                cw // 2, ch // 2,
                text="⚠️  Cannot preview",
                font=("Segoe UI", 11),
                fill=COLORS["accent_red"])

    def _update_info(self, path: Path):
        self.sel_name_lbl.config(text=path.name)
        info = self._get_entry_info(path)

        if path.is_dir():
            try:
                count = sum(1 for _ in path.iterdir())
            except PermissionError:
                count = "?"
            self.sel_type_lbl.config(
                text=f"Folder  •  {count} items",
                fg=COLORS["folder_color"])
            self.sel_size_lbl.config(text="")
            self.sel_res_lbl.config(text="")
        else:
            ext = path.suffix.upper().lstrip(".")
            self.sel_type_lbl.config(
                text=f"File  •  {ext}",
                fg=COLORS["file_color"])
            self.sel_size_lbl.config(
                text=f"Size: {format_size(info['size'])}")
            if info["resolution"]:
                rw, rh = info["resolution"]
                self.sel_res_lbl.config(
                    text=f"Resolution: {rw} × {rh}")
            else:
                self.sel_res_lbl.config(text="")


# ============================================================
#           TAB 1: SMART IMAGE TRIMMER
# ============================================================
class ImageTrimmerTab:
    def __init__(self, parent):
        self.frame        = tk.Frame(parent, bg=COLORS["bg_dark"])
        self.input_folder = None
        self.single_file  = None

        outer = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=COLORS["bg_dark"],
                           highlightthickness=0)
        vscroll = tk.Scrollbar(outer, orient="vertical",
                               command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._scroll_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        canvas_win = canvas.create_window(
            (0, 0), window=self._scroll_frame, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))

        self._build_content(self._scroll_frame)

    def _build_content(self, parent):
        tk.Label(parent, text="✂️  Smart Image Trimmer",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["accent_blue"]
                 ).pack(pady=(14, 2))

        tk.Label(parent,
                 text="Trim images with alpha threshold, color-based "
                      "trim, fuzz tolerance & padding",
                 font=("Segoe UI", 10),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(pady=(0, 8))

        self.drop_frame, self.drop_label = make_drop_zone(
            parent,
            "📁  Drag & Drop a FOLDER or IMAGE here\n"
            "or click to browse",
            on_drop_callback=self.on_drop,
            on_click_callback=self.browse,
        )

        src_card = tk.Frame(parent, bg=COLORS["bg_card"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
        src_card.pack(fill="x", padx=20, pady=5)
        src_inner = tk.Frame(src_card, bg=COLORS["bg_card"])
        src_inner.pack(fill="x", padx=15, pady=10)

        tk.Label(src_inner, text="Source:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        self.source_label = tk.Label(
            src_inner, text="None", font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["accent_blue"],
            wraplength=580, justify="left")
        self.source_label.pack(anchor="w")

        tk.Label(src_inner, text="Images Found:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w", pady=(5, 0))
        self.count_label = tk.Label(
            src_inner, text="0", font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["accent_orange"])
        self.count_label.pack(anchor="w")

        opts_card = tk.Frame(parent, bg=COLORS["bg_card"],
                             highlightbackground=COLORS["border"],
                             highlightthickness=1)
        opts_card.pack(fill="x", padx=20, pady=5)
        opts = tk.Frame(opts_card, bg=COLORS["bg_card"])
        opts.pack(fill="x", padx=15, pady=10)

        chk = tk.Frame(opts, bg=COLORS["bg_card"])
        chk.pack(anchor="w")

        self.overwrite_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            chk,
            text="Overwrite originals (no 'trimmed' subfolder)",
            variable=self.overwrite_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w")

        self.recursive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            chk,
            text="Include sub-folders recursively",
            variable=self.recursive_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w", pady=(4, 0))

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=8)

        tk.Label(opts, text="Alpha Threshold",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(opts,
                 text="Pixels with alpha < this are treated as "
                      "transparent.  0 = only pure alpha=0  |  "
                      "Higher = more aggressive",
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 wraplength=550, justify="left").pack(anchor="w")

        alpha_row = tk.Frame(opts, bg=COLORS["bg_card"])
        alpha_row.pack(fill="x", pady=(4, 0))
        self.alpha_var = tk.IntVar(value=10)
        self.alpha_lbl = tk.Label(
            alpha_row, text="10",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["accent_green"], width=4)
        self.alpha_lbl.pack(side="right")
        ttk.Scale(alpha_row, from_=0, to=254,
                  variable=self.alpha_var, orient="horizontal",
                  command=lambda v: self.alpha_lbl.config(
                      text=str(int(float(v))))
                  ).pack(side="left", fill="x", expand=True)

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=8)

        tk.Label(opts, text="Color Trim",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(opts,
                 text="Also remove pixels close to a target color "
                      "(for opaque white/black backgrounds)",
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 wraplength=550, justify="left").pack(anchor="w")

        self.color_trim_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            opts, text="Enable color trim",
            variable=self.color_trim_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
            command=self._toggle_color_opts,
        ).pack(anchor="w", pady=(4, 0))

        self._color_opts_frame = tk.Frame(opts, bg=COLORS["bg_card"])
        self._color_opts_frame.pack(fill="x")

        preset_row = tk.Frame(
            self._color_opts_frame, bg=COLORS["bg_card"])
        preset_row.pack(fill="x", pady=(4, 0))
        tk.Label(preset_row, text="Target:",
                 font=("Segoe UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]
                 ).pack(side="left")

        self.color_target = (255, 255, 255)
        self.color_preview_frame = tk.Frame(
            preset_row, bg="#ffffff", width=22, height=22,
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        self.color_preview_frame.pack(side="left", padx=6)

        for lbl_txt, rgb in [("White", (255, 255, 255)),
                              ("Black", (0, 0, 0)),
                              ("Pick…", None)]:
            tk.Button(
                preset_row, text=lbl_txt,
                font=("Segoe UI", 8),
                bg=COLORS["bg_card"], fg=COLORS["text"],
                relief="flat", cursor="hand2", padx=4,
                activebackground=COLORS["border"],
                command=lambda r=rgb: self._set_color_target(r)
            ).pack(side="left", padx=2)

        fuzz_frame = tk.Frame(
            self._color_opts_frame, bg=COLORS["bg_card"])
        fuzz_frame.pack(fill="x", pady=(6, 0))
        tk.Label(fuzz_frame, text="Fuzz / Tolerance:",
                 font=("Segoe UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(fuzz_frame,
                 text="How similar a color must be to get trimmed (0–255)",
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]
                 ).pack(anchor="w")

        fuzz_sl = tk.Frame(fuzz_frame, bg=COLORS["bg_card"])
        fuzz_sl.pack(fill="x")
        self.fuzz_var = tk.IntVar(value=30)
        self.fuzz_lbl = tk.Label(
            fuzz_sl, text="30",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["accent_green"], width=4)
        self.fuzz_lbl.pack(side="right")
        ttk.Scale(fuzz_sl, from_=0, to=255,
                  variable=self.fuzz_var, orient="horizontal",
                  command=lambda v: self.fuzz_lbl.config(
                      text=str(int(float(v))))
                  ).pack(side="left", fill="x", expand=True)

        self._toggle_color_opts()

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=8)

        tk.Label(opts, text="Padding (px)",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(opts,
                 text="Add pixels back around the result so edges "
                      "aren't clipped too tight",
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 wraplength=550, justify="left").pack(anchor="w")

        pad_row = tk.Frame(opts, bg=COLORS["bg_card"])
        pad_row.pack(fill="x", pady=(4, 0))
        self.pad_var = tk.IntVar(value=0)
        self.pad_lbl = tk.Label(
            pad_row, text="0",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["accent_green"], width=4)
        self.pad_lbl.pack(side="right")
        ttk.Scale(pad_row, from_=0, to=40,
                  variable=self.pad_var, orient="horizontal",
                  command=lambda v: self.pad_lbl.config(
                      text=str(int(float(v))))
                  ).pack(side="left", fill="x", expand=True)

        btn_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=8)
        self.trim_btn = make_hover_button(
            btn_frame, "✂️  Trim All Images",
            COLORS["accent_green"],
            self.start_trim, width=20, height=2)
        self.trim_btn.pack()

        self.progress_var = tk.DoubleVar()
        style = ttk.Style()
        style.theme_use("default")
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=COLORS["bg_card"],
                        background=COLORS["accent_green"],
                        thickness=18)
        ttk.Progressbar(
            parent, variable=self.progress_var, maximum=100,
            style="green.Horizontal.TProgressbar"
        ).pack(fill="x", padx=20, pady=(4, 0))

        self.log_text = tk.Text(
            parent, height=9,
            bg=COLORS["command_bg"], fg=COLORS["success"],
            font=("Consolas", 10),
            insertbackground=COLORS["text"],
            relief="flat", borderwidth=0,
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        self.log_text.pack(fill="both", expand=True,
                           padx=20, pady=(5, 14))

    def _toggle_color_opts(self):
        state = "normal" if self.color_trim_var.get() else "disabled"
        set_children_state(self._color_opts_frame, state)

    def _set_color_target(self, rgb):
        if rgb is None:
            from tkinter.colorchooser import askcolor
            result = askcolor(color="#ffffff",
                              title="Pick trim color")
            if result[0]:
                rgb = tuple(int(v) for v in result[0])
            else:
                return
        self.color_target = rgb
        self.color_preview_frame.config(
            bg="#{:02x}{:02x}{:02x}".format(*rgb))

    def browse(self, event=None):
        choice = _ask_file_or_folder(self.frame)
        if choice == "folder":
            folder = filedialog.askdirectory(
                title="Select folder with images")
            if folder:
                self.load_folder(folder)
        elif choice == "file":
            path = filedialog.askopenfilename(
                title="Select an image",
                filetypes=[("Image files",
                            "*.png *.jpg *.jpeg *.webp"),
                           ("All", "*.*")])
            if path:
                self.load_single_file(Path(path))

    def on_drop(self, event):
        paths = parse_drop_data(event.data.strip())
        if not paths:
            return
        p = Path(paths[0])
        if p.is_dir():
            self.load_folder(str(p))
        elif p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            self.load_single_file(p)
        else:
            messagebox.showwarning(
                "Unsupported", "Drop a folder or an image file.")

    def load_folder(self, folder_path):
        path = Path(folder_path)
        if not path.is_dir():
            messagebox.showerror("Error",
                                 f"Not a valid folder:\n{path}")
            return
        self.input_folder = path
        self.single_file  = None
        files = collect_images(path, recursive=True)
        self.source_label.config(text=str(path))
        self.count_label.config(text=f"{len(files)} image(s)")
        self.drop_label.config(
            text=f"✅  Folder: {path.name}", fg=COLORS["success"])
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

    def load_single_file(self, path: Path):
        self.single_file  = path
        self.input_folder = None
        self.source_label.config(text=str(path))
        self.count_label.config(text="1 image (single file)")
        self.drop_label.config(
            text=f"✅  File: {path.name}", fg=COLORS["success"])
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.frame.update_idletasks()

    def start_trim(self):
        if self.input_folder is None and self.single_file is None:
            messagebox.showwarning(
                "Nothing loaded",
                "Please select a folder or file first!")
            return
        threading.Thread(target=self.run_trim, daemon=True).start()

    def run_trim(self):
        self.trim_btn.config(state="disabled", text="⏳ Processing…")
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

        overwrite       = self.overwrite_var.get()
        recursive       = self.recursive_var.get()
        alpha_threshold = self.alpha_var.get()
        color_trim      = self.color_trim_var.get()
        color_target_v  = self.color_target
        color_fuzz      = self.fuzz_var.get()
        padding         = self.pad_var.get()

        if self.single_file:
            files    = [self.single_file]
            out_base = self.single_file.parent
        else:
            files    = collect_images(self.input_folder, recursive)
            out_base = self.input_folder

        total = len(files)
        if total == 0:
            self.log("⚠️ No image files found!")
            self.trim_btn.config(state="normal",
                                 text="✂️  Trim All Images")
            return

        self.log(f"📊 Found {total} image(s)")
        self.log(f"🔧 Alpha threshold: {alpha_threshold}")
        if color_trim:
            self.log(f"🎨 Color trim: ON  |  "
                     f"Target: {color_target_v}  |  Fuzz: {color_fuzz}")
        if padding > 0:
            self.log(f"📐 Padding: {padding}px")
        self.log("")

        success = 0
        for i, filepath in enumerate(files, 1):
            try:
                img = Image.open(filepath).convert("RGBA")
                trimmed = smart_trim(
                    img,
                    alpha_threshold=alpha_threshold,
                    color_trim=color_trim,
                    color_target=color_target_v,
                    color_fuzz=color_fuzz,
                    padding=padding,
                )

                if (trimmed.width == img.width and
                        trimmed.height == img.height):
                    self.log(
                        f"[{i}/{total}] ⏭️ {filepath.name}"
                        f"  |  {img.width}×{img.height} — no change")
                else:
                    if overwrite or self.single_file:
                        out_path = filepath
                    else:
                        rel      = filepath.relative_to(out_base)
                        out_path = out_base / "trimmed" / rel
                        out_path.parent.mkdir(
                            parents=True, exist_ok=True)

                    trimmed.save(out_path, "PNG")
                    old = f"{img.width}×{img.height}"
                    new = f"{trimmed.width}×{trimmed.height}"
                    self.log(
                        f"[{i}/{total}] ✅ {filepath.name}"
                        f"  |  {old} → {new}")
                    success += 1

            except Exception as e:
                self.log(
                    f"[{i}/{total}] ❌ {filepath.name} — {e}")

            self.progress_var.set((i / total) * 100)

        self.log(f"\n🎉 Done! {success}/{total} trimmed successfully.")
        if not overwrite and not self.single_file and success > 0:
            self.log(f"📁 Output: {out_base / 'trimmed'}")
        self.trim_btn.config(state="normal",
                             text="✂️  Trim All Images")


# ============================================================
#   TAB 2: IMAGE RESIZER
# ============================================================
class ImageResizerTab:
    MODES = [
        "Fit (keep ratio, no upscale)",
        "Fit + Upscale",
        "Exact Canvas (pad transparent)",
        "Long Edge",
        "Short Edge",
        "Width Only",
        "Height Only",
    ]

    PRESETS = {
        "Custom":       (0,    0),
        "512 × 512":    (512,  512),
        "1024 × 1024":  (1024, 1024),
        "2048 × 2048":  (2048, 2048),
        "256 × 256":    (256,  256),
        "128 × 128":    (128,  128),
        "1920 × 1080":  (1920, 1080),
        "1280 × 720":   (1280, 720),
    }

    def __init__(self, parent):
        self.frame        = tk.Frame(parent, bg=COLORS["bg_dark"])
        self.input_folder = None
        self.single_file  = None

        outer = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=COLORS["bg_dark"],
                           highlightthickness=0)
        vscroll = tk.Scrollbar(outer, orient="vertical",
                               command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._sf = tk.Frame(canvas, bg=COLORS["bg_dark"])
        _win = canvas.create_window((0, 0), window=self._sf,
                                    anchor="nw")

        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(_win, width=e.width))
        self._sf.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))

        self._build_content(self._sf)

    def _build_content(self, parent):
        tk.Label(parent, text="📐  Image Resizer",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["accent_blue"]
                 ).pack(pady=(14, 2))

        tk.Label(parent,
                 text="Batch-resize images while preserving aspect ratio  "
                      "•  multiple modes  •  optional canvas padding",
                 font=("Segoe UI", 10),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(pady=(0, 8))

        self.drop_frame, self.drop_label = make_drop_zone(
            parent,
            "📁  Drag & Drop a FOLDER or IMAGE here\nor click to browse",
            on_drop_callback=self._on_drop,
            on_click_callback=self._browse,
        )

        src_card = tk.Frame(parent, bg=COLORS["bg_card"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
        src_card.pack(fill="x", padx=20, pady=5)
        src_inner = tk.Frame(src_card, bg=COLORS["bg_card"])
        src_inner.pack(fill="x", padx=15, pady=10)

        tk.Label(src_inner, text="Source:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        self.source_label = tk.Label(
            src_inner, text="None", font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["accent_blue"],
            wraplength=580, justify="left")
        self.source_label.pack(anchor="w")

        tk.Label(src_inner, text="Images Found:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w", pady=(5, 0))
        self.count_label = tk.Label(
            src_inner, text="0", font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["accent_orange"])
        self.count_label.pack(anchor="w")

        opts_card = tk.Frame(parent, bg=COLORS["bg_card"],
                             highlightbackground=COLORS["border"],
                             highlightthickness=1)
        opts_card.pack(fill="x", padx=20, pady=5)
        opts = tk.Frame(opts_card, bg=COLORS["bg_card"])
        opts.pack(fill="x", padx=15, pady=12)

        chk = tk.Frame(opts, bg=COLORS["bg_card"])
        chk.pack(anchor="w")

        self.overwrite_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            chk,
            text="Overwrite originals (no 'resized' subfolder)",
            variable=self.overwrite_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w")

        self.recursive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            chk,
            text="Include sub-folders recursively",
            variable=self.recursive_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w", pady=(4, 0))

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=10)

        tk.Label(opts, text="Resize Mode",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")

        self.mode_var = tk.StringVar(value=self.MODES[0])
        mode_cb = ttk.Combobox(
            opts, textvariable=self.mode_var,
            values=self.MODES, state="readonly",
            font=("Segoe UI", 10), width=36)
        mode_cb.pack(anchor="w", pady=(4, 0))
        mode_cb.bind("<<ComboboxSelected>>", self._on_mode_changed)

        self._mode_desc = tk.Label(
            opts, text="",
            font=("Segoe UI", 8), bg=COLORS["bg_card"],
            fg=COLORS["text_dim"], wraplength=550, justify="left")
        self._mode_desc.pack(anchor="w", pady=(2, 0))

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=10)

        tk.Label(opts, text="Size Preset",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")

        preset_row = tk.Frame(opts, bg=COLORS["bg_card"])
        preset_row.pack(fill="x", pady=(4, 0))

        self.preset_var = tk.StringVar(value="Custom")
        preset_cb = ttk.Combobox(
            preset_row, textvariable=self.preset_var,
            values=list(self.PRESETS.keys()),
            state="readonly", font=("Segoe UI", 10), width=18)
        preset_cb.pack(side="left")
        preset_cb.bind("<<ComboboxSelected>>", self._on_preset_changed)

        tk.Label(preset_row, text="  or enter manually:",
                 font=("Segoe UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]
                 ).pack(side="left")

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=10)

        dim_row = tk.Frame(opts, bg=COLORS["bg_card"])
        dim_row.pack(fill="x")

        w_col = tk.Frame(dim_row, bg=COLORS["bg_card"])
        w_col.pack(side="left", padx=(0, 20))
        tk.Label(w_col, text="Width (px)",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        self.width_var = tk.StringVar(value="512")
        self._width_entry = tk.Entry(
            w_col, textvariable=self.width_var,
            font=("Segoe UI", 13, "bold"), width=8,
            bg=COLORS["bg_input"], fg=COLORS["accent_yellow"],
            insertbackground=COLORS["text"],
            relief="flat",
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        self._width_entry.pack()

        h_col = tk.Frame(dim_row, bg=COLORS["bg_card"])
        h_col.pack(side="left")
        tk.Label(h_col, text="Height (px)",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        self.height_var = tk.StringVar(value="512")
        self._height_entry = tk.Entry(
            h_col, textvariable=self.height_var,
            font=("Segoe UI", 13, "bold"), width=8,
            bg=COLORS["bg_input"], fg=COLORS["accent_yellow"],
            insertbackground=COLORS["text"],
            relief="flat",
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        self._height_entry.pack()

        self._dim_note = tk.Label(
            opts, text="",
            font=("Segoe UI", 8, "italic"),
            bg=COLORS["bg_card"], fg=COLORS["text_dim"])
        self._dim_note.pack(anchor="w", pady=(4, 0))

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=10)

        tk.Label(opts, text="Output Format",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        fmt_row = tk.Frame(opts, bg=COLORS["bg_card"])
        fmt_row.pack(anchor="w", pady=(4, 0))

        self.fmt_var = tk.StringVar(value="PNG")
        for fmt in ["PNG", "JPEG", "WEBP", "Keep original"]:
            tk.Radiobutton(
                fmt_row, text=fmt,
                variable=self.fmt_var, value=fmt,
                font=("Segoe UI", 9),
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_dark"],
                activebackground=COLORS["bg_card"],
            ).pack(side="left", padx=(0, 12))

        tk.Frame(opts, bg=COLORS["border"], height=1
                 ).pack(fill="x", pady=10)

        tk.Label(opts, text="Resampling Filter",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(opts,
                 text="LANCZOS = highest quality  •  BICUBIC = fast & smooth  "
                      "•  NEAREST = pixel-art",
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]
                 ).pack(anchor="w")

        filter_row = tk.Frame(opts, bg=COLORS["bg_card"])
        filter_row.pack(anchor="w", pady=(4, 0))
        self.filter_var = tk.StringVar(value="LANCZOS")
        for f in ["LANCZOS", "BICUBIC", "BILINEAR", "NEAREST"]:
            tk.Radiobutton(
                filter_row, text=f,
                variable=self.filter_var, value=f,
                font=("Segoe UI", 9),
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_dark"],
                activebackground=COLORS["bg_card"],
            ).pack(side="left", padx=(0, 10))

        self._on_mode_changed()

        btn_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=8)
        self.run_btn = make_hover_button(
            btn_frame, "📐  Resize All Images",
            COLORS["accent_purple"],
            self.start_resize, width=22, height=2)
        self.run_btn.pack()

        self.progress_var = tk.DoubleVar()
        style = ttk.Style()
        style.configure("purple.Horizontal.TProgressbar",
                        troughcolor=COLORS["bg_card"],
                        background=COLORS["accent_purple"],
                        thickness=18)
        ttk.Progressbar(
            parent, variable=self.progress_var, maximum=100,
            style="purple.Horizontal.TProgressbar"
        ).pack(fill="x", padx=20, pady=(4, 0))

        self.log_text = tk.Text(
            parent, height=9,
            bg=COLORS["command_bg"], fg=COLORS["success"],
            font=("Consolas", 10),
            insertbackground=COLORS["text"],
            relief="flat", borderwidth=0,
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        self.log_text.pack(fill="both", expand=True,
                           padx=20, pady=(5, 14))

    _MODE_DESCS = {
        "Fit (keep ratio, no upscale)":
            "Scale down so the image fits inside the W×H box. "
            "Images already smaller are left unchanged.",
        "Fit + Upscale":
            "Same as Fit but also enlarges small images to fill the box.",
        "Exact Canvas (pad transparent)":
            "Place the image (fitted) onto a W×H transparent canvas. "
            "All output images will be exactly W×H.",
        "Long Edge":
            "Scale so the longest side equals the Width value. "
            "Height field is ignored.",
        "Short Edge":
            "Scale so the shortest side equals the Width value. "
            "Height field is ignored.",
        "Width Only":
            "Scale so width equals the Width value; height follows ratio. "
            "Height field is ignored.",
        "Height Only":
            "Scale so height equals the Height value; width follows ratio. "
            "Width field is ignored.",
    }

    _SINGLE_AXIS = {
        "Long Edge", "Short Edge", "Width Only", "Height Only"}

    def _on_mode_changed(self, e=None):
        mode = self.mode_var.get()
        self._mode_desc.config(text=self._MODE_DESCS.get(mode, ""))
        if mode in self._SINGLE_AXIS:
            self._height_entry.config(state="disabled")
            self._dim_note.config(
                text="ℹ  Only the Width field is used in this mode "
                     "(except 'Height Only' which uses Height).")
            if mode == "Height Only":
                self._width_entry.config(state="disabled")
                self._height_entry.config(state="normal")
                self._dim_note.config(
                    text="ℹ  Only the Height field is used in this mode.")
            else:
                self._width_entry.config(state="normal")
        else:
            self._width_entry.config(state="normal")
            self._height_entry.config(state="normal")
            self._dim_note.config(text="")

    def _on_preset_changed(self, e=None):
        key = self.preset_var.get()
        if key == "Custom":
            return
        w, h = self.PRESETS[key]
        self.width_var.set(str(w))
        self.height_var.set(str(h))

    def _on_drop(self, event):
        paths = parse_drop_data(event.data.strip())
        if not paths:
            return
        p = Path(paths[0])
        if p.is_dir():
            self._load_folder(str(p))
        elif p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            self._load_single(p)
        else:
            messagebox.showwarning(
                "Unsupported", "Drop a folder or an image file.")

    def _browse(self, event=None):
        choice = _ask_file_or_folder(self.frame)
        if choice == "folder":
            folder = filedialog.askdirectory(
                title="Select folder with images")
            if folder:
                self._load_folder(folder)
        elif choice == "file":
            path = filedialog.askopenfilename(
                title="Select an image",
                filetypes=[("Image files",
                            "*.png *.jpg *.jpeg *.webp"),
                           ("All", "*.*")])
            if path:
                self._load_single(Path(path))

    def _load_folder(self, folder_path):
        path = Path(folder_path)
        if not path.is_dir():
            messagebox.showerror("Error", f"Not a valid folder:\n{path}")
            return
        self.input_folder = path
        self.single_file  = None
        files = collect_images(path, recursive=True)
        self.source_label.config(text=str(path))
        self.count_label.config(text=f"{len(files)} image(s)")
        self.drop_label.config(
            text=f"✅  Folder: {path.name}", fg=COLORS["success"])
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

    def _load_single(self, path: Path):
        self.single_file  = path
        self.input_folder = None
        self.source_label.config(text=str(path))
        self.count_label.config(text="1 image (single file)")
        self.drop_label.config(
            text=f"✅  File: {path.name}", fg=COLORS["success"])
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.frame.update_idletasks()

    def _get_filter(self):
        return {
            "LANCZOS":  Image.Resampling.LANCZOS,
            "BICUBIC":  Image.Resampling.BICUBIC,
            "BILINEAR": Image.Resampling.BILINEAR,
            "NEAREST":  Image.Resampling.NEAREST,
        }.get(self.filter_var.get(), Image.Resampling.LANCZOS)

    def _compute_new_size(self, orig_w, orig_h,
                          target_w, target_h, mode):
        if mode == "Fit (keep ratio, no upscale)":
            scale = min(target_w / orig_w, target_h / orig_h, 1.0)
            return int(orig_w * scale), int(orig_h * scale)
        elif mode == "Fit + Upscale":
            scale = min(target_w / orig_w, target_h / orig_h)
            return int(orig_w * scale), int(orig_h * scale)
        elif mode == "Exact Canvas (pad transparent)":
            scale = min(target_w / orig_w, target_h / orig_h, 1.0)
            return int(orig_w * scale), int(orig_h * scale)
        elif mode == "Long Edge":
            edge = max(orig_w, orig_h)
            scale = target_w / edge
            return int(orig_w * scale), int(orig_h * scale)
        elif mode == "Short Edge":
            edge = min(orig_w, orig_h)
            scale = target_w / edge
            return int(orig_w * scale), int(orig_h * scale)
        elif mode == "Width Only":
            scale = target_w / orig_w
            return int(orig_w * scale), int(orig_h * scale)
        elif mode == "Height Only":
            scale = target_h / orig_h
            return int(orig_w * scale), int(orig_h * scale)
        return orig_w, orig_h

    def _resize_image(self, img, target_w, target_h, mode, resample):
        orig_w, orig_h = img.size
        new_w, new_h   = self._compute_new_size(
            orig_w, orig_h, target_w, target_h, mode)

        if new_w == orig_w and new_h == orig_h:
            return img, False

        resized = img.resize((new_w, new_h), resample)

        if mode == "Exact Canvas (pad transparent)":
            canvas = Image.new("RGBA", (target_w, target_h),
                               (0, 0, 0, 0))
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) // 2
            canvas.paste(resized, (paste_x, paste_y))
            return canvas, True

        return resized, True

    def _output_ext(self, original: Path) -> str:
        fmt = self.fmt_var.get()
        if fmt == "Keep original":
            return original.suffix.lower()
        return {"PNG": ".png", "JPEG": ".jpg",
                "WEBP": ".webp"}.get(fmt, ".png")

    def _save_image(self, img, out_path, original):
        fmt = self.fmt_var.get()
        if fmt == "Keep original":
            fmt = original.suffix.lstrip(".").upper()
            if fmt == "JPG":
                fmt = "JPEG"
        if fmt in ("JPEG",):
            img = img.convert("RGB")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, fmt if fmt != "Keep original" else None)

    def start_resize(self):
        if self.input_folder is None and self.single_file is None:
            messagebox.showwarning(
                "Nothing loaded",
                "Please select a folder or file first!")
            return
        try:
            tw = int(self.width_var.get())
            th = int(self.height_var.get())
            if tw <= 0 or th <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid size",
                "Width and Height must be positive integers.")
            return

        threading.Thread(
            target=self._run_resize,
            args=(tw, th),
            daemon=True).start()

    def _run_resize(self, target_w, target_h):
        self.run_btn.config(state="disabled", text="⏳ Resizing…")
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

        mode      = self.mode_var.get()
        overwrite = self.overwrite_var.get()
        recursive = self.recursive_var.get()
        resample  = self._get_filter()

        if self.single_file:
            files    = [self.single_file]
            out_base = self.single_file.parent
        else:
            files    = collect_images(self.input_folder, recursive)
            out_base = self.input_folder

        total = len(files)
        if total == 0:
            self.log("⚠️ No image files found!")
            self.run_btn.config(state="normal",
                                text="📐  Resize All Images")
            return

        self.log(f"📐 Mode    : {mode}")
        self.log(f"📏 Target  : {target_w} × {target_h}")
        self.log(f"🔍 Filter  : {self.filter_var.get()}")
        self.log(f"📊 Files   : {total}\n")

        success = skipped = 0

        for i, filepath in enumerate(files, 1):
            try:
                img = Image.open(filepath).convert("RGBA")
                resized, changed = self._resize_image(
                    img, target_w, target_h, mode, resample)

                if not changed:
                    self.log(
                        f"[{i}/{total}] ⏭️ {filepath.name}"
                        f"  |  {img.width}×{img.height} — no change")
                    skipped += 1
                else:
                    ext = self._output_ext(filepath)
                    if overwrite or self.single_file:
                        out_path = filepath.with_suffix(ext)
                    else:
                        rel      = filepath.relative_to(out_base)
                        out_path = (out_base / "resized"
                                    / rel.with_suffix(ext))

                    self._save_image(resized, out_path, filepath)
                    old = f"{img.width}×{img.height}"
                    new = f"{resized.width}×{resized.height}"
                    self.log(
                        f"[{i}/{total}] ✅ {filepath.name}"
                        f"  |  {old} → {new}")
                    success += 1

            except Exception as e:
                self.log(
                    f"[{i}/{total}] ❌ {filepath.name} — {e}")

            self.progress_var.set((i / total) * 100)

        self.log(
            f"\n🎉 Done!  {success} resized  •  "
            f"{skipped} skipped  •  {total} total")
        if not overwrite and not self.single_file and success > 0:
            self.log(f"📁 Output: {out_base / 'resized'}")
        self.run_btn.config(state="normal",
                            text="📐  Resize All Images")


# ============================================================
#   TAB 3: BACKGROUND REMOVER (REMBG)
# ============================================================
class BackgroundRemoverTab:
    def __init__(self, parent, install_tab_ref=None):
        self.frame        = tk.Frame(parent, bg=COLORS["bg_dark"])
        self.input_folder = None
        self.single_file  = None
        self.install_tab  = install_tab_ref

        tk.Label(self.frame, text="🧠  Background Remover",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["accent_blue"]
                 ).pack(pady=(14, 2))

        tk.Label(self.frame,
                 text="Remove backgrounds using AI (rembg)  •  "
                      "Install models from the Install tab first",
                 font=("Segoe UI", 10),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(pady=(0, 8))

        self.drop_frame, self.drop_label = make_drop_zone(
            self.frame,
            "📁  Drag & Drop a FOLDER or IMAGE here\nor click to browse",
            on_drop_callback=self.on_drop,
            on_click_callback=self.browse,
            height=90,
        )

        scroll_outer = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        scroll_outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_outer, bg=COLORS["bg_dark"],
                           highlightthickness=0)
        vscroll = tk.Scrollbar(scroll_outer, orient="vertical",
                               command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        canvas_win  = canvas.create_window(
            (0, 0), window=inner_frame, anchor="nw")

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(canvas_win, width=e.width))
        inner_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))

        self._build_scrollable(inner_frame)

    def _build_scrollable(self, parent):
        options_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        options_card.pack(fill="x", padx=20, pady=5)

        opts = tk.Frame(options_card, bg=COLORS["bg_card"])
        opts.pack(fill="x", padx=15, pady=10)

        tk.Label(opts, text="Source:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        self.source_label = tk.Label(
            opts, text="None", font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["accent_blue"],
            wraplength=560, justify="left")
        self.source_label.pack(anchor="w")

        tk.Label(opts, text="Images Found:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w", pady=(5, 0))
        self.count_label = tk.Label(
            opts, text="0", font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["accent_orange"])
        self.count_label.pack(anchor="w")

        self.recursive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opts, text="Include sub-folders recursively",
            variable=self.recursive_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w", pady=(8, 0))

        # Model selection with status indicators
        model_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        model_card.pack(fill="x", padx=20, pady=5)

        model_header = tk.Frame(model_card, bg=COLORS["bg_card"])
        model_header.pack(fill="x", padx=15, pady=(10, 4))

        tk.Label(model_header, text="AI Model:",
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(side="left")

        tk.Label(model_header,
                 text="✅ = ready   ❌ = not installed (go to Install tab)",
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]
                 ).pack(side="right")

        models_frame = tk.Frame(model_card, bg=COLORS["bg_card"])
        models_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.model_var = tk.StringVar(value="isnet-general-use")
        self._model_status_labels = {}

        for label_text, model_id in REMBG_MODELS:
            row = tk.Frame(models_frame, bg=COLORS["bg_card"])
            row.pack(fill="x", pady=2)

            rb = tk.Radiobutton(
                row, text=label_text,
                variable=self.model_var, value=model_id,
                font=("Consolas", 10),
                bg=COLORS["bg_card"], fg=COLORS["text"],
                selectcolor=COLORS["bg_dark"],
                activebackground=COLORS["bg_card"],
                activeforeground=COLORS["accent_blue"],
                anchor="w", width=42,
            )
            rb.pack(side="left")

            status_lbl = tk.Label(
                row, text="⏳",
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                width=3)
            status_lbl.pack(side="left", padx=(4, 2))
            self._model_status_labels[model_id] = status_lbl

        # Check status on load
        self.frame.after(200, self.refresh_status)

        # Extra options
        extra_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        extra_card.pack(fill="x", padx=20, pady=5)

        extra = tk.Frame(extra_card, bg=COLORS["bg_card"])
        extra.pack(fill="x", padx=15, pady=10)

        self.alpha_mat_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            extra,
            text="Alpha Matting (-a) — Better edges (slower)",
            variable=self.alpha_mat_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w")

        self.trim_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            extra,
            text="✂️ Auto-trim after removal (uses smart trim)",
            variable=self.trim_var, font=("Segoe UI", 10),
            bg=COLORS["bg_card"], fg=COLORS["text"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text"],
        ).pack(anchor="w", pady=(5, 0))

        btn_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=8)
        self.run_btn = make_hover_button(
            btn_frame, "🧠  Remove Backgrounds",
            COLORS["accent_green"],
            self.start_removal, width=22, height=2)
        self.run_btn.pack()

        self.progress_var = tk.DoubleVar()
        style = ttk.Style()
        style.configure("blue.Horizontal.TProgressbar",
                        troughcolor=COLORS["bg_card"],
                        background=COLORS["accent_blue"],
                        thickness=18)
        ttk.Progressbar(
            parent, variable=self.progress_var, maximum=100,
            style="blue.Horizontal.TProgressbar"
        ).pack(fill="x", padx=20, pady=(4, 0))

        self.log_text = tk.Text(
            parent, height=7,
            bg=COLORS["command_bg"], fg=COLORS["success"],
            font=("Consolas", 10),
            insertbackground=COLORS["text"],
            relief="flat", borderwidth=0,
            highlightbackground=COLORS["border"],
            highlightthickness=1)
        self.log_text.pack(fill="both", expand=True,
                           padx=20, pady=(5, 14))

    def refresh_status(self):
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        for _, model_id in REMBG_MODELS:
            installed = is_model_installed(model_id)
            self.frame.after(
                0,
                lambda mid=model_id, ins=installed:
                    self._apply_status(mid, ins))

    def _apply_status(self, model_id, installed):
        lbl = self._model_status_labels.get(model_id)
        if lbl:
            if installed:
                lbl.config(text="✅", fg=COLORS["success"])
            else:
                lbl.config(text="❌", fg=COLORS["accent_red"])

    def browse(self, event=None):
        choice = _ask_file_or_folder(self.frame)
        if choice == "folder":
            folder = filedialog.askdirectory(
                title="Select folder with images")
            if folder:
                self.load_folder(folder)
        elif choice == "file":
            path = filedialog.askopenfilename(
                title="Select an image",
                filetypes=[("Image files",
                            "*.png *.jpg *.jpeg *.webp"),
                           ("All", "*.*")])
            if path:
                self.load_single_file(Path(path))

    def on_drop(self, event):
        paths = parse_drop_data(event.data.strip())
        if not paths:
            return
        p = Path(paths[0])
        if p.is_dir():
            self.load_folder(str(p))
        elif p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            self.load_single_file(p)
        else:
            messagebox.showwarning(
                "Unsupported", "Drop a folder or an image file.")

    def load_folder(self, folder_path):
        path = Path(folder_path)
        if not path.is_dir():
            messagebox.showerror("Error",
                                 f"Not a valid folder:\n{path}")
            return
        self.input_folder = path
        self.single_file  = None
        files = collect_images(path, recursive=True)
        self.source_label.config(text=str(path))
        self.count_label.config(text=f"{len(files)} image(s)")
        self.drop_label.config(
            text=f"✅  Folder: {path.name}", fg=COLORS["success"])
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

    def load_single_file(self, path: Path):
        self.single_file  = path
        self.input_folder = None
        self.source_label.config(text=str(path))
        self.count_label.config(text="1 image (single file)")
        self.drop_label.config(
            text=f"✅  File: {path.name}", fg=COLORS["success"])
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.frame.update_idletasks()

    def start_removal(self):
        if self.input_folder is None and self.single_file is None:
            messagebox.showwarning(
                "Nothing loaded",
                "Please select a folder or file!")
            return

        model = self.model_var.get()
        if not is_model_installed(model):
            messagebox.showwarning(
                "Model Not Installed",
                f"The model '{model}' is not installed.\n\n"
                f"Go to the ⚙️ Install tab to download it first.")
            return

        threading.Thread(target=self.run_removal, daemon=True).start()

    def run_removal(self):
        self.run_btn.config(state="disabled", text="⏳ Processing…")
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)

        model     = self.model_var.get()
        alpha     = self.alpha_mat_var.get()
        do_trim   = self.trim_var.get()
        recursive = self.recursive_var.get()

        if self.single_file:
            files      = [self.single_file]
            base_input = self.single_file.parent
        else:
            files      = collect_images(self.input_folder, recursive)
            base_input = self.input_folder

        total = len(files)
        if total == 0:
            self.log("⚠️ No image files found!")
            self.run_btn.config(state="normal",
                                text="🧠  Remove Backgrounds")
            return

        out_root = base_input / f"output_{model.replace('-', '_')}"
        out_root.mkdir(exist_ok=True)

        self.log(f"🧠 Model   : {model}")
        self.log(f"📂 Input   : {base_input}")
        self.log(f"📁 Output  : {out_root}")
        if alpha:
            self.log("🔧 Alpha Matting: ON")
        self.log(f"📊 Files   : {total}\n")

        success = 0
        for i, filepath in enumerate(files, 1):
            try:
                rel      = filepath.relative_to(base_input)
                out_path = out_root / rel.with_suffix(".png")
                out_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = ["rembg", "i"]
                if alpha:
                    cmd.append("-a")
                cmd.extend(["-m", model,
                            str(filepath), str(out_path)])

                self.log(f"[{i}/{total}] 🧠 {filepath.name} …")
                proc = subprocess.run(
                    cmd, capture_output=True, text=True)

                if proc.returncode != 0:
                    self.log(
                        f"  ❌ rembg error: "
                        f"{proc.stderr.strip() or proc.stdout.strip()}")
                else:
                    if do_trim:
                        img = Image.open(out_path).convert("RGBA")
                        trimmed = smart_trim(
                            img, alpha_threshold=10, padding=0)
                        if (trimmed.width != img.width or
                                trimmed.height != img.height):
                            trimmed.save(out_path, "PNG")
                    self.log(f"  ✅ done → {out_path.name}")
                    success += 1

            except FileNotFoundError:
                self.log("❌ rembg not found! Install it from the Install tab.")
                break
            except Exception as e:
                self.log(f"  ❌ {filepath.name} — {e}")

            self.progress_var.set((i / total) * 100)

        self.progress_var.set(100)
        self.log(f"\n🎉 Done! {success}/{total} processed.")
        self.log(f"📁 Output: {out_root}")
        self.run_btn.config(state="normal",
                            text="🧠  Remove Backgrounds")


# ============================================================
#   TAB 4: INSTALL (rembg + models)
# ============================================================
class InstallTab:
    """
    Dedicated tab for installing rembg and downloading AI models.
    Each install opens a real CMD / terminal window so the user
    can see progress directly — nothing runs hidden inside the app.
    """

    def __init__(self, parent, app_ref=None):
        self.frame   = tk.Frame(parent, bg=COLORS["bg_dark"])
        self.app_ref = app_ref

        self._model_status_labels = {}
        self._model_install_btns  = {}
        self._rembg_status_lbl    = None

        outer = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=COLORS["bg_dark"],
                           highlightthickness=0)
        vscroll = tk.Scrollbar(outer, orient="vertical",
                               command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        sf = tk.Frame(canvas, bg=COLORS["bg_dark"])
        _win = canvas.create_window((0, 0), window=sf, anchor="nw")

        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(_win, width=e.width))
        sf.bind("<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")))

        self._build(sf)
        self.frame.after(300, self.refresh_all)

    def _build(self, parent):
        tk.Label(parent, text="⚙️  Install & Setup",
                 font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["accent_blue"]
                 ).pack(pady=(14, 2))

        tk.Label(parent,
                 text="Install rembg and download AI model weights  •  "
                      "Each button opens a CMD window so you can watch progress",
                 font=("Segoe UI", 10),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(pady=(0, 12))

        refresh_row = tk.Frame(parent, bg=COLORS["bg_dark"])
        refresh_row.pack(fill="x", padx=20, pady=(0, 8))

        make_hover_button(
            refresh_row, "🔄  Refresh All Status",
            "#30363d", self.refresh_all,
            width=20, height=1, font_size=10
        ).pack(side="left")

        tk.Label(refresh_row,
                 text="   ✅ = installed / downloaded     "
                      "❌ = missing     ⏳ = checking …",
                 font=("Segoe UI", 9),
                 bg=COLORS["bg_dark"], fg=COLORS["text_dim"]
                 ).pack(side="left", padx=(10, 0))

        # SECTION 1: rembg package
        sec1 = tk.Frame(parent, bg=COLORS["bg_card"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        sec1.pack(fill="x", padx=20, pady=(0, 8))

        s1 = tk.Frame(sec1, bg=COLORS["bg_card"])
        s1.pack(fill="x", padx=15, pady=12)

        tk.Label(s1, text="1️⃣  rembg Package",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(s1,
                 text='The core AI background-removal library.  '
                      'Runs:  pip install "rembg[cpu,cli]"',
                 font=("Segoe UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 wraplength=600, justify="left"
                 ).pack(anchor="w", pady=(2, 6))

        rembg_row = tk.Frame(s1, bg=COLORS["bg_card"])
        rembg_row.pack(fill="x")

        self._rembg_status_lbl = tk.Label(
            rembg_row, text="⏳  Checking…",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["text_dim"])
        self._rembg_status_lbl.pack(side="left")

        self._rembg_install_btn = make_hover_button(
            rembg_row, "⬇  Install rembg",
            COLORS["accent_orange"],
            self._install_rembg,
            width=18, height=1, font_size=10)
        self._rembg_install_btn.pack(side="right")

        cmd_lbl = tk.Label(
            s1, text='pip install "rembg[cpu,cli]"',
            font=("Consolas", 10),
            bg=COLORS["command_bg"], fg=COLORS["accent_yellow"],
            padx=10, pady=4, anchor="w")
        cmd_lbl.pack(fill="x", pady=(4, 0))

        # SECTION 2: AI Models
        sec2 = tk.Frame(parent, bg=COLORS["bg_card"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        sec2.pack(fill="x", padx=20, pady=(0, 8))

        s2 = tk.Frame(sec2, bg=COLORS["bg_card"])
        s2.pack(fill="x", padx=15, pady=12)

        tk.Label(s2, text="2️⃣  AI Model Weights",
                 font=("Segoe UI", 12, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")
        tk.Label(s2,
                 text="Each model is an ONNX file (~50-170 MB) downloaded "
                      "from the internet on first use.\n"
                      "Click Install to open a CMD that triggers the download.  "
                      f"Models are saved to: {REMBG_MODEL_DIR}",
                 font=("Segoe UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 wraplength=600, justify="left"
                 ).pack(anchor="w", pady=(2, 8))

        for label_text, model_id in REMBG_MODELS:
            self._build_model_row(s2, label_text, model_id)

        # SECTION 3: info
        sec3 = tk.Frame(parent, bg=COLORS["bg_card"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1)
        sec3.pack(fill="x", padx=20, pady=(0, 14))

        s3 = tk.Frame(sec3, bg=COLORS["bg_card"])
        s3.pack(fill="x", padx=15, pady=12)

        tk.Label(s3, text="ℹ️  Info",
                 font=("Segoe UI", 11, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text"]
                 ).pack(anchor="w")

        info_lines = [
            f"Python:        {sys.executable}",
            f"Model folder:  {REMBG_MODEL_DIR}",
            f"Platform:      {sys.platform}",
        ]
        for line in info_lines:
            tk.Label(s3, text=line,
                     font=("Consolas", 9),
                     bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                     anchor="w").pack(anchor="w")

        btn_row = tk.Frame(s3, bg=COLORS["bg_card"])
        btn_row.pack(fill="x", pady=(8, 0))

        make_hover_button(
            btn_row, "📂  Open Model Folder",
            "#30363d",
            self._open_model_folder,
            width=20, height=1, font_size=9
        ).pack(side="left")

    def _build_model_row(self, parent, label_text, model_id):
        row = tk.Frame(parent, bg=COLORS["bg_card"])
        row.pack(fill="x", pady=4)

        status_lbl = tk.Label(
            row, text="⏳",
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["text_dim"],
            width=3)
        status_lbl.pack(side="left")
        self._model_status_labels[model_id] = status_lbl

        tk.Label(row, text=label_text,
                 font=("Consolas", 10),
                 bg=COLORS["bg_card"], fg=COLORS["text"],
                 anchor="w").pack(side="left", fill="x", expand=True)

        install_btn = make_hover_button(
            row, "⬇  Install",
            COLORS["accent_orange"],
            lambda mid=model_id: self._install_model(mid),
            width=10, height=1, font_size=9)
        install_btn.pack(side="right", padx=(6, 0))
        self._model_install_btns[model_id] = install_btn

        onnx_name = REMBG_MODEL_FILES.get(model_id, f"{model_id}.onnx")
        tk.Label(row, text=f"  → {onnx_name}",
                 font=("Consolas", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 anchor="w").pack(side="right", padx=(4, 8))

    # ----------------------------------------------------------
    #  Status refresh
    # ----------------------------------------------------------
    def refresh_all(self):
        if self._rembg_status_lbl:
            self._rembg_status_lbl.config(
                text="⏳  Checking…", fg=COLORS["text_dim"])
        for mid in self._model_status_labels:
            self._model_status_labels[mid].config(
                text="⏳", fg=COLORS["text_dim"])
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        rembg_ok = is_rembg_installed()
        self.frame.after(0, lambda: self._apply_rembg_status(rembg_ok))

        for _, model_id in REMBG_MODELS:
            installed = is_model_installed(model_id)
            self.frame.after(
                0,
                lambda mid=model_id, ins=installed:
                    self._apply_model_status(mid, ins))

        if self.app_ref:
            remover = self.app_ref.tabs.get("remover")
            if remover and hasattr(remover, 'refresh_status'):
                self.frame.after(100, remover.refresh_status)

    def _apply_rembg_status(self, installed):
        if installed:
            self._rembg_status_lbl.config(
                text="✅  rembg is installed",
                fg=COLORS["success"])
            self._rembg_install_btn.pack_forget()
        else:
            self._rembg_status_lbl.config(
                text="❌  rembg is NOT installed",
                fg=COLORS["accent_red"])
            self._rembg_install_btn.pack(side="right")

    def _apply_model_status(self, model_id, installed):
        lbl = self._model_status_labels.get(model_id)
        btn = self._model_install_btns.get(model_id)
        if not lbl:
            return
        if installed:
            lbl.config(text="✅", fg=COLORS["success"])
            if btn:
                btn.pack_forget()
        else:
            lbl.config(text="❌", fg=COLORS["accent_red"])
            if btn:
                btn.pack(side="right", padx=(6, 0))

    # ----------------------------------------------------------
    #  Write a temp .py script and run it in an external terminal
    # ----------------------------------------------------------
    def _write_temp_script(self, script_content: str) -> str:
        """Write script_content to a temp .py file, return its path."""
        import tempfile
        fd = tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False,
            prefix='toolkit_install_')
        fd.write(script_content)
        path = fd.name
        fd.close()
        return path

    def _install_rembg(self):
        """Open a CMD window that runs pip install rembg[cpu,cli]."""
        python = sys.executable
        script = f'''import subprocess, sys

print()
print("=" * 50)
print("  Installing rembg")
print("=" * 50)
print()
print('Running: pip install "rembg[cpu,cli]"')
print()

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "rembg[cpu,cli]"],
    capture_output=False
)

print()
if result.returncode == 0:
    print("SUCCESS! rembg is now installed.")
else:
    print("ERROR: pip install failed (see output above).")
print()
'''
        script_path = self._write_temp_script(script)
        self._open_cmd("Installing rembg",
                       f'"{python}" "{script_path}"')

    def _install_model(self, model_id: str):
        """Open a CMD that downloads the model via rembg."""
        python = sys.executable
        script = f'''import sys, os, subprocess, tempfile
from PIL import Image

print()
print("=" * 50)
print("  Downloading model: {model_id}")
print("=" * 50)
print()

# Create a tiny 1x1 dummy image
tmp_dir = tempfile.mkdtemp()
tmp_in  = os.path.join(tmp_dir, "dummy_in.png")
tmp_out = os.path.join(tmp_dir, "dummy_out.png")

Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(tmp_in)

print("Running rembg to trigger model download...")
print(f"  rembg i -m {model_id} <dummy_in> <dummy_out>")
print()
print("This may take a few minutes depending on your connection.")
print()

result = subprocess.run(
    ["rembg", "i", "-m", "{model_id}", tmp_in, tmp_out],
    capture_output=False
)

# Cleanup temp files
for f in [tmp_in, tmp_out]:
    try:
        os.remove(f)
    except Exception:
        pass
try:
    os.rmdir(tmp_dir)
except Exception:
    pass

print()
if result.returncode == 0:
    print("SUCCESS! Model '{model_id}' is now downloaded and ready.")
else:
    print("ERROR: Something went wrong (see output above).")
print()
'''
        script_path = self._write_temp_script(script)
        self._open_cmd(f"Installing model: {model_id}",
                       f'"{python}" "{script_path}"')

    def _open_cmd(self, title: str, command: str):
        """Open an external terminal window to run a command."""
        if sys.platform == "win32":
            # cmd /K keeps the window open after the command finishes
            # We wrap with pause so user sees the result
            bat_content = f'@echo off\ntitle {title}\n{command}\necho.\necho === Done! Press any key to close. ===\npause > nul\n'

            import tempfile
            bat_fd = tempfile.NamedTemporaryFile(
                mode='w', suffix='.bat', delete=False,
                prefix='toolkit_cmd_')
            bat_fd.write(bat_content)
            bat_path = bat_fd.name
            bat_fd.close()

            # Open the .bat in a new CMD window
            subprocess.Popen(
                ['cmd', '/c', 'start', title, bat_path],
                shell=False)

        elif sys.platform == "darwin":
            escaped = command.replace('"', '\\"')
            apple_script = (
                f'tell application "Terminal" to do script '
                f'"{escaped}"'
            )
            subprocess.Popen(["osascript", "-e", apple_script])
        else:
            for term in ["gnome-terminal", "konsole",
                         "xfce4-terminal", "xterm"]:
                try:
                    if term == "gnome-terminal":
                        subprocess.Popen(
                            [term, "--", "bash", "-c",
                             f'{command}; echo; echo "Done! Press Enter to close."; read'])
                    else:
                        subprocess.Popen(
                            [term, "-e",
                             f'bash -c \'{command}; echo; echo "Done! Press Enter."; read\''])
                    break
                except FileNotFoundError:
                    continue
            else:
                messagebox.showerror(
                    "No Terminal",
                    f"Could not find a terminal.\n\nRun manually:\n{command}")

        self.frame.after(8000, self.refresh_all)

    def _open_model_folder(self):
        folder = REMBG_MODEL_DIR
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
# ============================================================
#               HELPER: ask File or Folder
# ============================================================
def _ask_file_or_folder(parent):
    result = [None]
    dlg    = tk.Toplevel(parent)
    dlg.title("Browse…")
    dlg.configure(bg=COLORS["bg_dark"])
    dlg.resizable(False, False)
    dlg.grab_set()

    parent.update_idletasks()
    px = parent.winfo_rootx() + parent.winfo_width()  // 2
    py = parent.winfo_rooty() + parent.winfo_height() // 2
    dlg.geometry(f"280x130+{px - 140}+{py - 65}")

    tk.Label(dlg, text="What do you want to open?",
             font=("Segoe UI", 11, "bold"),
             bg=COLORS["bg_dark"], fg=COLORS["text"]
             ).pack(pady=(18, 10))

    btn_row = tk.Frame(dlg, bg=COLORS["bg_dark"])
    btn_row.pack()

    def pick(val):
        result[0] = val
        dlg.destroy()

    make_hover_button(
        btn_row, "📁  Folder", COLORS["accent_orange"],
        lambda: pick("folder"),
        width=10, height=1, font_size=10
    ).pack(side="left", padx=8)

    make_hover_button(
        btn_row, "🖼️  File", COLORS["accent_blue"],
        lambda: pick("file"),
        width=10, height=1, font_size=10
    ).pack(side="left", padx=8)

    dlg.wait_window()
    return result[0]


# ============================================================
#                    MAIN APPLICATION
# ============================================================
class AssetToolkit:
    def __init__(self, root):
        self.root = root
        self.root.title(f"⚒️ {APP_NAME}")
        self.root.configure(bg=COLORS["bg_dark"])
        self.root.minsize(860, 900)
        center_window(root, 980, 980)

        # Header
        header = tk.Frame(root, bg=COLORS["bg_card"], height=52)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header,
                 text=f"⚒️  {APP_NAME}",
                 font=("Segoe UI", 15, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["accent_orange"]
                 ).pack(side="left", padx=20, pady=12)

        version_frame = tk.Frame(header, bg=COLORS["bg_card"])
        version_frame.pack(side="right", padx=20)

        tk.Label(version_frame,
                 text=APP_VERSION,
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["accent_blue"]
                 ).pack(anchor="e")
        tk.Label(version_frame,
                 text=APP_STUDIO,
                 font=("Segoe UI", 8),
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]
                 ).pack(anchor="e")

        # Tab bar
        tab_bar = tk.Frame(root, bg=COLORS["bg_dark"])
        tab_bar.pack(fill="x", padx=20, pady=(10, 0))

        container = tk.Frame(root, bg=COLORS["bg_dark"])
        container.pack(fill="both", expand=True)

        self.tabs        = {}
        self.tab_buttons = {}
        self.current_tab = None

        # Build Install tab first so other tabs can reference it
        install_tab = InstallTab(container, app_ref=self)
        self.tabs["install"] = install_tab

        tab_defs = [
            ("📂 Explorer",   "explorer"),
            ("✂️ Trimmer",    "trimmer"),
            ("📐 Resizer",    "resizer"),
            ("🧠 BG Remover", "remover"),
            ("⚙️ Install",    "install"),
        ]

        for label, key in tab_defs:
            if key == "explorer":
                self.tabs[key] = FileExplorerTab(container, self)
            elif key == "trimmer":
                self.tabs[key] = ImageTrimmerTab(container)
            elif key == "resizer":
                self.tabs[key] = ImageResizerTab(container)
            elif key == "remover":
                self.tabs[key] = BackgroundRemoverTab(
                    container, install_tab_ref=install_tab)
            # "install" already created above

            btn = tk.Button(
                tab_bar, text=label,
                font=("Segoe UI", 11, "bold"),
                bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                activebackground=COLORS["accent_blue"],
                activeforeground="white",
                relief="flat", bd=0,
                padx=18, pady=8, cursor="hand2",
                command=lambda k=key: self.switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 2))
            self.tab_buttons[key] = btn

        self.switch_tab("explorer")

    def switch_tab(self, key):
        for tab in self.tabs.values():
            tab.frame.pack_forget()
        for k, btn in self.tab_buttons.items():
            btn.config(bg=COLORS["bg_card"], fg=COLORS["text_dim"])
        self.tabs[key].frame.pack(fill="both", expand=True)
        self.tab_buttons[key].config(
            bg=COLORS["accent_blue"], fg="white")
        self.current_tab = key

        # Auto-refresh status when switching to Install or BG Remover
        if key == "install":
            self.tabs["install"].refresh_all()
        elif key == "remover":
            self.tabs["remover"].refresh_status()


# ============================================================
#                        RUN
# ============================================================
if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = AssetToolkit(root)
    root.mainloop()