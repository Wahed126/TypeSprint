"""Opt-in real-display tests: TYPESPRINT_GUI_TESTS=1 /usr/bin/python3 -m unittest tests.test_gtk -v."""
import os
from pathlib import Path
import tempfile
import time
import unittest

ENABLED = os.environ.get("TYPESPRINT_GUI_TESTS") == "1"
if ENABLED:
    from typesprint.app import Application, Window
    from typesprint.storage import Store
    from gi.repository import Adw, Gdk, Gio, GLib, Gtk
    from tests.test_engine import Clock


def pump(seconds=.08):
    context = GLib.MainContext.default()
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        while context.pending():
            context.iteration(False)
        time.sleep(.002)


@unittest.skipUnless(ENABLED, "Set TYPESPRINT_GUI_TESTS=1 in a graphical session")
class GtkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("No GTK display available")
        cls.app = Application()
        cls.app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
        cls.app.register(None)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "history.sqlite3"
        self.clock = Clock()
        self.window = Window(self.app, store=Store(self.path), clock=self.clock)
        self.window.present()
        self.window.input_view.grab_focus()
        pump()

    def tearDown(self):
        self.window.close()
        pump(.03)
        self.temp.cleanup()

    def type(self, text):
        self.window.input_buffer.insert_at_cursor(text, -1)
        pump(.01)

    def test_focused_start_native_unicode_errors_and_backspace(self):
        w = self.window
        self.assertEqual(w.get_focus(), w.input_view)
        self.assertIsNone(w.round.started_at)
        self.type("x")
        self.assertEqual(w.round.started_at, self.clock.now)
        self.assertTrue(w.target_buffer.get_start_iter().has_tag(w.error_tag))
        self.assertTrue(w.input_buffer.get_start_iter().has_tag(w.input_error))
        w.input_buffer.backspace(w.input_buffer.get_end_iter(), True, True)
        self.type(w.round.target[0])
        self.assertEqual(w.round.attempts, 2)
        self.assertEqual(w.round.score().mistakes, 1)
        self.assertFalse(w.target_buffer.get_start_iter().has_tag(w.error_tag))
        self.assertTrue(w.target_buffer.get_start_iter().has_tag(w.correct_tag))
        self.assertTrue(w.target_buffer.get_iter_at_offset(1).has_tag(w.current_tag))
        w.mode.set_selected(1)
        w.category.set_selected(1)
        self.type("äöüß")
        self.assertEqual(w.round.text, "äöüß")
        self.assertEqual(w.round.attempts, 4)

    def test_restart_action_resets_active_round_and_focus(self):
        w = self.window
        self.type("wrong")
        self.clock.advance(4)
        w.activate_action("win.restart", None)
        pump()
        self.assertEqual(w.round.text, "")
        self.assertEqual(w.round.attempts, 0)
        self.assertIsNone(w.round.started_at)
        self.assertEqual(w.get_focus(), w.input_view)
        self.assertEqual(len(w.store.history()), 0)

    def test_deadline_results_play_again_and_history_after_relaunch(self):
        w = self.window
        w.duration.set_selected(0)
        self.type(w.round.target[:10])
        self.clock.advance(15)
        self.type("z")
        self.assertEqual(w.round.attempts, 10)
        self.assertEqual(w.play_stack.get_visible_child_name(), "results")
        self.assertEqual(w.get_focus(), w.results_heading)
        self.assertEqual(len(w.store.history()), 1)
        self.assertEqual(w.store.history()[0]["elapsed"], 15)
        w._tick()
        pump()
        self.assertEqual(len(w.store.history()), 1)
        self.assertIsNone(w.get_default_widget())
        w.activate_default()
        pump(.35)
        self.assertEqual(w.play_stack.get_visible_child_name(), "results")
        w.child_focus(Gtk.DirectionType.TAB_FORWARD)
        self.assertEqual(w.get_focus(), w.again)
        w.activate_default()
        pump(.35)  # GtkButton animates keyboard activation before emitting clicked.
        self.assertEqual(w.play_stack.get_visible_child_name(), "round")
        self.assertIsNone(w.get_default_widget())
        w.close()
        self.window = Window(self.app, store=Store(self.path), clock=self.clock)
        self.window.present()
        self.window.pages.set_visible_child_name("history")
        pump()
        self.assertIsNotNone(self.window.history_list.get_first_child())
        self.assertFalse(self.window.history_empty.get_visible())
        self.window.activate_action("win.restart", None)
        pump()
        self.assertEqual(self.window.pages.get_visible_child_name(), "play")
        self.assertEqual(self.window.get_focus(), self.window.input_view)

    def test_typing_keys_after_expiry_cannot_restart_results(self):
        w = self.window
        w.duration.set_selected(0)
        self.type(w.round.target[:5])
        self.clock.advance(15)
        w._tick()
        pump()
        finished = w.round
        self.assertEqual(w.get_focus(), w.results_heading)
        self.assertIsNone(w.get_default_widget())
        for key in (Gdk.KEY_space, Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.assertTrue(w._results_keys.emit("key-pressed", key, 0, Gdk.ModifierType(0)))
            w.activate_default()
        self.type("still typing more words ")
        pump(.35)
        self.assertIs(w.round, finished)
        self.assertEqual(w.play_stack.get_visible_child_name(), "results")
        self.assertEqual(len(w.store.history()), 1)
        w.child_focus(Gtk.DirectionType.TAB_FORWARD)
        self.assertEqual(w.get_focus(), w.again)
        w.activate_default()
        pump(.35)
        self.assertIsNot(w.round, finished)
        self.assertEqual(w.play_stack.get_visible_child_name(), "round")
        self.assertIsNone(w.round.started_at)

    def test_result_feedback_changes_with_speed_and_accuracy(self):
        w = self.window
        w.duration.set_selected(0)
        for length, wrong, title in ((20, 0, "A clean foundation."),
                                      (110, 0, "Fast and flawless."),
                                      (140, 20, "Fast hands, room for control.")):
            with self.subTest(title=title):
                target = w.round.target[:length]
                typed = ''.join(('q' if char == 'x' else 'x') if i < wrong else char
                                for i, char in enumerate(target))
                self.type(typed)
                self.clock.advance(15)
                w._tick()
                pump()
                self.assertEqual(w.feedback_title.get_label(), title)
                self.assertTrue(w.feedback_message.get_label())
                self.assertEqual(w.get_focus(), w.results_heading)
                if wrong:
                    self.assertIn("20 mistakes in 15.0 seconds", w.feedback_message.get_label())
                w.again.emit("clicked")
                pump()

    def test_restart_preserves_completion_before_results_callback(self):
        w = self.window
        w.duration.set_selected(0)
        self.type(w.round.target[:5])
        self.clock.advance(15)
        # Restart before the timer has had any opportunity to deliver expiry.
        w.activate_action("win.restart", None)
        self.assertEqual(len(w.store.history()), 1)
        self.assertEqual(w.store.history()[0]["elapsed"], 15)
        self.assertIsNone(w.round.started_at)
        # Also cover completion queued by the final Practice character.
        w.mode.set_selected(1)
        w.input_buffer.insert_at_cursor(w.round.target, -1)
        self.assertTrue(w.round.finished)
        w.activate_action("win.restart", None)
        pump()
        self.assertEqual(len(w.store.history()), 2)
        self.assertEqual(w.round.text, "")

    def test_code_newlines_indentation_and_settings_persist(self):
        w = self.window
        w.mode.set_selected(1)
        w.category.set_selected(2)
        target = w.round.target
        self.assertIn("\n    ", target)
        self.assertEqual(w.target_view.get_wrap_mode(), Gtk.WrapMode.NONE)
        self.type(target[:8])
        self.clock.advance(4)
        self.type(target[8:])
        self.assertEqual(w.round.text, target)
        self.assertEqual(w.play_stack.get_visible_child_name(), "results")
        self.assertEqual(w.round.score().accuracy, 100)
        w.font_scale.set_value(34)
        self.assertEqual(w.store.get("font_size"), "34")

    def test_survival_bonus_not_repeated_in_native_buffer(self):
        w = self.window
        w.mode.set_selected(2)
        word = w.round.target.split(" ")[0] + " "
        self.type(word)
        self.assertEqual(w.round.bonus_seconds, 1)
        w.input_buffer.backspace(w.input_buffer.get_end_iter(), True, True)
        self.type(" ")
        self.assertEqual(w.round.bonus_seconds, 1)

    def test_text_area_stays_fixed_and_active_line_is_visible_at_two_sizes(self):
        w = self.window
        w.mode.set_selected(1)
        w.category.set_selected(2)
        w.font_scale.set_value(36)
        for width, height in [(560, 640), (1200, 950)]:
            w.set_default_size(width, height)
            pump(.25)
            w._new_round()
            pump(.08)
            before = w.target_scroll.compute_bounds(w)[1]
            self.type(w.round.target[:-2])
            self.clock.advance(2)
            w._tick()
            pump(.2)
            after = w.target_scroll.compute_bounds(w)[1]
            self.assertAlmostEqual(before.get_y(), after.get_y(), delta=1)
            self.assertAlmostEqual(before.get_height(), after.get_height(), delta=1)
            cursor = w.target_buffer.get_iter_at_mark(w.target_mark)
            rect = w.target_view.get_iter_location(cursor)
            visible = w.target_view.get_visible_rect()
            self.assertGreaterEqual(rect.y, visible.y)
            self.assertLessEqual(rect.y + rect.height, visible.y + visible.height + 1)
            input_cursor = w.input_buffer.get_iter_at_mark(w.input_buffer.get_insert())
            input_rect = w.input_view.get_iter_location(input_cursor)
            input_visible = w.input_view.get_visible_rect()
            self.assertGreaterEqual(input_rect.y, input_visible.y)
            self.assertLessEqual(input_rect.y + input_rect.height, input_visible.y + input_visible.height + 1)
        self.assertGreater(w.target_view.get_width(), 0)


if __name__ == "__main__":
    unittest.main()
