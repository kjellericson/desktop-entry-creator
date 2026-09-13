import unittest
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import tkinter as tk

from desktop_entry_creator import DesktopEntryCreatorApp


class DesktopEntryCreatorTests(unittest.TestCase):
    def test_generates_expected_key_fields(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": type("Var", (), {"get": lambda self: "Demo App"})(),
            "generic_name": type("Var", (), {"get": lambda self: "Editor"})(),
            "comment": type("Var", (), {"get": lambda self: "Demo application"})(),
            "exec": type("Var", (), {"get": lambda self: "/usr/bin/true"})(),
            "icon": type("Var", (), {"get": lambda self: "demo-icon"})(),
            "path": type("Var", (), {"get": lambda self: "/tmp/demo"})(),
            "working_dir": type("Var", (), {"get": lambda self: "/tmp/work"})(),
            "try_exec": type("Var", (), {"get": lambda self: "/usr/bin/true"})(),
            "startup_wm_class": type("Var", (), {"get": lambda self: "Demo"})(),
            "mime_type": type("Var", (), {"get": lambda self: "text/plain"})(),
            "categories": type("Var", (), {"get": lambda self: "Utility;TextEditor;"})(),
            "keywords": type("Var", (), {"get": lambda self: "app;demo"})(),
            "terminal": type("Var", (), {"get": lambda self: False})(),
            "startup_notify": type("Var", (), {"get": lambda self: True})(),
            "version": type("Var", (), {"get": lambda self: "1.2"})(),
        }
        app.type_var = type("Var", (), {"get": lambda self: "Application"})()
        app.preview = None

        result = app.generate_desktop_entry()

        self.assertIn("[Desktop Entry]", result)
        self.assertIn("Name=Demo App", result)
        self.assertIn("Type=Application", result)
        self.assertIn("Path=/tmp/demo", result)
        self.assertIn("X-WorkingDirectory=/tmp/work", result)
        self.assertIn("Terminal=false", result)
        self.assertIn("StartupNotify=true", result)
        self.assertEqual(result.count("Path="), 1)

    def test_cli_argument_populates_exec_and_name(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var(),
            "exec": Var(),
        }

        app._apply_command_line_argument("/tmp/demo-app")

        self.assertEqual(app.variables["exec"].get(), "/tmp/demo-app")
        self.assertEqual(app.variables["name"].get(), "demo-app")

    def test_applies_desktop_content_to_form_fields(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var(),
            "generic_name": Var(),
            "comment": Var(),
            "exec": Var(),
            "icon": Var(),
            "path": Var(),
            "working_dir": Var(),
            "try_exec": Var(),
            "startup_wm_class": Var(),
            "mime_type": Var(),
            "categories": Var(),
            "keywords": Var(),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var(),
        }
        app.type_var = Var("Application")
        app._apply_desktop_entry_text(
            """[Desktop Entry]\nVersion=2.0\nType=Link\nName=My New App\nExec=/usr/bin/myapp\nIcon=myapp\nPath=/opt/myapp\nX-WorkingDirectory=/var/lib/myapp\nTerminal=true\nStartupNotify=false\n""")

        self.assertEqual(app.variables["name"].get(), "My New App")
        self.assertEqual(app.variables["exec"].get(), "/usr/bin/myapp")
        self.assertEqual(app.variables["path"].get(), "/opt/myapp")
        self.assertEqual(app.variables["working_dir"].get(), "/var/lib/myapp")
        self.assertEqual(app.type_var.get(), "Link")
        self.assertEqual(app.variables["terminal"].get(), True)
        self.assertEqual(app.variables["startup_notify"].get(), False)

    def test_loads_x_working_directory_from_desktop_file(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var(),
            "generic_name": Var(),
            "comment": Var(),
            "exec": Var(),
            "icon": Var(),
            "path": Var(),
            "working_dir": Var(),
            "try_exec": Var(),
            "startup_wm_class": Var(),
            "mime_type": Var(),
            "categories": Var(),
            "keywords": Var(),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var(),
        }
        app.type_var = Var("Application")

        app._apply_desktop_entry_text(
            """[Desktop Entry]\nVersion=1.0\nType=Application\nX-WorkingDirectory=/var/lib/example\n""")

        self.assertEqual(
            app.variables["working_dir"].get(), "/var/lib/example")

    def test_preview_edit_does_not_refresh_preview(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        class FakePreview:
            def __init__(self, text):
                self.text = text
                self.delete_calls = 0
                self.insert_calls = 0

            def get(self, *args):
                return self.text

            def delete(self, *args):
                self.delete_calls += 1

            def insert(self, *args):
                self.insert_calls += 1

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app._updating_preview = False
        app.variables = {
            "name": Var(),
            "generic_name": Var(),
            "comment": Var(),
            "exec": Var(),
            "icon": Var(),
            "path": Var(),
            "working_dir": Var(),
            "try_exec": Var(),
            "startup_wm_class": Var(),
            "mime_type": Var(),
            "categories": Var(),
            "keywords": Var(),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var(),
        }
        app.type_var = Var("Application")
        app.preview = FakePreview(
            "[Desktop Entry]\nType=Application\nName=My App\n")

        app._on_preview_edit()

        self.assertFalse(app._updating_preview)
        self.assertEqual(app.preview.delete_calls, 0)
        self.assertEqual(app.preview.insert_calls, 0)
        self.assertEqual(app.variables["name"].get(), "My App")

    def test_preserves_unknown_lines_in_generated_output(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": type("Var", (), {"get": lambda self: "Demo App"})(),
            "generic_name": type("Var", (), {"get": lambda self: "Editor"})(),
            "comment": type("Var", (), {"get": lambda self: "Demo application"})(),
            "exec": type("Var", (), {"get": lambda self: "/usr/bin/true"})(),
            "icon": type("Var", (), {"get": lambda self: "demo-icon"})(),
            "path": type("Var", (), {"get": lambda self: "/tmp/demo"})(),
            "working_dir": type("Var", (), {"get": lambda self: "/tmp/work"})(),
            "try_exec": type("Var", (), {"get": lambda self: "/usr/bin/true"})(),
            "startup_wm_class": type("Var", (), {"get": lambda self: "Demo"})(),
            "mime_type": type("Var", (), {"get": lambda self: "text/plain"})(),
            "categories": type("Var", (), {"get": lambda self: "Utility;TextEditor;"})(),
            "keywords": type("Var", (), {"get": lambda self: "app;demo"})(),
            "terminal": type("Var", (), {"get": lambda self: False})(),
            "startup_notify": type("Var", (), {"get": lambda self: True})(),
            "version": type("Var", (), {"get": lambda self: "1.2"})(),
        }
        app.type_var = type("Var", (), {"get": lambda self: "Application"})()
        app.unknown_lines = ["X-Custom-Flag=true",
                             "X-GNOME-FullName=My Demo App"]

        result = app.generate_desktop_entry()

        self.assertIn("X-Custom-Flag=true", result)
        self.assertIn("X-GNOME-FullName=My Demo App", result)

    def test_loads_existing_desktop_file_into_form(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var(),
            "generic_name": Var(),
            "comment": Var(),
            "exec": Var(),
            "icon": Var(),
            "path": Var(),
            "working_dir": Var(),
            "try_exec": Var(),
            "startup_wm_class": Var(),
            "mime_type": Var(),
            "categories": Var(),
            "keywords": Var(),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var(),
        }
        app.type_var = Var("Application")
        app._updating_preview = False
        app.preview = type("Preview", (), {
            "delete": lambda self, *args: None,
            "insert": lambda self, *args: None,
        })()

        with TemporaryDirectory() as temp_dir:
            desktop_path = Path(temp_dir) / "sample.desktop"
            desktop_path.write_text(
                """[Desktop Entry]\nVersion=3.1\nType=Link\nName=Loaded App\nExec=/usr/bin/example\nIcon=example-icon\nTerminal=true\nStartupNotify=false\n""",
                encoding="utf-8",
            )

            with patch.object(DesktopEntryCreatorApp, "_ask_open_file", return_value=str(desktop_path)), \
                    patch("desktop_entry_creator.messagebox.showinfo"), \
                    patch("desktop_entry_creator.messagebox.showerror"), \
                    patch.object(DesktopEntryCreatorApp, "_refresh_preview"):
                app._load_desktop_file()

        self.assertEqual(app.type_var.get(), "Link")
        self.assertEqual(app.variables["name"].get(), "Loaded App")
        self.assertEqual(app.variables["exec"].get(), "/usr/bin/example")
        self.assertEqual(app.variables["icon"].get(), "example-icon")
        self.assertTrue(app.variables["terminal"].get())
        self.assertFalse(app.variables["startup_notify"].get())

    def test_loads_lowercase_keys_without_round_trip_duplicates(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var(),
            "generic_name": Var(),
            "comment": Var(),
            "exec": Var(),
            "icon": Var(),
            "path": Var(),
            "working_dir": Var(),
            "try_exec": Var(),
            "startup_wm_class": Var(),
            "mime_type": Var(),
            "categories": Var(),
            "keywords": Var(),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var(),
        }
        app.type_var = Var("Application")
        app._updating_preview = False
        app.preview = type("Preview", (), {
            "delete": lambda self, *args: None,
            "insert": lambda self, *args: None,
        })()

        app._apply_desktop_entry_text(
            """[Desktop Entry]\nversion=4.0\ntype=application\nname=Lowercase App\nexec=/usr/bin/example\nterminal=true\nstartupnotify=false\nX-Custom=first\nx-custom=second\n""")

        result = app.generate_desktop_entry()

        self.assertEqual(app.type_var.get(), "application")
        self.assertEqual(app.variables["name"].get(), "Lowercase App")
        self.assertIn("Name=Lowercase App", result)
        self.assertEqual(result.count("Name="), 1)
        self.assertEqual(result.count("x-custom=second"), 1)
        self.assertNotIn("X-Custom=first", result)
        self.assertNotIn("x-custom=first", result)

    def test_ignores_section_header_when_loading_desktop_file(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var(),
            "generic_name": Var(),
            "comment": Var(),
            "exec": Var(),
            "icon": Var(),
            "path": Var(),
            "working_dir": Var(),
            "try_exec": Var(),
            "startup_wm_class": Var(),
            "mime_type": Var(),
            "categories": Var(),
            "keywords": Var(),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var(),
        }
        app.type_var = Var("Application")

        app._apply_desktop_entry_text(
            """[Desktop Entry]\nVersion=1.0\nType=Application\nName=Header Test\n""")

        self.assertEqual(app.unknown_lines, [])
        self.assertEqual(
            app.generate_desktop_entry().count("[Desktop Entry]"), 1)

    def test_validates_duplicate_headers_before_save(self):
        validation_error = DesktopEntryCreatorApp._validate_desktop_entry_content(
            """[Desktop Entry]\nVersion=1.0\n[Desktop Entry]\nName=Demo\n""")

        self.assertEqual(
            validation_error,
            "The desktop entry contains duplicate [Desktop Entry] headers.",
        )

    def test_validates_duplicate_keys_before_save(self):
        validation_error = DesktopEntryCreatorApp._validate_desktop_entry_content(
            """[Desktop Entry]\nVersion=1.0\nName=Demo\nname=Duplicate\n""")

        self.assertEqual(
            validation_error,
            "The desktop entry contains a duplicate key: name.",
        )

    def test_saves_and_refreshes_desktop_database(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var("Saved App"),
            "generic_name": Var("Tool"),
            "comment": Var("Save test"),
            "exec": Var("/usr/bin/example"),
            "icon": Var("example-icon"),
            "path": Var("/tmp"),
            "working_dir": Var("/tmp"),
            "try_exec": Var(""),
            "startup_wm_class": Var(""),
            "mime_type": Var(""),
            "categories": Var("Utility;"),
            "keywords": Var("save;test"),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var("1.0"),
        }
        app.type_var = Var("Application")
        app.pending_generated_icon_svg = None

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "saved.desktop"
            with patch.object(DesktopEntryCreatorApp, "_ask_save_file", return_value=str(output_path)), \
                    patch("desktop_entry_creator.messagebox.showinfo"), \
                    patch("desktop_entry_creator.messagebox.showerror"), \
                    patch("desktop_entry_creator.messagebox.askyesno", return_value=False), \
                    patch.object(DesktopEntryCreatorApp, "_refresh_desktop_database") as refresh_database:
                app._save_desktop_file()

            self.assertTrue(output_path.exists())
            self.assertEqual(app.last_desktop_file, str(output_path))
            refresh_database.assert_called_once_with(Path(temp_dir))

    def test_reset_form_defaults_type_to_application(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
            app.variables = {
                "name": tk.StringVar(master=root, value="App Name"),
                "terminal": tk.BooleanVar(master=root, value=True),
            }
            app.type_var = tk.StringVar(master=root, value="Link")
            app.pending_generated_icon_svg = "<svg/>"
            app.pending_generated_icon_spec = {"chars": "A"}

            with patch.object(DesktopEntryCreatorApp, "_refresh_preview"):
                app._reset_form()

            self.assertEqual(app.type_var.get(), "Application")
            self.assertEqual(app.variables["name"].get(), "")
            self.assertFalse(app.variables["terminal"].get())
            self.assertIsNone(app.pending_generated_icon_svg)
            self.assertIsNone(app.pending_generated_icon_spec)
        finally:
            root.destroy()

    def test_reports_validator_errors_after_save(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var("Validated App"),
            "generic_name": Var("Tool"),
            "comment": Var("Save test"),
            "exec": Var("/usr/bin/example"),
            "icon": Var("example-icon"),
            "path": Var("/tmp"),
            "working_dir": Var("/tmp"),
            "try_exec": Var(""),
            "startup_wm_class": Var(""),
            "mime_type": Var(""),
            "categories": Var("Utility;"),
            "keywords": Var("save;test"),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var("1.0"),
        }
        app.type_var = Var("Application")
        app.pending_generated_icon_svg = None
        app.pending_generated_icon_spec = None

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "validated.desktop"
            with patch.object(DesktopEntryCreatorApp, "_ask_save_file", return_value=str(output_path)), \
                    patch("desktop_entry_creator.messagebox.showinfo") as showinfo, \
                    patch("desktop_entry_creator.messagebox.showerror") as showerror, \
                    patch("desktop_entry_creator.messagebox.askyesno", return_value=False), \
                    patch.object(DesktopEntryCreatorApp, "_refresh_desktop_database"), \
                    patch.object(DesktopEntryCreatorApp, "_run_desktop_file_validator", return_value={
                        "errors": True,
                        "output": "invalid key",
                        "available": True,
                    }):
                app._save_desktop_file()

            self.assertTrue(output_path.exists())
            showinfo.assert_not_called()
            showerror.assert_called_once()
            self.assertIn("desktop-file-validator reported",
                          showerror.call_args[0][1])

    def test_run_desktop_file_validator_returns_error_output(self):
        completed = subprocess.CompletedProcess(
            args=["desktop-file-validator", "sample.desktop"],
            returncode=1,
            stdout="sample.desktop: error: value missing\n",
            stderr="",
        )

        with patch("desktop_entry_creator.subprocess.run", return_value=completed):
            result = DesktopEntryCreatorApp._run_desktop_file_validator(
                Path("sample.desktop"))

        self.assertEqual(
            result,
            {
                "errors": True,
                "output": "sample.desktop: error: value missing",
                "available": True,
            },
        )

    def test_run_desktop_file_validator_returns_none_when_tool_missing(self):
        with patch("desktop_entry_creator.subprocess.run", side_effect=FileNotFoundError):
            result = DesktopEntryCreatorApp._run_desktop_file_validator(
                Path("sample.desktop"))

        self.assertEqual(
            result,
            {
                "errors": False,
                "output": None,
                "available": False,
            },
        )

    def test_shows_validator_warnings_in_success_dialog(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var("Warned App"),
            "generic_name": Var("Tool"),
            "comment": Var("Save test"),
            "exec": Var("/usr/bin/example"),
            "icon": Var("example-icon"),
            "path": Var("/tmp"),
            "working_dir": Var("/tmp"),
            "try_exec": Var(""),
            "startup_wm_class": Var(""),
            "mime_type": Var(""),
            "categories": Var("Utility;"),
            "keywords": Var("save;test"),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var("1.0"),
        }
        app.type_var = Var("Application")
        app.pending_generated_icon_svg = None
        app.pending_generated_icon_spec = None

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "warned.desktop"
            with patch.object(DesktopEntryCreatorApp, "_ask_save_file", return_value=str(output_path)), \
                    patch("desktop_entry_creator.messagebox.showinfo") as showinfo, \
                    patch("desktop_entry_creator.messagebox.showerror") as showerror, \
                    patch("desktop_entry_creator.messagebox.askyesno", return_value=False), \
                    patch.object(DesktopEntryCreatorApp, "_refresh_desktop_database"), \
                    patch.object(DesktopEntryCreatorApp, "_run_desktop_file_validator", return_value={
                        "errors": False,
                        "output": "warn: recommended key missing",
                        "available": True,
                    }):
                app._save_desktop_file()

            showerror.assert_not_called()
            showinfo.assert_called_once()
            self.assertIn("desktop-file-validator warnings",
                          showinfo.call_args[0][1])
            self.assertIn("warn: recommended key missing",
                          showinfo.call_args[0][1])

    def test_generate_icons_sets_pending_svg_without_writing_file(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var("My Demo App"),
            "icon": Var(""),
        }
        app.pending_generated_icon_svg = None
        app.root = None

        with TemporaryDirectory() as temp_dir:
            desktop_path = Path(temp_dir) / "my-demo.desktop"
            with patch.object(DesktopEntryCreatorApp, "_select_generated_icon_svg", return_value="<svg>MD</svg>"), \
                    patch("desktop_entry_creator.messagebox.showinfo") as showinfo, \
                    patch("desktop_entry_creator.messagebox.showerror") as showerror:
                app._generate_icon_file()

            icon_path = desktop_path.with_suffix(".svg")
            self.assertEqual(app.pending_generated_icon_svg, "<svg>MD</svg>")
            self.assertEqual(app.variables["icon"].get(), "")
            self.assertFalse(icon_path.exists())
            showerror.assert_not_called()
            showinfo.assert_called_once()

    def test_save_desktop_writes_pending_icon_next_to_desktop_file(self):
        class Var:
            def __init__(self, value=""):
                self._value = value

            def set(self, value):
                self._value = value

            def get(self):
                return self._value

        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.variables = {
            "name": Var("Pending Icon App"),
            "generic_name": Var("Tool"),
            "comment": Var("Save test"),
            "exec": Var("/usr/bin/example"),
            "icon": Var(""),
            "path": Var("/tmp"),
            "working_dir": Var("/tmp"),
            "try_exec": Var(""),
            "startup_wm_class": Var(""),
            "mime_type": Var(""),
            "categories": Var("Utility;"),
            "keywords": Var("save;icon"),
            "terminal": Var(False),
            "startup_notify": Var(True),
            "version": Var("1.0"),
        }
        app.type_var = Var("Application")
        app.root = None
        expected_spec = {
            "bg1": "#101010",
            "bg2": "#202020",
            "shape": "diamond",
            "shape_color": "#333333",
            "line_color": "#444444",
            "circle_color": "#555555",
            "lines": [],
            "circles": [],
            "chars": "PI",
        }
        app.pending_generated_icon_spec = expected_spec
        app.pending_generated_icon_svg = "<svg><text>PI</text></svg>"

        with TemporaryDirectory() as temp_dir:
            desktop_path = Path(temp_dir) / "pending-icon.desktop"

            with patch.object(DesktopEntryCreatorApp, "_ask_save_file", return_value=str(desktop_path)), \
                    patch("desktop_entry_creator.messagebox.showinfo"), \
                    patch("desktop_entry_creator.messagebox.showerror"), \
                    patch("desktop_entry_creator.messagebox.askyesno", return_value=False), \
                    patch.object(DesktopEntryCreatorApp, "_write_generated_icon_png") as write_png, \
                    patch.object(DesktopEntryCreatorApp, "_refresh_desktop_database"):
                app._save_desktop_file()

            icon_path = desktop_path.with_suffix(".png")
            write_png.assert_called_once_with(expected_spec, icon_path)
            self.assertEqual(app.variables["icon"].get(), str(icon_path))
            self.assertIsNone(app.pending_generated_icon_svg)
            self.assertIsNone(app.pending_generated_icon_spec)

    def test_select_generated_icon_svg_returns_none_on_cancel(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.root = object()

        with patch.object(DesktopEntryCreatorApp, "_generate_icon_specs", return_value=[{"chars": "AA"}]), \
                patch.object(DesktopEntryCreatorApp, "_show_icon_picker_dialog", return_value=None):
            result = app._select_generated_icon_svg("App")

        self.assertIsNone(result)

    def test_select_generated_icon_svg_uses_first_spec_without_root(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)
        app.root = None
        spec = {
            "bg1": "#101010",
            "bg2": "#202020",
            "shape": "diamond",
            "shape_color": "#333333",
            "line_color": "#444444",
            "circle_color": "#555555",
            "lines": [],
            "circles": [],
            "chars": "AB",
        }

        with patch.object(DesktopEntryCreatorApp, "_generate_icon_specs", return_value=[spec]):
            result = app._select_generated_icon_svg("App")

        self.assertIn("<svg", result)
        self.assertIn(">AB<", result)

    def test_prompts_when_saved_outside_standard_application_directory(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)

        with TemporaryDirectory() as temp_dir:
            nonstandard_directory = Path(temp_dir) / "custom"
            with patch("desktop_entry_creator.messagebox.askyesno", return_value=True) as askyesno, \
                    patch("desktop_entry_creator.messagebox.showinfo") as showinfo:
                app._prompt_to_add_application_directory(nonstandard_directory)

        askyesno.assert_called_once()
        showinfo.assert_called_once()

    def test_does_not_prompt_for_standard_application_directory(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)

        with patch("desktop_entry_creator.messagebox.askyesno") as askyesno, \
                patch("desktop_entry_creator.messagebox.showinfo") as showinfo:
            app._prompt_to_add_application_directory(
                Path.home() / ".local/share/applications")

        askyesno.assert_not_called()
        showinfo.assert_not_called()

    def test_uses_icon_field_file_for_gui_icon_when_file_exists(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)

        class Var:
            def __init__(self, value=""):
                self._value = value

            def get(self):
                return self._value

        class FakeCanvas:
            def __init__(self):
                self.last_image = None
                self.deleted = False

            def delete(self, *_):
                self.deleted = True

            def create_image(self, _x, _y, image=None, anchor=None):
                self.last_image = image

        class FakeImage:
            def __init__(self, width=256, height=256):
                self._width = width
                self._height = height

            def width(self):
                return self._width

            def height(self):
                return self._height

            def subsample(self, x_factor, y_factor):
                return FakeImage(
                    max(1, self._width // max(1, x_factor)),
                    max(1, self._height // max(1, y_factor)),
                )

        app.variables = {"icon": Var("/tmp/icon.png")}
        app.pending_generated_icon_spec = None
        app.display_icon_image = None
        app.icon_canvas = FakeCanvas()

        with patch("desktop_entry_creator.Path.is_file", return_value=True), \
                patch("desktop_entry_creator.tk.PhotoImage", return_value=FakeImage()):
            app._update_gui_icon_from_field()

        self.assertLessEqual(app.display_icon_image.width(), 128)
        self.assertLessEqual(app.display_icon_image.height(), 128)
        self.assertTrue(app.icon_canvas.deleted)
        self.assertIs(app.icon_canvas.last_image, app.display_icon_image)

    def test_clears_preview_when_icon_field_path_missing(self):
        app = DesktopEntryCreatorApp.__new__(DesktopEntryCreatorApp)

        class Var:
            def __init__(self, value=""):
                self._value = value

            def get(self):
                return self._value

        class FakeCanvas:
            def __init__(self):
                self.last_image = None
                self.deleted = False

            def delete(self, *_):
                self.deleted = True

            def create_image(self, _x, _y, image=None, anchor=None):
                self.last_image = image

        app.variables = {"icon": Var("/tmp/missing.png")}
        app.pending_generated_icon_spec = None
        app.display_icon_image = None
        app.icon_canvas = FakeCanvas()

        with patch("desktop_entry_creator.Path.is_file", return_value=False), \
                patch("desktop_entry_creator.tk.PhotoImage") as photo_image:
            app._update_gui_icon_from_field()

        photo_image.assert_not_called()
        self.assertIsNone(app.display_icon_image)
        self.assertTrue(app.icon_canvas.deleted)
        self.assertIsNone(app.icon_canvas.last_image)


if __name__ == "__main__":
    unittest.main()
