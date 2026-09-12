import unittest

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
        self.assertIn("WorkingDirectory=/tmp/work", result)
        self.assertIn("Terminal=false", result)
        self.assertIn("StartupNotify=true", result)
        self.assertEqual(result.count("Path="), 1)

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
            """[Desktop Entry]\nVersion=2.0\nType=Link\nName=My New App\nExec=/usr/bin/myapp\nIcon=myapp\nPath=/opt/myapp\nWorkingDirectory=/var/lib/myapp\nTerminal=true\nStartupNotify=false\n""")

        self.assertEqual(app.variables["name"].get(), "My New App")
        self.assertEqual(app.variables["exec"].get(), "/usr/bin/myapp")
        self.assertEqual(app.variables["path"].get(), "/opt/myapp")
        self.assertEqual(app.variables["working_dir"].get(), "/var/lib/myapp")
        self.assertEqual(app.type_var.get(), "Link")
        self.assertEqual(app.variables["terminal"].get(), True)
        self.assertEqual(app.variables["startup_notify"].get(), False)

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


if __name__ == "__main__":
    unittest.main()
