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


if __name__ == "__main__":
    unittest.main()
