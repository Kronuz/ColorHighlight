import os
import re
import sys
import json
import errno
import plistlib
import datetime

import sublime

from .colors import names_to_hex, xterm_to_hex

DEFAULT_COLOR_SCHEME = 'Monokai.sublime-color-scheme'

all_names_to_hex = dict(names_to_hex, **xterm_to_hex)


def log(s):
    # print("[Colorizer]", s)
    pass


if sys.version_info[0] == 3:
    if not hasattr(plistlib, 'loads'):
        plistlib.loads = lambda data: plistlib.readPlistFromBytes(data)
        plistlib.dumps = lambda value: plistlib.writePlistToBytes(value)
else:
    plistlib.loads = lambda data: plistlib.readPlistFromString(data)
    plistlib.dumps = lambda value: plistlib.writePlistToString(value)


def write_package(path, content):
    rf = sublime.packages_path() + path
    try:
        os.makedirs(os.path.dirname(rf))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    with open(rf, 'w') as f:
        f.write(content)


def read_package(path):
    rf = sublime.packages_path() + path
    if os.path.exists(rf):
        with open(rf, 'r') as f:
            res = f.read()
    else:
        rf = 'Packages' + path
        res = sublime.load_resource(rf)
    return res


class ColorScheme(object):
    backup_ext = ".chback"

    def __init__(self, settings):
        path = settings.get('color_scheme') or DEFAULT_COLOR_SCHEME
        if not path.startswith('Packages/'):
            path = 'Packages/Color Scheme - Default/' + path
        self.path = path[8:]
        self.time = datetime.datetime.now()

    def hash(self):
        if not hasattr(self, '_hash'):
            self._hash = hash(self.content())
        return self._hash

    def restore(self):
        # Remove "Packages" part from name
        if not os.path.exists(sublime.packages_path() + self.path + self.backup_ext):
            log("No backup :(")
            return False
        log("Starting restore scheme: " + self.path)
        write_package(self.path, read_package(self.path + self.backup_ext))
        log("Restore done.")
        return True

    def backup(self, content):
        if os.path.exists(sublime.packages_path() + self.path + self.backup_ext):
            log("Already backed up")
            return False
        write_package(self.path + self.backup_ext, content)  # backup
        log("Backup done")
        return True

    def content(self):
        if not hasattr(self, '_content'):
            # Remove "Packages" part from name
            content = read_package(self.path)
            self.backup(content)
            self._content = content
        return self._content


class SchemaColorizer(object):
    prefix = "col_"

    colors = {}
    color_scheme = None
    need_update = False

    def normalize(self, col):
        if col:
            col = all_names_to_hex.get(col.lower(), col.upper())
            if col.startswith('0X'):
                col = '#' + col[2:]
            try:
                if col[0] != '#':
                    raise ValueError
                if len(col) == 4:
                    col = '#' + col[1] * 2 + col[2] * 2 + col[3] * 2 + 'FF'
                elif len(col) == 5:
                    col = '#' + col[1] * 2 + col[2] * 2 + col[3] * 2 + col[4] * 2
                elif len(col) == 7:
                    col += 'FF'
                r = int(col[1:3], 16)
                g = int(col[3:5], 16)
                b = int(col[5:7], 16)
                a = int(col[7:9], 16) or 1  # alpha == 0 doesn't apply alpha in Sublime
                return '#%02X%02X%02X%02X' % (r, g, b, a)
            except Exception:
                log("Invalid color: %r" % col)

    def get_inv_col(self, bg_col, col):
        br = int(bg_col[1:3], 16)
        bg = int(bg_col[3:5], 16)
        bb = int(bg_col[5:7], 16)

        r = int(col[1:3], 16)
        g = int(col[3:5], 16)
        b = int(col[5:7], 16)
        a = int(col[7:9], 16) / 255.0

        r = br * (1 - a) + r * a
        g = bg * (1 - a) + g * a
        b = bb * (1 - a) + b * a

        # L = (max(r, g, b) + min(r, g, b)) / 2
        # Y709 = 0.2126 * r + 0.7152 * g + 0.0722 * b
        Y601 = ((r * 299) + (g * 587) + (b * 114)) / 1000

        v = Y601

        if v >= 128:
            v -= 128
        else:
            v += 128

        return '#%sFF' % (('%02X' % v) * 3)

    def region_name(self, s):
        return self.prefix + s[1:]

    def add_color(self, col):
        col = self.normalize(col)
        if not col:
            return
        if col not in self.colors:
            self.colors[col] = self.region_name(col)
            self.need_update = True
        return self.colors[col]

    def current_views(self):
        for window in sublime.windows():
            for view in window.views():
                yield view

    def get_background_col(self, view=None):
        style = view.style()
        bg_col = style.get('background')
        if bg_col:
            return (bg_col + 'FF')[:9].upper()
        return '#333333FF'

    def update(self, view):
        if not self.need_update:
            return
        self.need_update = False

        content = self.color_scheme.content()
        current_colors = set("#%s" % c.upper() for c in re.findall(r'\b%s([a-fA-F0-9]{8})\b' % self.prefix, content))

        bg_col = self.get_background_col(view)

        rules = []
        if not re.search(r'\b%sgutter\b' % self.prefix, content):
            rules.append({
                "scope": "%sgutter" % self.prefix,
                "background": "#000000",
                "foreground": "#ffffff",
            })
        for col, name in self.colors.items():
            if col not in current_colors:
                fg_col = self.get_inv_col(bg_col, col)
                rules.append({
                    "scope": name,
                    "background": col,
                    "foreground": fg_col,
                })

        if rules:
            try:
                # For sublime-color-scheme
                m = re.search(r'([\t ]*)"rules":\s*\[[\r\n]+', content)
                if m:
                    json_rules = json.dumps({"rules": rules}, indent=m.group(1))
                    json_rules = '\n'.join(map(str.rstrip, json_rules.split('\n')[2:-2])) + ',\n'
                    content = content[:m.end()] + json_rules + content[m.end():]
                    write_package(self.color_scheme.path, content)
                    log("Updated sublime-color-scheme")
                    return

                # for tmTheme
                if re.match(r'^\s*<?xml', content):
                    plist_content = plistlib.loads(content.encode('utf-8'))
                    plist_content['settings'].extend({
                        "name": r['name'],
                        "scope": r['scope'],
                        "settings": {
                            "foreground": r['foreground'],
                            "background": r['background'],
                        }
                    } for r in rules)
                    content = plistlib.dumps(plist_content).decode('utf-8')
                    write_package(self.color_scheme.path, content)
                    log("Updated tmTheme")
                    return

                log("Not Updated: Schema format not recognized")
            except Exception as e:
                log("Not Updated: %s" % e)

    def clear(self):
        self.colors = {}

    def setup_color_scheme(self, settings):
        color_scheme = ColorScheme(settings)
        if self.color_scheme and self.color_scheme.path == color_scheme.path:
            if self.color_scheme.time + datetime.timedelta(seconds=1) > color_scheme.time:
                return
            if self.color_scheme.hash() == color_scheme.hash():
                self.color_scheme.time = color_scheme.time
                return
        log("Color scheme %s setup" % color_scheme.path)
        self.color_scheme = color_scheme
        content = self.color_scheme.content()
        self.colors = dict(("#%s" % c, "%s%s" % (self.prefix, c)) for c in re.findall(r'\b%s([a-fA-F0-9]{8})\b' % self.prefix, content))

    def restore_color_scheme(self):
        # do not support empty color scheme
        if not self.color_scheme:
            log("Empty scheme, can't restore")
            return
        if self.color_scheme.restore():
            self.colors = {}
