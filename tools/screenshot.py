#!/usr/bin/python3
"""Render the screenshots of the README from the real window (needs a display).

Run it with `make screenshot`. It types a few queries into the launcher,
waits for the results and saves the window, with its rounded corners and
transparency, as PNG files in docs/screenshots/.
"""

import sys
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import lupa  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
SHOTS = [("apps", "fire"), ("calculator", "2*(3+4)^2")]


def pump(milliseconds):
    """Let GTK draw for a while."""
    end = GLib.get_monotonic_time() + milliseconds * 1000
    while GLib.get_monotonic_time() < end:
        while Gtk.events_pending():
            Gtk.main_iteration()


def capture(win, path):
    """Save the content of the window (alpha included) as a PNG."""
    gdk_window = win.get_window()
    pixbuf = Gdk.pixbuf_get_from_window(
        gdk_window, 0, 0, gdk_window.get_width(), gdk_window.get_height()
    )
    pixbuf.savev(str(path), "png", [], [])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = lupa.Launcher()
    app.register(None)
    app.do_startup()
    app.build()
    app.show()
    # keep the window while it takes the focus of the terminal that started this
    app.win.disconnect(app.focus_handler)
    for name, query in SHOTS:
        app.entry.set_text(query)
        app.refresh()
        pump(600)
        capture(app.win, OUT / f"{name}.png")
        print(f"saved {OUT / (name + '.png')}")


if __name__ == "__main__":
    main()
