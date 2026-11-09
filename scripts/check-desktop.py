#!/usr/bin/python3
"""Play a real-time Sprint through GTK buffers/actions and save screenshots.

Run from project root in a graphical desktop session:
GSETTINGS_BACKEND=memory /usr/bin/python3 scripts/check-desktop.py

This uses isolated temporary storage. It does not synthesize physical key events.
"""
from pathlib import Path
import sys
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from typesprint.app import Application, Window
from typesprint.storage import Store
from gi.repository import Adw, Gdk, Gio, GLib, Gtk


def pump(seconds=.08):
    context = GLib.MainContext.default()
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        while context.pending():
            context.iteration(False)
        time.sleep(.002)


def screenshot(window, name):
    paintable = Gtk.WidgetPaintable.new(window)
    node = None
    # A newly created paintable needs a frame before its current image exists.
    for _ in range(10):
        window.queue_draw()
        pump(.06)
        snapshot = Gtk.Snapshot.new()
        paintable.snapshot(snapshot, window.get_width(), window.get_height())
        node = snapshot.to_node()
        if node is not None:
            break
    if node is None:
        # GNOME can suspend rendering for an occluded window. Geometry, focus,
        # timing and persistence checks still run independently of capture.
        print(f"Snapshot unavailable for {name}; continuing layout checks", flush=True)
        return
    texture = window.get_renderer().render_texture(node, None)
    out = ROOT / "artifacts" / (name + ".png")
    out.parent.mkdir(exist_ok=True)
    texture.save_to_png(str(out))
    print(f"Captured {out.name}: {window.get_width()} × {window.get_height()}", flush=True)


def type_text(window, text):
    for character in text:
        window.input_buffer.insert_at_cursor(character, -1)
        pump(.04)


def verify_relaunch(path):
    app = Application()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    w = Window(app, store=Store(path))
    w.present()
    w.pages.set_visible_child_name("history")
    pump(.4)
    assert w.history_list.get_first_child() is not None
    assert len(w.store.history()) == 1
    screenshot(w, "history-relaunched")
    w.close()
    pump(.05)
    print("Completed session is visible in History in a fresh application process", flush=True)


def main():
    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        raise SystemExit("No graphical display available")
    app = Application()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    with tempfile.TemporaryDirectory(prefix="typesprint-desktop-") as tmp:
        path = Path(tmp) / "history.sqlite3"
        w = Window(app, store=Store(path))
        try:
            w.duration.set_selected(0)
            w.set_default_size(560, 640)
            w.present()
            w.input_view.grab_focus()
            pump(.4)
            type_text(w, "x")
            w.input_buffer.backspace(w.input_buffer.get_end_iter(), True, True)
            type_text(w, w.round.target[0])
            assert w.round.score().mistakes == 1
            assert w.round.score().correct_characters == 1
            assert app.get_accels_for_action("win.restart") == ["<Control>r"]
            w.activate_action("win.restart", None)
            assert w.round.text == "" and w.round.started_at is None
            assert w.get_focus() == w.input_view
            print("GTK insertion, Backspace, restart action, and accelerator registration passed", flush=True)
            start_y = w.target_scroll.compute_bounds(w)[1].get_y()
            type_text(w, w.round.target[:55])
            assert w.round.attempts == 55
            assert start_y == w.target_scroll.compute_bounds(w)[1].get_y()
            screenshot(w, "play-small-light")
            bounds = w.input_scroll.compute_bounds(w)[1]
            assert bounds.get_y() + bounds.get_height() <= w.get_height(), "Typing field clipped in small window"
            w.child_focus(Gtk.DirectionType.TAB_FORWARD)
            assert w.get_focus() != w.input_view
            w.activate_action("win.history", None)
            assert w.pages.get_visible_child_name() == "history"
            w.activate_action("win.play", None)
            assert w.get_focus() == w.input_view
            w.set_default_size(1200, 950)
            pump(.35)
            type_text(w, w.round.target[len(w.round.text):len(w.round.text) + 80])
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            pump(.2)
            screenshot(w, "play-large-dark")
            print("Focus traversal, page actions, and both window sizes passed; waiting for the 15-second deadline", flush=True)
            until = time.monotonic() + 17
            while w.play_stack.get_visible_child_name() != "results" and time.monotonic() < until:
                pump(.05)
            assert w.play_stack.get_visible_child_name() == "results"
            assert w.round.score().elapsed == 15
            assert len(w.store.history()) == 1
            assert w.get_focus() == w.again
            screenshot(w, "results-dark")
            w.again.emit("clicked")
            assert w.play_stack.get_visible_child_name() == "round"
            assert w.round.started_at is None
            assert w.get_focus() == w.input_view
            print("Full real-time Sprint, results focus, and Play again passed", flush=True)
            w.close()
            pump(.05)
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--verify-history", str(path)], check=True)
        finally:
            w.close()
            pump(.05)
    print("All desktop checks passed", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-history":
        verify_relaunch(sys.argv[2])
    else:
        main()
