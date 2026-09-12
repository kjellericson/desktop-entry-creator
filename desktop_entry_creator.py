#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk


class DesktopEntryCreatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("desktop-entry-creator")
        self.root.geometry("980x760")
        self.root.minsize(900, 700)

        self.variables = {}
        self.tooltip = None
        self._updating_preview = False
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
        self._seed_example()
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
        if kind == "directory":
            value = filedialog.askdirectory(title="Select directory")
        elif kind == "icon":
            value = filedialog.askopenfilename(
                title="Select icon file",
                filetypes=[
                    ("Image Files", "*.png *.jpg *.jpeg *.gif *.svg *.xpm *.ico"),
                    ("All Files", "*.*"),
                ],
            )
        else:
            value = filedialog.askopenfilename(
                title="Select file",
                filetypes=[("All Files", "*.*")],
            )

        if value:
            var.set(value)

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

        preview_label = ttk.Label(
            actions_frame, text="Generated desktop entry")
        preview_label.grid(row=0, column=0, sticky="w", padx=10, pady=(0, 6))

        self.preview = tk.Text(actions_frame, wrap="word",
                               height=28, font=("Monospace", 10))
        self.preview.grid(row=1, column=0, sticky="nsew",
                          padx=(10, 10), pady=(0, 10))

        buttons = ttk.Frame(actions_frame)
        buttons.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ttk.Button(buttons, text="Save .desktop", command=self._save_desktop_file).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(buttons, text="Reset", command=self._reset_form).grid(
            row=0, column=1, sticky="ew", padx=(5, 0))

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
            ("working_dir", "WorkingDirectory"),
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
            "TryExec": "try_exec",
            "StartupWMClass": "startup_wm_class",
            "MimeType": "mime_type",
            "Categories": "categories",
            "Keywords": "keywords",
            "Version": "version",
            "Terminal": "terminal",
            "StartupNotify": "startup_notify",
        }

        for line in text.splitlines():
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                self.unknown_lines.append(line)
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "Type":
                self.type_var.set(value)
                continue
            if key in remap:
                entries[key] = value
            else:
                self.unknown_lines.append(line)

        for key, mapped_key in remap.items():
            if key not in entries:
                continue
            value = entries[key]
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

    def _save_desktop_file(self):
        content = self.generate_desktop_entry()
        default_dir = os.path.join(os.path.expanduser(
            "~"), ".local", "share", "applications")
        os.makedirs(default_dir, exist_ok=True)
        output_path = filedialog.asksaveasfilename(
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

        try:
            Path(output_path).write_text(content, encoding="utf-8")
            messagebox.showinfo(
                "Saved", f"Desktop entry saved to:\n{output_path}")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save file:\n{exc}")

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
