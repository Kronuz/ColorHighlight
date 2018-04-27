import os
import re
import json
from collections import OrderedDict

import sublime

from .colors import names_to_hex, xterm_to_hex


all_names_to_hex = dict(names_to_hex, **xterm_to_hex)


def log(s):
    # print("[Colorizer]", s)
    pass


class SchemaColorizer(object):
    name = "Color"
    prefix = "col_"
    backup_ext = ".chback"

    colors = {}
    color_scheme = None
    need_upd = False
    need_restore = False
    need_backup = False
    gen_string = """
        <dict>
            <key>name</key>
            <string>{name}</string>
            <key>scope</key>
            <string>{scope}</string>
            <key>settings</key>
            <dict>
                <key>background</key>
                <string>{background}</string>
                <key>foreground</key>
                <string>{foreground}</string>
            </dict>
        </dict>
"""

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
                print("Invalid color: %r" % col)

    def write_file(self, pp, fl, s):
        rf = pp + fl
        dn = os.path.dirname(rf)
        if not os.path.exists(dn):
            os.makedirs(dn)
        f = open(rf, 'w')
        f.write(s)
        f.close()

    def read_file(self, pp, fl):
        rf = pp + fl
        if os.path.exists(rf):
            f = open(rf, 'r')
            res = f.read()
            f.close()
        else:
            rf = 'Packages' + fl
            res = sublime.load_resource(rf)
        return res

    def get_inv_col(self, bg_col, col):
        br = int(bg_col[1:3], 16) / 255.0
        bg = int(bg_col[3:5], 16) / 255.0
        bb = int(bg_col[5:7], 16) / 255.0

        r = int(col[1:3], 16) / 255.0
        g = int(col[3:5], 16) / 255.0
        b = int(col[5:7], 16) / 255.0
        a = int(col[7:9], 16) / 255.0

        r = br * (1 - a) + r * a
        g = bg * (1 - a) + g * a
        b = bb * (1 - a) + b * a

        # L = (max(r, g, b) + min(r, g, b)) / 2
        # Y709 = 0.2126 * r + 0.7152 * g + 0.0722 * b
        Y601 = 0.299 * r + 0.587 * g + 0.114 * b

        v = Y601

        if v >= 0.5:
            v -= 0.5
        else:
            v += 0.5

        return '#%sFF' % (('%02X' % (v * 255)) * 3)

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
            bg_col = view.style()['background']
        else:
            bg_col = '#333333FF'

        rules = []
        for col, name in self.colors.items():
            if col not in current_colors:
                fg_col = self.get_inv_col(bg_col, col)
                rules.append({
                    "name": self.name,
                    "scope": name,
                    "background": col,
                    "foreground": fg_col,
                })

        if rules:
            try:
                json_content = json.loads(content, object_pairs_hook=OrderedDict)
                json_content['rules'].extend(rules)
                content = json.dumps(json_content, indent=4)
            except ValueError:
                string = ""
                for rule in rules:
                    string += self.gen_string.format(**rule)
                if string:
                    # edit content
                    n = content.find("<array>") + len("<array>")
                    try:
                        content = content[:n] + string + content[n:]
                    except UnicodeDecodeError:
                        content = content[:n] + string.encode("utf-8") + content[n:]

            self.write_file(packages_path, cs, content)
            self.need_restore = True
            log("Updated")

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
            self.colors = {}
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
