#!/usr/bin/python3
"""Lupa, a keyboard launcher for Linux (GTK3).

Run again to toggle the window. Search: applications, calculator (type
`2*(3+4)`), files via plocate (type at least 3 chars), and a web-search
fallback. Enter opens, Esc closes, Up/Down move, Ctrl+1..9 pick a row.
"""

import ast
import math
import operator
import os
import subprocess
import urllib.parse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

WEB = "https://www.google.com/search?q="
MAX_ROWS = 8
PLACEHOLDER = "Search apps, files or math"

CSS = b"""
window { background: transparent; }
.box { background: rgba(32,32,36,0.94); border-radius: 14px;
       border: 1px solid rgba(255,255,255,0.12); padding: 10px; }
entry { font-size: 22px; background: transparent; color: #fff;
        border: none; box-shadow: none; padding: 8px; }
list, row { background: transparent; color: #eee; }
row { border-radius: 8px; padding: 6px 8px; }
row:selected { background: rgba(70,130,255,0.85); color: #fff; }
.sub { font-size: 11px; opacity: 0.65; }
.hint { font-size: 22px; color: rgba(255,255,255,0.4); }
"""

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_NAMES = {"pi": math.pi, "e": math.e}
_FUNCS = {
    n: getattr(math, n)
    for n in ("sqrt", "sin", "cos", "tan", "log", "log10", "exp", "floor", "ceil")
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and len(node.args) == 1
    ):
        return _FUNCS[node.func.id](_eval(node.args[0]))
    raise ValueError("unsupported")


def calc(text):
    """Return a formatted result, or None if text is not an expression."""
    if not any(c.isdigit() for c in text):
        return None
    try:
        value = _eval(
            ast.parse(text.replace("^", "**").replace(",", "."), mode="eval").body
        )
    except (
        ValueError,
        SyntaxError,
        ZeroDivisionError,
        OverflowError,
        TypeError,
        RecursionError,
    ):
        return None
    if isinstance(value, float):
        value = round(value, 10)
        if value == int(value):
            value = int(value)
    return str(value)


class Result:
    def __init__(self, title, subtitle, icon, action):
        self.title, self.subtitle, self.icon, self.action = (
            title,
            subtitle,
            icon,
            action,
        )


def search_apps(query):
    q = query.lower()
    scored = []
    for app in Gio.AppInfo.get_all():
        if not app.should_show():
            continue
        name = app.get_display_name() or ""
        low = name.lower()
        if low.startswith(q):
            score = 0
        elif q in low:
            score = 1
        elif (
            q in (app.get_generic_name() or "").lower()
            or q in (app.get_keywords() and " ".join(app.get_keywords()) or "").lower()
        ):
            score = 2
        else:
            continue
        scored.append((score, low, app))
    scored.sort(key=lambda t: t[:2])
    return [
        Result(
            a.get_display_name(),
            a.get_description() or "Application",
            a.get_icon(),
            lambda a=a: a.launch([], None),
        )
        for _, _, a in scored[:MAX_ROWS]
    ]


def search_files(query):
    if len(query) < 3 or not os.path.exists("/usr/bin/plocate"):
        return []
    home = os.path.expanduser("~")
    try:
        out = subprocess.run(
            ["plocate", "-i", "-l", "40", "-b", "--", query],
            capture_output=True,
            text=True,
            timeout=1.5,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    paths = [
        p for p in out.splitlines() if p.startswith(home) and "/." not in p[len(home) :]
    ]
    results = []
    for p in paths[:5]:
        uri = Gio.File.new_for_path(p).get_uri()
        icon = Gio.content_type_get_icon(
            "inode/directory"
            if os.path.isdir(p)
            else Gio.content_type_guess(p, None)[0]
        )
        results.append(
            Result(
                os.path.basename(p),
                p.replace(home, "~", 1),
                icon,
                lambda uri=uri: open_uri(uri),
            )
        )
    return results


def open_uri(uri):
    Gio.AppInfo.launch_default_for_uri(uri, None)


class Launcher(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.dcotecnologia.Lupa")
        self.win = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        if self.win is None:
            self.build()
        if self.win.get_visible():
            self.win.hide()
        else:
            self.show()

    # -- UI -----------------------------------------------------------
    def build(self):
        self.win = win = Gtk.ApplicationWindow(application=self)
        win.set_decorated(False)
        win.set_skip_taskbar_hint(True)
        win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        win.set_keep_above(True)
        win.set_default_size(640, -1)
        win.set_resizable(False)
        visual = win.get_screen().get_rgba_visual()
        if visual:
            win.set_visual(visual)
        win.set_app_paintable(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.get_style_context().add_class("box")
        # GTK 3 only shows the placeholder of an entry that is not focused, and this
        # one always has the focus, so a dim label over the entry plays that part
        self.entry = Gtk.Entry()
        self.hint = Gtk.Label(
            label=PLACEHOLDER,
            xalign=0,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER,
            margin_start=10,
        )
        self.hint.get_style_context().add_class("hint")
        field = Gtk.Overlay()
        field.add(self.entry)
        field.add_overlay(self.hint)
        field.set_overlay_pass_through(self.hint, True)
        self.entry.connect("changed", self.on_changed)
        self.entry.connect("key-press-event", self.on_key)
        self.entry.connect("activate", lambda *_: self.run_selected())
        box.pack_start(field, False, False, 0)
        self.list = Gtk.ListBox()
        self.list.connect("row-activated", lambda _l, _r: self.run_selected())
        self.revealer = Gtk.Revealer(reveal_child=False)
        self.revealer.add(self.list)
        box.pack_start(self.revealer, False, False, 0)
        win.add(box)

        self.focus_handler = win.connect("focus-out-event", lambda *_: win.hide())
        win.connect("delete-event", lambda w, _e: w.hide() or True)
        win.show_all()
        win.hide()
        self.results = []
        self.timer = 0

    def show(self):
        self.entry.set_text("")
        self.clear()
        self.win.show_all()
        self.revealer.set_reveal_child(False)
        screen = (
            Gdk.Display.get_default().get_primary_monitor()
            or Gdk.Display.get_default().get_monitor(0)
        )
        geo = screen.get_geometry()
        self.win.move(geo.x + (geo.width - 640) // 2, geo.y + geo.height // 4)
        self.win.present_with_time(Gtk.get_current_event_time())
        self.entry.grab_focus()

    def clear(self):
        for row in self.list.get_children():
            self.list.remove(row)
        self.results = []
        self.revealer.set_reveal_child(False)

    def on_key(self, _w, ev):
        key = ev.keyval
        if key == Gdk.KEY_Escape:
            self.win.hide()
            return True
        if key in (Gdk.KEY_Down, Gdk.KEY_Up):
            self.move(1 if key == Gdk.KEY_Down else -1)
            return True
        if ev.state & Gdk.ModifierType.CONTROL_MASK and Gdk.KEY_1 <= key <= Gdk.KEY_9:
            self.select(key - Gdk.KEY_1)
            self.run_selected()
            return True
        return False

    def move(self, step):
        if not self.results:
            return
        row = self.list.get_selected_row()
        idx = (row.get_index() if row else -1) + step
        self.select(max(0, min(idx, len(self.results) - 1)))

    def select(self, idx):
        row = self.list.get_row_at_index(idx)
        if row:
            self.list.select_row(row)

    # -- search -------------------------------------------------------
    def on_changed(self, entry):
        self.hint.set_visible(not entry.get_text())
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer = GLib.timeout_add(80, self.refresh)  # debounce typing

    def refresh(self):
        self.timer = 0
        text = self.entry.get_text().strip()
        self.clear()
        if not text:
            return False
        results = []
        value = calc(text)
        if value is not None:
            results.append(
                Result(
                    f"= {value}",
                    "Press Enter to copy",
                    None,
                    lambda v=value: self.copy(v),
                )
            )
        results += search_apps(text)
        results += search_files(text)
        results.append(
            Result(
                f"Search the web for “{text}”",
                "Browser",
                None,
                lambda t=text: open_uri(WEB + urllib.parse.quote_plus(t)),
            )
        )
        self.results = results[: MAX_ROWS + 6]
        for i, r in enumerate(self.results):
            self.list.add(self.make_row(r, i))
        self.list.show_all()
        self.revealer.set_reveal_child(True)
        self.select(0)
        return False

    @staticmethod
    def make_row(r, i):
        hb = Gtk.Box(spacing=10)
        img = Gtk.Image.new_from_gicon(
            r.icon or Gio.ThemedIcon.new("system-search"), Gtk.IconSize.DND
        )
        img.set_pixel_size(32)
        hb.pack_start(img, False, False, 0)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        t = Gtk.Label(label=r.title, xalign=0, ellipsize=3)
        s = Gtk.Label(label=r.subtitle, xalign=0, ellipsize=3)
        s.get_style_context().add_class("sub")
        vb.pack_start(t, False, False, 0)
        vb.pack_start(s, False, False, 0)
        hb.pack_start(vb, True, True, 0)
        if i < 9:
            hb.pack_end(Gtk.Label(label=f"Ctrl+{i + 1}"), False, False, 0)
        return hb

    def run_selected(self):
        row = self.list.get_selected_row()
        if not row:
            return
        action = self.results[row.get_index()].action
        self.win.hide()
        try:
            action()
        except GLib.Error as err:
            print("launch failed:", err.message)

    def copy(self, value):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(value, -1)
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).store()


if __name__ == "__main__":
    raise SystemExit(Launcher().run([]))
