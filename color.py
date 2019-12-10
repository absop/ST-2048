import os
import json
import sublime


class ColorSchemeManager():
    color_scheme = "Monokai.sublime-color-scheme"

    def __init__(self):
        self.settings = sublime.load_settings("Sublime2048.sublime-settings")
        self.preferences = sublime.load_settings(
            "Preferences.sublime-settings")
        self.settings.add_on_change("colors", self.build)
        self.preferences.add_on_change("color_scheme", self.rebuild)
        self.build()

    def cache_path(self):
        return os.path.join(sublime.packages_path(),
            "User", "Color Schemes", "Sublime2048")

    def clear(self):
        color_scheme_path = self.cache_path()
        for file in os.listdir(color_scheme_path):
            if file != self.color_scheme:
                try:
                    os.remove(os.path.join(color_scheme_path, file))
                except:
                    pass

    def rebuild(self):
        scheme = self.preferences.get("color_scheme", self.color_scheme)
        if scheme != self.color_scheme:
            self.color_scheme = scheme
            self.build()

    def build(self):
        styles = sublime.active_window().active_view().style()
        colors = self.settings.get("colors")
        foreground = colors["foreground"].pop("numbers")

        color_scheme_path = self.cache_path()
        color_scheme_name = os.path.basename(
            self.color_scheme).replace("tmTheme", "sublime-color-scheme")
        color_scheme_file = os.path.join(color_scheme_path, color_scheme_name)
        color_scheme_data = {
            "name": os.path.splitext(os.path.basename(self.color_scheme))[0],
            "author": "Sublime2048",
            "variables": {},
            "globals": {},
            "rules": [
                {
                    "scope": key + ".sublime2048",
                    "foreground": foreground,
                    "background": value
                }
                for key, value in colors["background"].items()
            ] + [
                {
                    "scope": key + ".sublime2048",
                    "foreground": value,
                }
                for key, value in colors["foreground"].items()
            ]
        }
        os.makedirs(color_scheme_path, exist_ok=True)
        with open(color_scheme_file, "w+") as file:
            file.write(json.dumps(color_scheme_data))


def plugin_loaded():
    ColorSchemeManager()
