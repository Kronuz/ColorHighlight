import os
import re
import sys
import json
import errno
import plistlib

import sublime

from .colors import names_to_hex, xterm_to_hex


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


class SchemaColorizer(object):
    prefix = "col_"
    backup_ext = ".chback"

    colors = {}
    color_scheme = None
    need_upd = False
    need_restore = False
    need_backup = False

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

    def write_file(self, pp, fl, s):
        rf = pp + fl
        try:
            os.makedirs(os.path.dirname(rf))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        with open(rf, 'w') as f:
            f.write(s)

    def read_file(self, pp, fl):
        rf = pp + fl
        if os.path.exists(rf):
            with open(rf, 'r') as f:
                res = f.read()
        else:
            rf = 'Packages' + fl
            res = sublime.load_resource(rf)
        return res

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
            self.need_upd = True
        return self.colors[col]

    def need_update(self):
        return self.need_upd

    def color_scheme_path(self, view):
        packages_path = sublime.packages_path()
        cs = self.color_scheme
        if cs is None:
            self.color_scheme = view.settings().get('color_scheme')
            cs = self.color_scheme
        # do not support empty color scheme
        if not cs:
            log("Empty scheme")
            return
        # extract name
        cs = cs[cs.find('/'):]
        return packages_path, cs

    def get_color_scheme(self, packages_path, cs):
        content = self.read_file(packages_path, cs)
        if os.path.exists(packages_path + cs + self.backup_ext):
            log("Already backuped")
            self.need_restore = True
        else:
            self.write_file(packages_path, cs + self.backup_ext, content)  # backup
            log("Backup done")
        return content

    def update(self, view):
        if not self.need_upd:
            return
        self.need_upd = False

        color_scheme_path = self.color_scheme_path(view)
        if not color_scheme_path:
            return
        packages_path, cs = color_scheme_path
        content = self.get_color_scheme(packages_path, cs)

        current_colors = set("#%s" % c.upper() for c in re.findall(r'\b%s([a-fA-F0-9]{8})\b' % self.prefix, content))

        if hasattr(view, 'style'):
            bg_col = (view.style()['background'] + 'FF')[:9].upper()
        else:
            bg_col = '#333333FF'

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
                    self.write_file(packages_path, cs, content)
                    self.need_restore = True
                    log("Updated sublime-color-scheme")

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
                    self.write_file(packages_path, cs, content)
                    self.need_restore = True
                    log("Updated tmTheme")

                log("Not Updated: Schem format not recognized")
            except Exception as e:
                log("Not Updated: %s" % e)

    def clear(self):
        self.colors.clear()

    def restore_color_scheme(self):
        if not self.need_restore:
            return
        self.need_restore = False
        cs = self.color_scheme
        # do not support empty color scheme
        if not cs:
            log("Empty scheme, can't restore")
            return
        # extract name
        cs = cs[cs.find('/'):]
        packages_path = sublime.packages_path()
        if os.path.exists(packages_path + cs + self.backup_ext):
            log("Starting restore scheme: " + cs)
            # TODO: move to other thread
            self.write_file(packages_path, cs, self.read_file(packages_path, cs + self.backup_ext))
            self.colors.clear()
            log("Restore done.")
        else:
            log("No backup :(")

    def set_color_scheme(self, view):
        settings = view.settings()
        cs = settings.get('color_scheme')
        if cs != self.color_scheme:
            color_scheme_path = self.color_scheme_path(view)
            if color_scheme_path:
                packages_path, cs = color_scheme_path
                content = self.get_color_scheme(packages_path, cs)
                self.colors = dict(("#%s" % c, "%s%s" % (self.prefix, c)) for c in re.findall(r'\b%s([a-fA-F0-9]{8})\b' % self.prefix, content))
            self.color_scheme = settings.get('color_scheme')
            self.need_backup = True

    def change_color_scheme(self, view):
        cs = view.settings().get('color_scheme')
        if cs and cs != self.color_scheme:
            log("Color scheme changed %s -> %s" % (self.color_scheme, cs))
            self.restore_color_scheme()
            self.set_color_scheme(view)
            self.update(view)
