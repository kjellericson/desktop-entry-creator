#!/usr/bin/env python3

import os
import re
import sys
import shutil
import subprocess
import colorsys
import hashlib
import html
import random
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

ICON_DISPLAY_SIZE = 128


class DesktopEntryCreatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Desktop Entry Creator")
        self.root.geometry("980x760")
        self.root.minsize(900, 700)

        self.display_icon_image = None

        self.variables = {}
        self.tooltip = None
        self._updating_preview = False
        self.last_desktop_file = None
        self.pending_generated_icon_svg = None
        self.pending_generated_icon_spec = None
        self.unknown_lines = []
        self.field_help = {
            "name": "The visible app name that appears in menus, launchers, and app grids. This is the friendly label users see.",
            "generic_name": "A generic label for the app category, such as 'Text Editor' or 'Browser'. It helps desktop search and grouping.",
            "comment": "A short description shown by the desktop environment when you hover over the app or view details.",
            "exec": "The exact command that launches the program. This is the most important field: it tells the desktop what to run.",
            "icon": "The icon displayed for the launcher. Use an icon name from the system theme or a full file path to a PNG/SVG icon.",
            "path": "The startup path or working directory the app should use as a filesystem location. Useful for apps that expect to run from a specific folder.",
            "working_dir": "The directory from which the command should start. This is useful for apps that read local files or expect a certain base folder.",
            "categories": "Semicolon-separated categories like Utility;Development;Game; to help the desktop organize and filter the app.",
            "keywords": "Additional search keywords separated by semicolons so users can find the app through launcher search.",
            "startup_wm_class": "The window manager class used to identify the app's main window. Often used for window rules and matching.",
            "mime_type": "The MIME types this app can open, if it is a file-association application such as an editor or viewer.",
            "try_exec": "Optional path to a binary that must exist before launch. If it is missing, the desktop won't launch the app.",
            "version": "The launcher version string. This helps identify the desktop entry metadata, not usually the program version itself.",
            "terminal": "Runs the command in a terminal window instead of as a background GUI app. Use this for console programs or debugging.",
            "startup_notify": "Tells the desktop environment to show launch feedback such as a splash or progress animation while the app starts.",
            "type": "The desktop entry type: Application launches a program, Link points to a URL or file, and Directory represents a folder entry.",
        }
        self._build_ui()
        self.root.bind("<Control-w>", self._quit_application)
        self.root.bind("<Control-W>", self._quit_application)
        self._reset_form()
        self._refresh_preview()

    def _show_tooltip(self, event, text):
        if self.tooltip is not None:
            self._hide_tooltip()

        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        self.tooltip.geometry(f"+{event.x_root + 18}+{event.y_root + 18}")

        label = tk.Label(
            self.tooltip,
            text=text,
            justify="left",
            background="#fff9c4",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=5,
            wraplength=260,
        )
        label.pack()
        self.tooltip.deiconify()

    def _hide_tooltip(self, event=None):
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None

    def _attach_tooltip(self, widget, text):
        widget.bind("<Enter>", lambda event: self._show_tooltip(event, text))
        widget.bind("<Leave>", self._hide_tooltip)

    def _select_field_path(self, var, kind):
        current_value = var.get().strip()
        initialdir, initialpath = self._resolve_dialog_initial_path(
            current_value)

        if kind == "directory":
            value = self._ask_directory(
                title="Select directory",
                initialdir=initialdir,
            )
        elif kind == "icon":
            value = self._ask_open_file(
                title="Select icon file",
                filetypes=[
                    ("Image Files", "*.png *.jpg *.jpeg *.gif *.svg *.xpm *.ico"),
                    ("All Files", "*.*"),
                ],
                initialdir=initialdir,
                initialpath=initialpath,
            )
        else:
            value = self._ask_open_file(
                title="Select file",
                filetypes=[("All Files", "*.*")],
                initialdir=initialdir,
                initialpath=initialpath,
            )

        if value:
            var.set(value)

    @staticmethod
    def _resolve_dialog_initial_path(value):
        if not value:
            return None, None

        candidate = Path(value).expanduser()
        if candidate.is_dir():
            return str(candidate), str(candidate)
        if candidate.is_file():
            return str(candidate.parent), str(candidate)

        parent = candidate.parent
        if str(parent) and str(parent) != ".":
            return str(parent), str(candidate)
        return None, None

    def _run_system_dialog(self, command):
        root = getattr(self, "root", None)
        root_was_visible = False
        if root is not None:
            try:
                root_was_visible = root.state() != "withdrawn"
                if root_was_visible:
                    root.withdraw()
            except tk.TclError:
                root_was_visible = False

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            if root is not None and root_was_visible:
                try:
                    root.deiconify()
                    root.lift()
                    root.focus_force()
                except tk.TclError:
                    pass
            return True, None
        finally:
            if root is not None and root_was_visible:
                try:
                    root.deiconify()
                    root.lift()
                    root.focus_force()
                except tk.TclError:
                    pass

        if result.returncode == 0:
            selected = result.stdout.strip()
            return True, selected or None
        return True, None

    def _dialog_window_id(self):
        root = getattr(self, "root", None)
        if root is None:
            return None
        try:
            return str(root.winfo_id())
        except tk.TclError:
            return None

    def _ask_open_file(self, title, filetypes, initialdir=None, initialpath=None):
        handled, selected = self._ask_open_file_system_dialog(
            title=title,
            filetypes=filetypes,
            initialdir=initialdir,
            initialpath=initialpath,
        )
        if handled:
            return selected

        return self._run_foreground_dialog(lambda: filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initialdir,
            initialfile=Path(initialpath).name if initialpath else None,
            parent=getattr(self, "root", None),
        ))

    def _run_foreground_dialog(self, dialog_callable):
        root = getattr(self, "root", None)
        if root is None:
            return dialog_callable()

        previous_topmost = False
        try:
            previous_topmost = bool(root.attributes("-topmost"))
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            root.update_idletasks()
        except tk.TclError:
            pass

        try:
            return dialog_callable()
        finally:
            try:
                root.attributes("-topmost", previous_topmost)
                root.lift()
            except tk.TclError:
                pass

    def _ask_directory(self, title, initialdir=None):
        handled, selected = self._ask_directory_system_dialog(
            title=title,
            initialdir=initialdir,
        )
        if handled:
            return selected

        return self._run_foreground_dialog(lambda: filedialog.askdirectory(
            title=title,
            initialdir=initialdir,
            parent=getattr(self, "root", None),
        ))

    def _ask_save_file(self, title, defaultextension, filetypes, initialdir, initialfile):
        handled, selected = self._ask_save_file_system_dialog(
            title=title,
            filetypes=filetypes,
            initialdir=initialdir,
            initialfile=initialfile,
        )
        if handled:
            return selected

        return self._run_foreground_dialog(lambda: filedialog.asksaveasfilename(
            title=title,
            defaultextension=defaultextension,
            filetypes=filetypes,
            initialdir=initialdir,
            initialfile=initialfile,
            parent=getattr(self, "root", None),
        ))

    @staticmethod
    def _format_kdialog_filters(filetypes):
        patterns = []
        for _label, pattern in filetypes:
            patterns.extend(part for part in pattern.split() if part)
        return " ".join(patterns) or "*"

    @staticmethod
    def _format_zenity_filters(filetypes):
        filters = []
        for label, pattern in filetypes:
            filters.append(f"{label} | {pattern}")
        return filters

    def _ask_open_file_system_dialog(self, title, filetypes, initialdir=None, initialpath=None):
        window_id = self._dialog_window_id()
        if shutil.which("zenity"):
            command = ["zenity", "--file-selection",
                       "--title", title, "--modal"]
            if window_id:
                command.extend(["--attach", window_id])
            for file_filter in self._format_zenity_filters(filetypes):
                command.extend(["--file-filter", file_filter])
            if initialpath:
                command.extend(["--filename", initialpath])
            elif initialdir:
                command.extend(["--filename", os.path.join(initialdir, "")])
            return self._run_system_dialog(command)

        if shutil.which("kdialog"):
            start_path = initialpath or initialdir or os.path.expanduser("~")
            command = [
                "kdialog",
                "--title",
                title,
                "--getopenfilename",
                start_path,
                self._format_kdialog_filters(filetypes),
            ]
            if window_id:
                command[1:1] = ["--attach", window_id]
            return self._run_system_dialog(command)

        return False, None

    def _ask_directory_system_dialog(self, title, initialdir=None):
        window_id = self._dialog_window_id()
        if shutil.which("zenity"):
            command = ["zenity", "--file-selection",
                       "--directory", "--title", title, "--modal"]
            if window_id:
                command.extend(["--attach", window_id])
            if initialdir:
                command.extend(["--filename", os.path.join(initialdir, "")])
            return self._run_system_dialog(command)

        if shutil.which("kdialog"):
            start_path = initialdir or os.path.expanduser("~")
            command = ["kdialog", "--title", title,
                       "--getexistingdirectory", start_path]
            if window_id:
                command[1:1] = ["--attach", window_id]
            return self._run_system_dialog(command)

        return False, None

    def _ask_save_file_system_dialog(self, title, filetypes, initialdir, initialfile):
        window_id = self._dialog_window_id()
        if shutil.which("zenity"):
            suggested = os.path.join(initialdir, initialfile)
            command = [
                "zenity",
                "--file-selection",
                "--save",
                "--confirm-overwrite",
                "--title",
                title,
                "--modal",
                "--filename",
                suggested,
            ]
            if window_id:
                command.extend(["--attach", window_id])
            for file_filter in self._format_zenity_filters(filetypes):
                command.extend(["--file-filter", file_filter])
            return self._run_system_dialog(command)

        if shutil.which("kdialog"):
            suggested = os.path.join(initialdir, initialfile)
            command = [
                "kdialog",
                "--title",
                title,
                "--getsavefilename",
                suggested,
                self._format_kdialog_filters(filetypes),
            ]
            if window_id:
                command[1:1] = ["--attach", window_id]
            return self._run_system_dialog(command)

        return False, None

    def _add_field(self, parent, row, label, key, default="", width=36, chooser=None):
        help_text = self.field_help.get(key, "Information about this field.")

        question = ttk.Label(parent, text="?", foreground="#2b6cb0",
                             font=("TkDefaultFont", 10, "bold"))
        question.grid(row=row, column=0, sticky="w", padx=(10, 4), pady=(8, 4))
        self._attach_tooltip(question, help_text)

        label_widget = ttk.Label(parent, text=f"{label}:")
        label_widget.grid(row=row, column=1, sticky="w",
                          padx=(0, 8), pady=(8, 4))
        self._attach_tooltip(label_widget, help_text)

        var = tk.StringVar(value=default)
        var.trace_add("write", lambda *_: self._refresh_preview())
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=2, sticky="ew", padx=(0, 10), pady=(8, 4))

        if chooser:
            button = ttk.Button(
                parent, text="Browse", command=lambda: self._select_field_path(var, chooser))
            button.grid(row=row, column=3, sticky="w",
                        padx=(0, 10), pady=(8, 4))

        self.variables[key] = var
        return var

    def _add_checkbox(self, parent, row, label, key, default=False):
        help_text = self.field_help.get(key, "Information about this field.")

        question = ttk.Label(parent, text="?", foreground="#2b6cb0",
                             font=("TkDefaultFont", 10, "bold"))
        question.grid(row=row, column=0, sticky="w", padx=(10, 4), pady=(8, 4))
        self._attach_tooltip(question, help_text)

        var = tk.BooleanVar(value=default)
        var.trace_add("write", lambda *_: self._refresh_preview())
        checkbox = ttk.Checkbutton(parent, text=label, variable=var)
        checkbox.grid(row=row, column=1, sticky="w", padx=(0, 10), pady=(8, 4))
        self._attach_tooltip(checkbox, help_text)
        self.variables[key] = var
        return var

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        main.columnconfigure(1, weight=1)

        form = ttk.LabelFrame(main, text="Launcher details", padding=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))
        form.columnconfigure(2, weight=1)

        self._add_field(form, 0, "Name", "name", "My App")
        self._add_field(form, 1, "Generic Name", "generic_name", "Application")
        self._add_field(form, 2, "Comment", "comment",
                        "Launch the application")
        self._add_field(form, 3, "Exec", "exec",
                        "/usr/bin/firefox --new-window", chooser="file")
        self._add_field(form, 4, "Icon", "icon",
                        "/usr/share/icons/hicolor/256x256/apps/firefox.png", chooser="icon")
        self._add_field(form, 5, "Path", "path",
                        "/home/your-user", chooser="directory")
        self._add_field(form, 6, "Working Directory",
                        "working_dir", os.getcwd(), chooser="directory")
        self._add_field(form, 7, "Categories", "categories",
                        "Utility;Development;")
        self._add_field(form, 8, "Keywords", "keywords", "app;desktop;utility")
        self._add_field(form, 9, "Startup WM Class", "startup_wm_class", "")
        self._add_field(form, 10, "Mime Type", "mime_type", "")
        self._add_field(form, 11, "Try Exec", "try_exec", "", chooser="file")
        self._add_field(form, 12, "Version", "version", "1.0")
        self._add_checkbox(form, 13, "Run in terminal", "terminal", False)
        self._add_checkbox(form, 14, "Startup Notify", "startup_notify", True)

        dropdown_frame = ttk.Frame(form)
        dropdown_frame.grid(row=15, column=2, sticky="ew",
                            padx=(0, 10), pady=(8, 4))

        question = ttk.Label(form, text="?", foreground="#2b6cb0",
                             font=("TkDefaultFont", 10, "bold"))
        question.grid(row=15, column=0, sticky="w", padx=(10, 4), pady=(8, 4))
        self._attach_tooltip(question, self.field_help["type"])

        ttk.Label(form, text="Type:").grid(row=15, column=1,
                                           sticky="w", padx=(0, 8), pady=(8, 4))
        self.type_var = tk.StringVar(value="Application")
        self.type_var.trace_add("write", lambda *_: self._refresh_preview())
        ttk.Combobox(
            dropdown_frame,
            textvariable=self.type_var,
            values=["Application", "Link", "Directory"],
            state="readonly",
            width=34,
        ).pack(fill="x")

        actions_frame = ttk.Frame(main)
        actions_frame.grid(row=0, column=1, sticky="nsew")
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(actions_frame)
        header.grid(row=0, column=0, sticky="w", padx=10, pady=(0, 6))
        icon_frame = ttk.Frame(
            header, width=ICON_DISPLAY_SIZE, height=ICON_DISPLAY_SIZE)
        icon_frame.pack(side="left", padx=(0, 10))
        icon_frame.pack_propagate(False)

        self.icon_canvas = tk.Canvas(
            icon_frame,
            width=ICON_DISPLAY_SIZE,
            height=ICON_DISPLAY_SIZE,
            highlightthickness=0,
            background="white",
        )
        self.icon_canvas.pack(fill="both", expand=True)

        top_actions = ttk.Frame(header)
        top_actions.pack(side="left", fill="y")
        ttk.Button(top_actions, text="Generate icons", command=self._generate_icon_file).pack(
            anchor="nw", pady=(2, 0))

        preview_label = ttk.Label(
            actions_frame, text="Generated desktop entry")
        preview_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))

        self.preview = tk.Text(actions_frame, wrap="word",
                               height=28, font=("Monospace", 10))
        self.preview.grid(row=2, column=0, sticky="nsew",
                          padx=(10, 10), pady=(0, 10))

        buttons = ttk.Frame(actions_frame)
        buttons.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)
        buttons.columnconfigure(3, weight=1)

        ttk.Button(buttons, text="Save .desktop", command=self._save_desktop_file).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(buttons, text="Load .desktop", command=self._load_desktop_file).grid(
            row=0, column=1, sticky="ew", padx=(5, 5))
        ttk.Button(buttons, text="Reset", command=self._reset_form).grid(
            row=0, column=3, sticky="ew", padx=(5, 0))

        footer_label = ttk.Label(main, text="kjell@haxx.se")
        footer_label.grid(row=1, column=0, columnspan=2,
                          sticky="e", padx=(0, 4), pady=(4, 0))

        self.preview.bind("<KeyRelease>", self._on_preview_edit)

    def _seed_example(self):
        self.variables["name"].set("Example App")
        self.variables["generic_name"].set("Developer Tool")
        self.variables["comment"].set("Open the Example App")
        self.variables["exec"].set("/usr/bin/gedit")
        self.variables["icon"].set("accessories-text-editor")
        self.variables["path"].set("/home/your-user")
        self.variables["working_dir"].set(os.getcwd())
        self.variables["categories"].set("Utility;TextEditor;")
        self.variables["keywords"].set("editor;text;utility")
        self.variables["startup_wm_class"].set("")
        self.variables["mime_type"].set("")
        self.variables["try_exec"].set("")
        self.variables["version"].set("1.0")
        self.variables["terminal"].set(False)
        self.variables["startup_notify"].set(True)

    def _reset_form(self):
        for key, variable in self.variables.items():
            if isinstance(variable, tk.StringVar):
                variable.set("")
            elif isinstance(variable, tk.BooleanVar):
                variable.set(False)
        self.type_var.set("Application")
        self.pending_generated_icon_svg = None
        self.pending_generated_icon_spec = None
        self._refresh_preview()

    def _string_value(self, key, fallback=""):
        value = self.variables.get(key)
        if value is None:
            return fallback
        if isinstance(value, tk.BooleanVar):
            return "true" if value.get() else "false"
        getter = getattr(value, "get", None)
        if callable(getter):
            value = getter()
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            text = value.strip()
        else:
            text = str(value).strip()
        if text.lower() in {"true", "false"}:
            return text.lower()
        return text

    def generate_desktop_entry(self):
        lines = [
            "[Desktop Entry]",
            f"Version={self._string_value('version', '1.0') or '1.0'}",
            f"Type={self.type_var.get()}",
        ]

        for key, field_name in [
            ("name", "Name"),
            ("generic_name", "GenericName"),
            ("comment", "Comment"),
            ("exec", "Exec"),
            ("icon", "Icon"),
            ("path", "Path"),
            ("working_dir", "X-WorkingDirectory"),
            ("try_exec", "TryExec"),
            ("startup_wm_class", "StartupWMClass"),
            ("mime_type", "MimeType"),
            ("categories", "Categories"),
            ("keywords", "Keywords"),
        ]:
            value = self._string_value(key)
            if value:
                lines.append(f"{field_name}={value}")

        terminal_value = self._string_value("terminal")
        startup_notify = self._string_value("startup_notify")
        lines.extend([
            f"Terminal={terminal_value}",
            f"StartupNotify={startup_notify}",
        ])

        unknown_lines = getattr(self, "unknown_lines", [])
        if unknown_lines:
            lines.extend(unknown_lines)

        return "\n".join(lines) + "\n"

    def _apply_desktop_entry_text(self, text):
        entries = {}
        self.unknown_lines = []
        remap = {
            "Name": "name",
            "GenericName": "generic_name",
            "Comment": "comment",
            "Exec": "exec",
            "Icon": "icon",
            "Path": "path",
            "WorkingDirectory": "working_dir",
            "X-WorkingDirectory": "working_dir",
            "TryExec": "try_exec",
            "StartupWMClass": "startup_wm_class",
            "MimeType": "mime_type",
            "Categories": "categories",
            "Keywords": "keywords",
            "Version": "version",
            "Terminal": "terminal",
            "StartupNotify": "startup_notify",
        }
        remap_by_lower = {key.lower(): value for key, value in remap.items()}
        unknown_entries = {}
        unknown_order = []

        for line in text.splitlines():
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                continue
            if "=" not in line:
                if line not in unknown_order:
                    unknown_order.append(line)
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            key_lower = key.lower()
            if key_lower == "type":
                self.type_var.set(value)
                continue
            if key_lower in remap_by_lower:
                entries[key_lower] = value
            else:
                unknown_entries.pop(key_lower, None)
                unknown_entries[key_lower] = f"{key}={value}"

        self.unknown_lines = unknown_order + list(unknown_entries.values())

        for key_lower, mapped_key in remap_by_lower.items():
            if key_lower not in entries:
                continue
            value = entries[key_lower]
            if mapped_key in self.variables:
                variable = self.variables[mapped_key]
                if mapped_key in {"terminal", "startup_notify"}:
                    variable.set(value.lower() == "true")
                else:
                    variable.set(value)

    def _on_preview_edit(self, event=None):
        text = self.preview.get("1.0", tk.END).strip()
        if not text:
            return
        self._updating_preview = True
        try:
            self._apply_desktop_entry_text(text)
        finally:
            self._updating_preview = False

    def _refresh_preview(self):
        if self._updating_preview:
            return
        content = self.generate_desktop_entry()
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", content)
        self._update_gui_icon_from_field()

    def _update_gui_icon_from_field(self):
        pending_spec = getattr(self, "pending_generated_icon_spec", None)
        if pending_spec is not None and hasattr(self, "icon_canvas"):
            self._draw_icon_preview(
                self.icon_canvas, pending_spec, ICON_DISPLAY_SIZE)
            self.display_icon_image = None
            return

        icon_path = self._string_value("icon", "")
        selected_icon = None
        if icon_path:
            candidate = Path(icon_path).expanduser()
            if candidate.is_file():
                try:
                    selected_icon = tk.PhotoImage(file=str(candidate))
                    selected_icon = self._fit_image_to_display(selected_icon)
                except tk.TclError:
                    selected_icon = None

        self.display_icon_image = selected_icon

        if hasattr(self, "icon_canvas"):
            self.icon_canvas.delete("all")
            if self.display_icon_image is not None:
                self.icon_canvas.create_image(
                    ICON_DISPLAY_SIZE // 2,
                    ICON_DISPLAY_SIZE // 2,
                    image=self.display_icon_image,
                    anchor="center",
                )

    @staticmethod
    def _fit_image_to_display(image):
        if image is None:
            return None
        width_getter = getattr(image, "width", None)
        height_getter = getattr(image, "height", None)
        if not callable(width_getter) or not callable(height_getter):
            return image

        width = width_getter()
        height = height_getter()
        if width <= ICON_DISPLAY_SIZE and height <= ICON_DISPLAY_SIZE:
            return image

        factor = max(
            1,
            (width + ICON_DISPLAY_SIZE - 1) // ICON_DISPLAY_SIZE,
            (height + ICON_DISPLAY_SIZE - 1) // ICON_DISPLAY_SIZE,
        )
        subsample = getattr(image, "subsample", None)
        if callable(subsample):
            return subsample(factor, factor)
        return image

    def _quit_application(self, event=None):
        self.root.destroy()
        return "break"

    def _save_desktop_file(self):
        default_dir = os.path.join(os.path.expanduser(
            "~"), ".local", "share", "applications")
        os.makedirs(default_dir, exist_ok=True)
        output_path = self._ask_save_file(
            title="Choose location for .desktop file",
            defaultextension=".desktop",
            filetypes=[("Desktop Entry Files", "*.desktop"),
                       ("All Files", "*.*")],
            initialdir=default_dir,
            initialfile=f"{self._slugify(self._string_value('name', 'desktop-entry'))}.desktop",
        )

        if not output_path:
            return

        if not output_path.endswith(".desktop"):
            output_path += ".desktop"

        output_path_obj = Path(output_path)
        pending_icon_spec = getattr(self, "pending_generated_icon_spec", None)

        try:
            if pending_icon_spec:
                icon_path = output_path_obj.with_suffix(".png")
                self._write_generated_icon_png(pending_icon_spec, icon_path)
                self.variables["icon"].set(str(icon_path))
                self.pending_generated_icon_svg = None
                self.pending_generated_icon_spec = None

            content = self.generate_desktop_entry()
            validation_error = self._validate_desktop_entry_content(content)
            if validation_error:
                messagebox.showerror("Save failed", validation_error)
                return

            output_path_obj.write_text(content, encoding="utf-8")
            self.last_desktop_file = output_path
            self._refresh_desktop_database(output_path_obj.parent)
            self._prompt_to_add_application_directory(output_path_obj.parent)

            validator_result = self._run_desktop_file_validator(output_path_obj)
            if isinstance(validator_result, dict):
                has_errors = bool(validator_result.get("errors"))
                validator_output = (validator_result.get("output") or "").strip()
            else:
                # Backward compatibility for older tests/mocks returning string/None.
                has_errors = bool(validator_result)
                validator_output = (validator_result or "").strip()

            if has_errors:
                messagebox.showerror(
                    "Saved with validation errors",
                    f"Desktop entry saved to:\n{output_path}\n\n"
                    "desktop-file-validator reported:\n"
                    f"{validator_output or 'Unknown validation error.'}",
                )
            else:
                success_message = f"Desktop entry saved to:\n{output_path}"
                if validator_output:
                    success_message += (
                        "\n\ndesktop-file-validator warnings:\n"
                        f"{validator_output}"
                    )
                messagebox.showinfo(
                    "Saved", success_message)
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save file:\n{exc}")

    @staticmethod
    def _run_desktop_file_validator(path):
        try:
            result = subprocess.run(
                ["desktop-file-validator", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return {"errors": False, "output": None, "available": False}

        output = (result.stdout or "") + (result.stderr or "")
        return {
            "errors": result.returncode != 0,
            "output": output.strip() or None,
            "available": True,
        }

    @staticmethod
    def _hex_to_rgb(color_value):
        value = color_value.lstrip("#")
        if len(value) != 6:
            raise ValueError(f"Unsupported color value: {color_value}")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    def _write_generated_icon_png(self, spec, icon_path, size=512):
        start_rgb = self._hex_to_rgb(spec["bg1"])
        end_rgb = self._hex_to_rgb(spec["bg2"])

        image = Image.new("RGB", (size, size), start_rgb)
        pixels = image.load()
        for y in range(size):
            for x in range(size):
                blend = (x + y) / (2 * (size - 1))
                pixels[x, y] = tuple(
                    int(start_rgb[channel] * (1.0 - blend) +
                        end_rgb[channel] * blend)
                    for channel in range(3)
                )

        draw = ImageDraw.Draw(image)
        shape_color = spec["shape_color"]
        if spec["shape"] == "rounded_rect":
            draw.rounded_rectangle(
                (92, 92, 420, 420), radius=84, fill=shape_color)
        elif spec["shape"] == "circle":
            draw.ellipse((86, 86, 426, 426), fill=shape_color)
        else:
            draw.polygon(self._shape_points(
                spec["shape"], size), fill=shape_color)

        for line_spec in spec["lines"]:
            draw.line(
                (line_spec["x1"], line_spec["y1"],
                 line_spec["x2"], line_spec["y2"]),
                fill=spec["line_color"],
                width=line_spec["w"],
            )

        for circle_spec in spec["circles"]:
            cx = circle_spec["cx"]
            cy = circle_spec["cy"]
            radius = circle_spec["r"]
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline=spec["circle_color"],
                width=circle_spec["w"],
            )

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 190)
        except OSError:
            font = ImageFont.load_default()

        text = spec["chars"]
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = (size - text_width) // 2
        text_y = int(size * 0.57 - text_height / 2)
        draw.text((text_x, text_y), text, font=font, fill="#ffffff")

        image.save(icon_path, format="PNG")

    @staticmethod
    def _generated_icon_colors(seed_text):
        digest = hashlib.sha1(seed_text.encode("utf-8")).hexdigest()
        hue = int(digest[:8], 16) / 0xFFFFFFFF
        r1, g1, b1 = colorsys.hsv_to_rgb(hue, 0.55, 0.82)
        r2, g2, b2 = colorsys.hsv_to_rgb((hue + 0.12) % 1.0, 0.7, 0.95)
        return (
            f"#{int(r1 * 255):02x}{int(g1 * 255):02x}{int(b1 * 255):02x}",
            f"#{int(r2 * 255):02x}{int(g2 * 255):02x}{int(b2 * 255):02x}",
        )

    @staticmethod
    def _generated_icon_label(name):
        words = [token for token in re.split(r"\s+", name.strip()) if token]
        if len(words) >= 2:
            return f"{words[0][0]}{words[1][0]}".upper()
        if words and len(words[0]) >= 2:
            return words[0][:2].upper()
        if words:
            return words[0][:1].upper()
        return "AP"

    @staticmethod
    def _rgb_hex(red, green, blue):
        return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"

    def _generate_icon_specs(self, app_name, count=8):
        words = [token for token in re.split(
            r"\s+", app_name.strip()) if token]
        letters = "".join(ch for ch in app_name.upper()
                          if ch.isalpha()) or "APP"

        label_pool = []
        if len(words) >= 2:
            label_pool.append((words[0][0] + words[1][0]).upper())
        if len(words) >= 3:
            label_pool.append(
                (words[0][0] + words[1][0] + words[2][0]).upper())
        if len(letters) >= 3:
            label_pool.extend([letters[:1], letters[:2], letters[:3]])
        elif len(letters) == 2:
            label_pool.extend([letters[:1], letters[:2]])
        else:
            label_pool.append(letters[:1])
        label_pool = [value for value in label_pool if value]
        if not label_pool:
            label_pool = ["A", "AP", "APP"]

        rng = random.SystemRandom()
        shape_choices = ["rounded_rect", "circle", "diamond", "hexagon"]
        specs = []
        for _ in range(count):
            hue = rng.random()
            bg1 = self._rgb_hex(*colorsys.hsv_to_rgb(hue, 0.55, 0.88))
            bg2 = self._rgb_hex(
                *colorsys.hsv_to_rgb((hue + 0.18) % 1.0, 0.70, 0.98))
            shape_color = self._rgb_hex(
                *colorsys.hsv_to_rgb((hue + 0.50) % 1.0, 0.45, 0.30))
            line_color = self._rgb_hex(
                *colorsys.hsv_to_rgb((hue + 0.33) % 1.0, 0.75, 0.94))
            circle_color = self._rgb_hex(
                *colorsys.hsv_to_rgb((hue + 0.66) % 1.0, 0.50, 0.98))

            lines = []
            for _ in range(rng.randint(3, 6)):
                lines.append({
                    "x1": rng.randint(50, 460),
                    "y1": rng.randint(50, 460),
                    "x2": rng.randint(50, 460),
                    "y2": rng.randint(50, 460),
                    "w": rng.randint(4, 12),
                })

            circles = []
            for _ in range(rng.randint(2, 5)):
                circles.append({
                    "cx": rng.randint(70, 440),
                    "cy": rng.randint(70, 440),
                    "r": rng.randint(16, 62),
                    "w": rng.randint(2, 7),
                })

            specs.append({
                "bg1": bg1,
                "bg2": bg2,
                "shape": rng.choice(shape_choices),
                "shape_color": shape_color,
                "line_color": line_color,
                "circle_color": circle_color,
                "lines": lines,
                "circles": circles,
                "chars": rng.choice(label_pool),
            })

        return specs

    @staticmethod
    def _shape_points(shape_name, size):
        if shape_name == "diamond":
            return [
                (size * 0.5, size * 0.18),
                (size * 0.82, size * 0.5),
                (size * 0.5, size * 0.82),
                (size * 0.18, size * 0.5),
            ]
        if shape_name == "hexagon":
            return [
                (size * 0.25, size * 0.2),
                (size * 0.75, size * 0.2),
                (size * 0.9, size * 0.5),
                (size * 0.75, size * 0.8),
                (size * 0.25, size * 0.8),
                (size * 0.1, size * 0.5),
            ]
        return []

    def _draw_icon_preview(self, canvas, spec, size):
        canvas.delete("all")
        canvas.create_rectangle(0, 0, size, size, fill=spec["bg1"], outline="")

        shape = spec["shape"]
        if shape == "rounded_rect":
            canvas.create_rectangle(size * 0.18, size * 0.18, size * 0.82, size * 0.82,
                                    fill=spec["shape_color"], outline="")
        elif shape == "circle":
            canvas.create_oval(size * 0.2, size * 0.2, size * 0.8, size * 0.8,
                               fill=spec["shape_color"], outline="")
        else:
            points = self._shape_points(shape, size)
            flat_points = [coord for point in points for coord in point]
            canvas.create_polygon(
                *flat_points, fill=spec["shape_color"], outline="")

        for line_spec in spec["lines"]:
            scale = size / 512.0
            canvas.create_line(
                line_spec["x1"] * scale,
                line_spec["y1"] * scale,
                line_spec["x2"] * scale,
                line_spec["y2"] * scale,
                fill=spec["line_color"],
                width=max(1, int(line_spec["w"] * scale)),
            )

        for circle_spec in spec["circles"]:
            scale = size / 512.0
            cx = circle_spec["cx"] * scale
            cy = circle_spec["cy"] * scale
            r = circle_spec["r"] * scale
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                               outline=spec["circle_color"], width=max(1, int(circle_spec["w"] * scale)))

        canvas.create_text(
            size * 0.5,
            size * 0.56,
            text=spec["chars"],
            fill="#ffffff",
            font=("Sans", max(16, int(size * 0.26)), "bold"),
        )

    def _build_generated_icon_svg(self, spec):
        initials = html.escape(spec["chars"])
        shape = spec["shape"]
        shape_fragment = ""
        if shape == "rounded_rect":
            shape_fragment = (
                "  <rect x=\"92\" y=\"92\" width=\"328\" height=\"328\" rx=\"84\" "
                f"fill=\"{spec['shape_color']}\"/>\n"
            )
        elif shape == "circle":
            shape_fragment = (
                f"  <circle cx=\"256\" cy=\"256\" r=\"170\" fill=\"{spec['shape_color']}\"/>\n"
            )
        else:
            points = self._shape_points(shape, 512)
            points_str = " ".join(f"{int(x)},{int(y)}" for x, y in points)
            shape_fragment = (
                f"  <polygon points=\"{points_str}\" fill=\"{spec['shape_color']}\"/>\n"
            )

        line_fragments = []
        for line_spec in spec["lines"]:
            line_fragments.append(
                "  <line"
                f" x1=\"{line_spec['x1']}\" y1=\"{line_spec['y1']}\""
                f" x2=\"{line_spec['x2']}\" y2=\"{line_spec['y2']}\""
                f" stroke=\"{spec['line_color']}\" stroke-width=\"{line_spec['w']}\""
                " stroke-linecap=\"round\" opacity=\"0.65\"/>\n"
            )

        circle_fragments = []
        for circle_spec in spec["circles"]:
            circle_fragments.append(
                "  <circle"
                f" cx=\"{circle_spec['cx']}\" cy=\"{circle_spec['cy']}\" r=\"{circle_spec['r']}\""
                f" stroke=\"{spec['circle_color']}\" stroke-width=\"{circle_spec['w']}\""
                " fill=\"none\" opacity=\"0.72\"/>\n"
            )

        return (
            "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\" viewBox=\"0 0 512 512\">\n"
            "  <defs>\n"
            "    <linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">\n"
            f"      <stop offset=\"0%\" stop-color=\"{spec['bg1']}\"/>\n"
            f"      <stop offset=\"100%\" stop-color=\"{spec['bg2']}\"/>\n"
            "    </linearGradient>\n"
            "  </defs>\n"
            "  <rect width=\"512\" height=\"512\" rx=\"96\" fill=\"url(#bg)\"/>\n"
            f"{shape_fragment}"
            f"{''.join(line_fragments)}"
            f"{''.join(circle_fragments)}"
            "  <text x=\"50%\" y=\"57%\" text-anchor=\"middle\" font-size=\"190\""
            " font-family=\"Sans\" font-weight=\"700\" fill=\"#ffffff\">"
            f"{initials}</text>\n"
            "</svg>\n"
        )

    def _show_icon_picker_dialog(self, app_name):

        dialog = tk.Toplevel(self.root)
        dialog.title("Choose a generated icon")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        selection = {"spec": None}

        def choose(spec):
            selection["spec"] = spec
            dialog.destroy()

        container = ttk.Frame(dialog, padding=10)
        container.grid(row=0, column=0, sticky="nsew")

        slots = []
        for index in range(8):
            row = index // 4
            column = index % 4

            tile = ttk.Frame(container, padding=6)
            tile.grid(row=row, column=column, padx=6, pady=6)

            canvas = tk.Canvas(tile, width=120, height=120,
                               highlightthickness=1, highlightbackground="#bdbdbd", background="#ffffff")
            canvas.grid(row=0, column=0, padx=2, pady=(0, 6))

            button = ttk.Button(tile, text="Use")
            button.grid(row=1, column=0, sticky="ew")
            slots.append({"canvas": canvas, "button": button})

        current_specs = []

        def apply_specs(new_specs):
            current_specs.clear()
            current_specs.extend(new_specs[:8])

            for idx, slot in enumerate(slots):
                canvas = slot["canvas"]
                button = slot["button"]
                if idx >= len(current_specs):
                    canvas.delete("all")
                    button.state(["disabled"])
                    button.configure(command=lambda: None)
                    canvas.bind("<Button-1>", lambda _event: None)
                    continue

                spec = current_specs[idx]
                self._draw_icon_preview(canvas, spec, 120)
                button.state(["!disabled"])
                button.configure(
                    command=lambda selected=spec: choose(selected))
                canvas.bind("<Button-1>", lambda _event,
                            selected=spec: choose(selected))

        def regenerate():
            apply_specs(self._generate_icon_specs(app_name, count=8))

        regenerate()

        actions = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        actions.grid(row=1, column=0, sticky="ew")
        ttk.Button(actions, text="Regenerate 8",
                   command=regenerate).pack(side="left")
        ttk.Button(actions, text="Cancel",
                   command=dialog.destroy).pack(side="right")

        dialog.wait_window()
        return selection["spec"]

    def _select_generated_icon_svg(self, app_name):
        if hasattr(self, "root") and self.root is not None:
            chosen_spec = self._show_icon_picker_dialog(app_name)
        else:
            specs = self._generate_icon_specs(app_name, count=8)
            chosen_spec = specs[0] if specs else None

        if chosen_spec is None:
            return None
        self.pending_generated_icon_spec = chosen_spec
        return self._build_generated_icon_svg(chosen_spec)

    def _generate_icon_file(self):
        app_name = self._string_value("name", "Application") or "Application"
        icon_svg = self._select_generated_icon_svg(app_name)
        if not icon_svg:
            return
        self.pending_generated_icon_svg = icon_svg
        self._update_gui_icon_from_field()
        messagebox.showinfo(
            "Icon selected",
            "Generated icon selected. It will be saved next to the .desktop file when you save.",
        )

    @staticmethod
    def _validate_desktop_entry_content(content):
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines or lines[0] != "[Desktop Entry]":
            return "The desktop entry must start with a single [Desktop Entry] header."

        header_count = sum(1 for line in lines if line == "[Desktop Entry]")
        if header_count != 1:
            return "The desktop entry contains duplicate [Desktop Entry] headers."

        seen_keys = set()
        for line in lines[1:]:
            if line.startswith("[") and line.endswith("]"):
                return "The desktop entry contains an unexpected section header."
            if "=" not in line:
                continue
            key = line.split("=", 1)[0].strip().lower()
            if key in seen_keys:
                return f"The desktop entry contains a duplicate key: {key}."
            seen_keys.add(key)

        return None

    def _refresh_desktop_database(self, directory):
        try:
            subprocess.run(
                ["update-desktop-database", str(directory)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    def _prompt_to_add_application_directory(self, directory):
        directory = Path(directory).resolve()
        if self._is_standard_application_directory(directory):
            return

        prompt = (
            f"The launcher was saved in:\n{directory}\n\n"
            "That folder is not one of the standard application locations. "
            "Add this path to your desktop application's launcher list so the "
            "entry appears in menus and searches?"
        )
        if messagebox.askyesno("Add folder to application list?", prompt):
            messagebox.showinfo(
                "Add this folder to the application list",
                f"Add this path to your desktop application's application list:\n{directory}",
            )

    @staticmethod
    def _is_standard_application_directory(directory):
        standard_directories = {
            Path(os.path.expanduser("~/.local/share/applications")).resolve(),
            Path("/usr/share/applications").resolve(),
            Path("/usr/local/share/applications").resolve(),
        }
        return Path(directory).resolve() in standard_directories

    def _load_desktop_file(self):
        input_path = self._ask_open_file(
            title="Choose existing .desktop file",
            filetypes=[("Desktop Entry Files", "*.desktop"),
                       ("All Files", "*.*")],
            initialdir=os.path.join(os.path.expanduser(
                "~"), ".local", "share", "applications"),
        )

        if not input_path:
            return

        try:
            text = Path(input_path).read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Load failed", f"Could not open file:\n{exc}")
            return

        self._updating_preview = True
        try:
            self._apply_desktop_entry_text(text)
            self.last_desktop_file = input_path
            self.pending_generated_icon_svg = None
            self.pending_generated_icon_spec = None
        finally:
            self._updating_preview = False
        self._refresh_preview()

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-") or "desktop-entry"


def main():
    root = tk.Tk()
    app = DesktopEntryCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
