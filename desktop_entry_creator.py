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
        self._build_ui()
        self._seed_example()
        self._refresh_preview()

    def _add_field(self, parent, row, label, key, default="", width=36):
        label_widget = ttk.Label(parent, text=f"{label}:")
        label_widget.grid(row=row, column=0, sticky="w",
                          padx=(10, 8), pady=(8, 4))

        var = tk.StringVar(value=default)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=(8, 4))

        self.variables[key] = var
        return var

    def _add_checkbox(self, parent, row, label, key, default=False):
        var = tk.BooleanVar(value=default)
        checkbox = ttk.Checkbutton(parent, text=label, variable=var)
        checkbox.grid(row=row, column=1, sticky="w", padx=(0, 10), pady=(8, 4))
        self.variables[key] = var
        return var

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        main.columnconfigure(1, weight=1)

        form = ttk.LabelFrame(main, text="Launcher details", padding=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))
        form.columnconfigure(1, weight=1)

        self._add_field(form, 0, "Name", "name", "My App")
        self._add_field(form, 1, "Generic Name", "generic_name", "Application")
        self._add_field(form, 2, "Comment", "comment",
                        "Launch the application")
        self._add_field(form, 3, "Exec", "exec",
                        "/usr/bin/firefox --new-window")
        self._add_field(form, 4, "Icon", "icon",
                        "/usr/share/icons/hicolor/256x256/apps/firefox.png")
        self._add_field(form, 5, "Path", "path", "/home/your-user")
        self._add_field(form, 6, "Working Directory",
                        "working_dir", os.getcwd())
        self._add_field(form, 7, "Categories", "categories",
                        "Utility;Development;")
        self._add_field(form, 8, "Keywords", "keywords", "app;desktop;utility")
        self._add_field(form, 9, "Startup WM Class", "startup_wm_class", "")
        self._add_field(form, 10, "Mime Type", "mime_type", "")
        self._add_field(form, 11, "Try Exec", "try_exec", "")
        self._add_field(form, 12, "Version", "version", "1.0")
        self._add_checkbox(form, 13, "Run in terminal", "terminal", False)
        self._add_checkbox(form, 14, "Startup Notify", "startup_notify", True)

        dropdown_frame = ttk.Frame(form)
        dropdown_frame.grid(row=15, column=1, sticky="ew",
                            padx=(0, 10), pady=(8, 4))
        ttk.Label(form, text="Type:").grid(row=15, column=0,
                                           sticky="w", padx=(10, 8), pady=(8, 4))
        self.type_var = tk.StringVar(value="Application")
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
        buttons.columnconfigure(2, weight=1)

        ttk.Button(buttons, text="Generate", command=self._refresh_preview).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(buttons, text="Save .desktop", command=self._save_desktop_file).grid(
            row=0, column=1, sticky="ew", padx=5)
        ttk.Button(buttons, text="Reset", command=self._reset_form).grid(
            row=0, column=2, sticky="ew", padx=(5, 0))

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

        return "\n".join(lines) + "\n"

    def _refresh_preview(self):
        content = self.generate_desktop_entry()
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", content)

    def _save_desktop_file(self):
        content = self.generate_desktop_entry()
        output_path = filedialog.asksaveasfilename(
            title="Choose location for .desktop file",
            defaultextension=".desktop",
            filetypes=[("Desktop Entry Files", "*.desktop"),
                       ("All Files", "*.*")],
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
