"""Native GTK 4 / libadwaita application."""
import gi
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from .engine import Config
from .exercises import Exercises
from .storage import Store

APP_ID = "io.github.typesprint.TypeSprint"
MODES = ["Sprint", "Practice", "Survival"]
CATEGORIES = {"english": "English", "german": "Deutsch", "python": "Python", "typescript": "TypeScript"}

CSS = """
window { background: @window_bg_color; }
.brand { font-weight: 800; letter-spacing: 1px; }
.hero { font-size: 30px; font-weight: 800; letter-spacing: -1px; }
.eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 2px; }
.stat-value { font-size: 26px; font-weight: 700; font-feature-settings: 'tnum'; }
.stat-label { font-size: 10px; font-weight: 700; letter-spacing: 1px; }
.stats { padding: 15px 8px; border-radius: 14px; background: @card_bg_color; border: 1px solid alpha(@window_fg_color, 0.10); }
.compact .stats { padding: 8px; }
.exercise { border-radius: 14px; background: @card_bg_color; border: 1px solid alpha(@window_fg_color, 0.13); }
.exercise:focus-within { outline: 2px solid @accent_bg_color; outline-offset: 2px; }
textview, textview text { background: transparent; }
textview { padding: 16px; border-radius: 12px; }
.hint { font-size: 12px; }
.pill { border-radius: 20px; padding: 5px 12px; background: alpha(@accent_bg_color, 0.13); color: @accent_color; font-size: 12px; font-weight: 700; }
.result-title { font-size: 32px; font-weight: 800; }
.best { color: @accent_color; font-weight: 700; }
.primary-action { padding: 12px 30px; border-radius: 24px; font-weight: 700; }
button:focus-visible, dropdown:focus-visible, scale:focus-visible { outline: 2px solid @accent_bg_color; outline-offset: 2px; }
"""


def label(text="", css=None, xalign=0):
    widget = Gtk.Label(label=text, xalign=xalign)
    if css:
        widget.add_css_class(css)
    return widget


def box(orientation=Gtk.Orientation.VERTICAL, spacing=12):
    return Gtk.Box(orientation=orientation, spacing=spacing)


def margins(widget, value):
    for side in ("top", "bottom", "start", "end"):
        getattr(widget, f"set_margin_{side}")(value)
    return widget


class Window(Adw.ApplicationWindow):
    def __init__(self, app, store=None, exercises=None, clock=None):
        super().__init__(application=app, title="TypeSprint", default_width=940, default_height=840)
        self.set_size_request(540, 620)
        self.store = store or Store()
        self.exercises = exercises or Exercises()
        self.clock = clock
        self.round = None
        self._saved = False
        self._finishing = False
        self._suppress = False
        self._timer_id = 0
        self._result_idle = 0
        self._scroll_idle = 0
        self._font_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(self.get_display(), self._font_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._provider = provider
        Gtk.IconTheme.get_for_display(self.get_display()).add_search_path(
            str(Path(__file__).resolve().parent.parent / "packaging" / "icons"))
        self.set_icon_name(APP_ID)
        self._build()
        self.connect("close-request", self._on_close)
        self._new_round()
        self._timer_id = GLib.timeout_add(50, self._tick)

    def _build(self):
        root = box(spacing=0)
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="TypeSprint", subtitle="A little practice. A better rhythm.")
        header.set_title_widget(title)
        root.append(header)
        self.pages = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.pages.set_vexpand(True)
        nav = Gtk.StackSwitcher(stack=self.pages, halign=Gtk.Align.CENTER)
        nav.set_margin_top(8)
        nav.set_margin_bottom(12)
        root.append(nav)
        self.pages.add_titled(self._build_play(), "play", "Play")
        self.pages.add_titled(self._build_history(), "history", "History")
        self.pages.add_titled(self._build_settings(), "settings", "Settings")
        self.pages.connect("notify::visible-child-name", self._page_changed)
        root.append(self.pages)
        self.toast_overlay = Adw.ToastOverlay(child=root)
        self.set_content(self.toast_overlay)
        action = Gio.SimpleAction.new("restart", None)
        action.connect("activate", lambda *_: self._restart())
        self.add_action(action)
        for name in ("play", "history", "settings"):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _, __, page=name: self.pages.set_visible_child_name(page))
            self.add_action(action)
        self.get_application().set_accels_for_action("win.restart", ["<Control>r"])
        for i, name in enumerate(("play", "history", "settings"), 1):
            self.get_application().set_accels_for_action("win." + name, [f"<Control>{i}"])

    def _wrap_page(self, child):
        clamp = Adw.Clamp(maximum_size=1000, tightening_threshold=740)
        clamp.set_child(margins(child, 24))
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(clamp)
        return scroll

    def _build_play(self):
        self.play_stack = Gtk.Stack()
        content = box(spacing=18)
        heading = box(spacing=4)
        heading.append(label("TYPE • BREATHE • REPEAT", "eyebrow"))
        heading.append(label("Find your rhythm.", "hero"))
        heading.append(label("A fresh start is always one shortcut away.", "dim-label"))
        content.append(heading)
        controls = box(Gtk.Orientation.HORIZONTAL, 10)
        controls.set_homogeneous(True)
        self.mode = Gtk.DropDown.new_from_strings(MODES)
        try:
            selected = MODES.index(self.store.get("mode", "sprint").title())
        except ValueError:
            selected = 0
        self.mode.set_selected(selected)
        self.category = Gtk.DropDown()
        self.duration = Gtk.DropDown.new_from_strings(["15 seconds", "30 seconds", "60 seconds"])
        duration = self.store.get("duration", "30")
        self.duration.set_selected(["15", "30", "60"].index(duration) if duration in {"15", "30", "60"} else 1)
        for title, widget in (("Mode", self.mode), ("Exercise", self.category), ("Sprint length", self.duration)):
            item = box(spacing=5)
            item.append(label(title, "dim-label"))
            widget.update_property([Gtk.AccessibleProperty.LABEL], [title])
            item.append(widget)
            controls.append(item)
        self._set_categories(self.store.get("category", "english"))
        self.mode.connect("notify::selected", self._mode_changed)
        self.category.connect("notify::selected", self._config_changed)
        self.duration.connect("notify::selected", self._config_changed)
        self.duration.set_sensitive(self.mode.get_selected() == 0)
        content.append(controls)
        stats = box(Gtk.Orientation.HORIZONTAL, 0)
        stats.set_homogeneous(True)
        stats.add_css_class("stats")
        self.metrics = {}
        for key, title in (("wpm", "WPM"), ("accuracy", "ACCURACY"), ("mistakes", "MISTAKES"), ("clock", "TIME")):
            item = box(spacing=3)
            val = label("—", "stat-value", .5)
            val.set_width_chars(6)
            val.set_max_width_chars(6)
            val.set_ellipsize(Pango.EllipsizeMode.END)
            item.append(val)
            item.append(label(title, "stat-label", .5))
            stats.append(item)
            self.metrics[key] = val
        content.append(stats)
        status = box(Gtk.Orientation.HORIZONTAL)
        self.state_label = label("Ready when you are", "pill")
        status.append(self.state_label)
        self.progress_label = label("", "dim-label", 1)
        self.progress_label.set_hexpand(True)
        status.append(self.progress_label)
        content.append(status)
        self.target_view = Gtk.TextView(editable=False, cursor_visible=False,
                                        wrap_mode=Gtk.WrapMode.WORD_CHAR, monospace=True,
                                        top_margin=5, bottom_margin=5)
        self.target_view.set_can_focus(False)
        self.target_view.add_css_class("typing-text")
        self.target_view.update_property([Gtk.AccessibleProperty.LABEL], ["Exercise text. Match this text in the typing field below."])
        self.target_buffer = self.target_view.get_buffer()
        self.correct_tag = self.target_buffer.create_tag("correct", weight=Pango.Weight.BOLD)
        self.error_tag = self.target_buffer.create_tag("error", underline=Pango.Underline.ERROR, weight=Pango.Weight.BOLD)
        self.current_tag = self.target_buffer.create_tag("current", underline=Pango.Underline.DOUBLE, weight=Pango.Weight.HEAVY)
        self.target_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                               min_content_height=155)
        self.target_scroll.set_size_request(-1, 155)
        self.target_scroll.set_child(self.target_view)
        self.target_scroll.add_css_class("exercise")
        content.append(self.target_scroll)
        input_heading = box(Gtk.Orientation.HORIZONTAL)
        input_heading.append(label("YOUR TURN", "eyebrow"))
        self.legend = label("Bold: correct   ·   Underline: error   ·   Double line: next", "hint", 1)
        self.legend.set_hexpand(True)
        self.legend.set_wrap(True)
        input_heading.append(self.legend)
        content.append(input_heading)
        self.input_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, monospace=True,
                                       accepts_tab=False, top_margin=5, bottom_margin=5)
        self.input_view.add_css_class("typing-text")
        self.input_view.update_property([Gtk.AccessibleProperty.LABEL], ["Typing field"],)
        self.input_view.update_property([Gtk.AccessibleProperty.DESCRIPTION], ["Type the exercise exactly. The clock starts on your first character. Control R restarts. Tab moves to the next control."])
        self.input_buffer = self.input_view.get_buffer()
        self.input_buffer.set_enable_undo(False)
        self.input_error = self.input_buffer.create_tag("error", underline=Pango.Underline.ERROR)
        self.input_buffer.connect("insert-text", self._insert)
        self.input_buffer.connect("delete-range", self._delete)
        self.input_buffer.connect("changed", self._input_changed)
        self.input_buffer.connect("mark-set", self._cursor_changed)
        self.input_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                              min_content_height=100)
        self.input_scroll.set_size_request(-1, 100)
        self.input_scroll.set_child(self.input_view)
        self.input_scroll.add_css_class("exercise")
        content.append(self.input_scroll)
        footer = box(Gtk.Orientation.HORIZONTAL)
        self.help_label = label("Start typing to begin. Backspace to correct.", "hint")
        self.help_label.set_wrap(True)
        self.help_label.set_hexpand(True)
        footer.append(self.help_label)
        restart = Gtk.Button(label="Restart  Ctrl+R", action_name="win.restart")
        restart.set_tooltip_text("Start a fresh round (Ctrl+R)")
        footer.append(restart)
        content.append(footer)
        self.play_stack.add_named(self._wrap_page(content), "round")
        compact = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-height: 800px"))
        compact.add_setter(heading, "visible", False)
        compact.add_setter(content, "spacing", 10)
        for side in ("top", "bottom", "start", "end"):
            compact.add_setter(content, "margin-" + side, 16)
        for widget, height in ((self.target_scroll, 120), (self.input_scroll, 80)):
            compact.add_setter(widget, "min-content-height", height)
            compact.add_setter(widget, "height-request", height)
        compact.connect("apply", lambda *_: content.add_css_class("compact"))
        compact.connect("unapply", lambda *_: content.remove_css_class("compact"))
        self.add_breakpoint(compact)
        self.result_box = box(spacing=20)
        self.result_box.set_valign(Gtk.Align.CENTER)
        self.result_box.append(label("NICELY DONE", "eyebrow", .5))
        self.result_box.append(label("Round complete.", "result-title", .5))
        self.result_subtitle = label("", "dim-label", .5)
        self.result_subtitle.set_wrap(True)
        self.result_box.append(self.result_subtitle)
        self.best_label = label("", "best", .5)
        self.best_label.set_wrap(True)
        self.result_box.append(self.best_label)
        result_grid = Gtk.Grid(column_spacing=20, row_spacing=24, column_homogeneous=True)
        self.result_values = {}
        for i, (key, title) in enumerate((("wpm", "WORDS / MINUTE"), ("accuracy", "ACCURACY"),
                                          ("mistakes", "MISTAKES"), ("elapsed", "ELAPSED"))):
            item = box(spacing=4)
            value = label("", "hero", .5)
            item.append(value)
            item.append(label(title, "stat-label", .5))
            result_grid.attach(item, i % 2, i // 2, 1, 1)
            self.result_values[key] = value
        self.result_box.append(margins(result_grid, 20))
        self.result_detail = label("", "dim-label", .5)
        self.result_detail.set_wrap(True)
        self.result_box.append(self.result_detail)
        self.again = Gtk.Button(label="Play again", action_name="win.restart", halign=Gtk.Align.CENTER)
        self.again.add_css_class("suggested-action")
        self.again.add_css_class("primary-action")
        self.result_box.append(self.again)
        self.result_box.append(label("Ctrl+R for a fresh round", "hint", .5))
        self.play_stack.add_named(self._wrap_page(self.result_box), "results")
        self._dark_handler = Adw.StyleManager.get_default().connect("notify::dark", self._colors)
        self._colors()
        self._apply_font(self._stored_font())
        return self.play_stack

    def _stored_font(self):
        try:
            return max(16, min(36, int(self.store.get("font_size", "22"))))
        except (ValueError, TypeError):
            return 22

    def _colors(self, *_):
        dark = Adw.StyleManager.get_default().get_dark()
        self.correct_tag.set_property("foreground", "#8be0c0" if dark else "#126549")
        self.error_tag.set_property("foreground", "#ff9a9e" if dark else "#b01832")
        self.error_tag.set_property("background", "#54202c" if dark else "#ffe4e8")
        self.input_error.set_property("foreground", "#ff9a9e" if dark else "#b01832")
        self.current_tag.set_property("background", "#384c73" if dark else "#dbe7ff")

    def _set_categories(self, preferred="english"):
        self.category_keys = list(CATEGORIES) if self.mode.get_selected() == 1 else ["english", "german"]
        self.category.set_model(Gtk.StringList.new([CATEGORIES[key] for key in self.category_keys]))
        self.category.set_selected(self.category_keys.index(preferred) if preferred in self.category_keys else 0)

    def _mode_changed(self, *_):
        self._suppress = True
        old = self.round.config.category if self.round else "english"
        self._set_categories(old)
        self.duration.set_sensitive(self.mode.get_selected() == 0)
        self._suppress = False
        self._config_changed()

    def _config_changed(self, *_):
        if not self._suppress:
            self._new_round()

    def _restart(self):
        self.pages.set_visible_child_name("play")
        self._new_round()
        self.input_view.grab_focus()

    def _new_round(self):
        if self._result_idle:
            GLib.source_remove(self._result_idle)
            self._result_idle = 0
        # A restart can beat the results idle callback, or even the timer tick.
        # Preserve completed rounds; only unfinished rounds are discarded.
        if self.round and self.round.tick() and not self._saved:
            self._finish()
        config = Config(MODES[self.mode.get_selected()].lower(), self.category_keys[self.category.get_selected()],
                        [15, 30, 60][self.duration.get_selected()])
        try:
            self.store.set_many({"mode": config.mode, "category": config.category, "duration": config.duration})
        except Exception as error:
            self._storage_error(error)
        kwargs = {"clock": self.clock} if self.clock else {}
        self.round = self.exercises.create(config, **kwargs)
        self._saved = False
        self._finishing = False
        self.set_default_widget(None)
        self._suppress = True
        self.input_buffer.set_text("")
        self._suppress = False
        self.input_view.set_editable(True)
        self.target_buffer.set_text(self.round.target)
        if not hasattr(self, "target_mark"):
            self.target_mark = self.target_buffer.create_mark(None, self.target_buffer.get_start_iter(), False)
        self.play_stack.set_visible_child_name("round")
        self.state_label.set_label("Ready when you are")
        is_code = config.category in {"python", "typescript"}
        self.target_view.set_wrap_mode(Gtk.WrapMode.NONE if is_code else Gtk.WrapMode.WORD_CHAR)
        self.input_view.set_wrap_mode(Gtk.WrapMode.NONE if is_code else Gtk.WrapMode.WORD_CHAR)
        policy = Gtk.PolicyType.AUTOMATIC if is_code else Gtk.PolicyType.NEVER
        self.target_scroll.set_policy(policy, Gtk.PolicyType.AUTOMATIC)
        self.input_scroll.set_policy(policy, Gtk.PolicyType.AUTOMATIC)
        self.help_label.set_label("Code: four spaces per indent; Enter for a new line. Tab moves focus." if is_code
                                 else "Correct word + Space = +1s. Each position earns once." if config.mode == "survival"
                                 else "Start typing to begin. Backspace to correct.")
        self._render()

    def _storage_error(self, error):
        self.toast_overlay.add_toast(Adw.Toast(title=f"Could not save locally: {error}"))

    def _insert(self, buffer, location, text, length):
        if self._suppress:
            return
        if not self.round.edit(location.get_offset(), location.get_offset(), text):
            buffer.stop_emission_by_name("insert-text")
        if self.round.finished:
            self._queue_finish()

    def _delete(self, buffer, start, end):
        if self._suppress:
            return
        if not self.round.edit(start.get_offset(), end.get_offset(), ""):
            buffer.stop_emission_by_name("delete-range")
        if self.round.finished:
            self._queue_finish()

    def _input_changed(self, *_):
        if not self._suppress:
            self._render()

    def _cursor_changed(self, buffer, location, mark):
        if self.round and not self._suppress and mark.get_name() == "insert":
            self._highlight_cursor(location.get_offset())

    def _highlight_cursor(self, offset):
        offset = min(offset, len(self.round.target))
        self.target_buffer.remove_tag(self.current_tag, self.target_buffer.get_start_iter(), self.target_buffer.get_end_iter())
        start = self.target_buffer.get_iter_at_offset(offset)
        end = self.target_buffer.get_iter_at_offset(min(offset + 1, len(self.round.target)))
        self.target_buffer.apply_tag(self.current_tag, start, end)
        self.target_buffer.move_mark(self.target_mark, start)
        # Coalesce edits, then scroll after layout without a trailing animation.
        if not self._scroll_idle:
            self._scroll_idle = GLib.idle_add(self._ensure_cursor_visible)

    def _ensure_cursor_visible(self):
        self._scroll_idle = 0
        current = self.target_buffer.get_iter_at_mark(self.target_mark)
        rect = self.target_view.get_iter_location(current)
        visible = self.target_view.get_visible_rect()
        for adjustment, position, size, view_start, view_size in (
            (self.target_scroll.get_vadjustment(), rect.y, rect.height, visible.y, visible.height),
            (self.target_scroll.get_hadjustment(), rect.x, max(1, rect.width), visible.x, visible.width),
        ):
            padding = 10
            delta = 0
            if position < view_start + padding:
                delta = position - view_start - padding
            elif position + size > view_start + view_size - padding:
                delta = position + size - view_start - view_size + padding
            if delta:
                adjustment.set_value(adjustment.get_value() + delta)
        self.input_view.scroll_mark_onscreen(self.input_buffer.get_insert())
        return GLib.SOURCE_REMOVE

    def _render(self):
        if self.round is None:
            return
        if self.target_buffer.get_char_count() != len(self.round.target):
            self.target_buffer.set_text(self.round.target)
        start, end = self.target_buffer.get_bounds()
        self.target_buffer.remove_tag(self.correct_tag, start, end)
        self.target_buffer.remove_tag(self.error_tag, start, end)
        self.input_buffer.remove_tag(self.input_error, *self.input_buffer.get_bounds())
        # Apply contiguous runs instead of a separate GTK operation per character.
        text = self.round.text
        run_start = 0
        previous = None
        for i in range(min(len(text), len(self.round.target)) + 1):
            correct = text[i] == self.round.target[i] if i < min(len(text), len(self.round.target)) else None
            if correct != previous:
                if previous is not None:
                    self.target_buffer.apply_tag(self.correct_tag if previous else self.error_tag,
                                                 self.target_buffer.get_iter_at_offset(run_start),
                                                 self.target_buffer.get_iter_at_offset(i))
                    if not previous:
                        self.input_buffer.apply_tag(self.input_error, self.input_buffer.get_iter_at_offset(run_start),
                                                    self.input_buffer.get_iter_at_offset(i))
                previous = correct
                run_start = i
        if len(text) > len(self.round.target):
            self.input_buffer.apply_tag(self.input_error, self.input_buffer.get_iter_at_offset(len(self.round.target)),
                                        self.input_buffer.get_end_iter())
        cursor = self.input_buffer.get_iter_at_mark(self.input_buffer.get_insert()).get_offset()
        self._highlight_cursor(cursor)
        self._update_stats()

    def _update_stats(self):
        score = self.round.score()
        # A fraction-of-a-second sample has no useful rate and can be enormous.
        self.metrics["wpm"].set_label("—" if self.round.started_at is not None and score.elapsed < 1 else f"{score.wpm:.0f}")
        self.metrics["accuracy"].set_label(f"{score.accuracy:.0f}%")
        self.metrics["mistakes"].set_label(str(score.mistakes))
        remaining = self.round.remaining()
        self.metrics["clock"].set_label(f"{remaining:.1f}s" if remaining is not None else f"{score.elapsed:.0f}s")
        if self.round.started_at is not None and not self.round.finished:
            self.state_label.set_label("Keep your rhythm")
        cursor = min(self.input_buffer.get_iter_at_mark(self.input_buffer.get_insert()).get_offset(), len(self.round.target) - 1)
        character = self.round.target[cursor]
        next_key = {" ": "Space", "\n": "Enter", "\t": "Tab"}.get(character, f"“{character}”")
        next_hint = f"Next: {next_key}"
        if self.round.config.mode == "practice":
            self.progress_label.set_label(f"{next_hint} · {min(len(self.round.text), len(self.round.target))}/{len(self.round.target)}")
        elif self.round.config.mode == "survival":
            self.progress_label.set_label(f"{next_hint} · +{score.bonus_seconds}s")
        else:
            self.progress_label.set_label(next_hint if self.round.started_at is not None else "Clock starts on your first character")

    def _tick(self):
        if self.round and not self._finishing:
            if self.round.tick():
                self._queue_finish()
            else:
                self._update_stats()
        return GLib.SOURCE_CONTINUE

    def _queue_finish(self):
        if not self._finishing:
            self._finishing = True
            self.input_view.set_editable(False)
            self._result_idle = GLib.idle_add(self._finish)

    def _finish(self):
        self._result_idle = 0
        if self._saved:
            return GLib.SOURCE_REMOVE
        score = self.round.score()
        self._saved = True
        new_best = False
        saved = True
        try:
            new_best = self.store.save(score)
        except Exception as error:
            saved = False
            self._storage_error(error)
        self.result_values["wpm"].set_label(f"{score.wpm:.1f}")
        self.result_values["accuracy"].set_label(f"{score.accuracy:.1f}%")
        self.result_values["mistakes"].set_label(str(score.mistakes))
        self.result_values["elapsed"].set_label(f"{score.elapsed:.1f}s")
        duration = f" · {score.duration}s" if score.mode == "sprint" else ""
        self.result_subtitle.set_label(f"{score.mode.title()} · {CATEGORIES[score.category]}{duration}")
        self.best_label.set_label("New personal best!" if new_best else ("Saved to your history" if saved else "Result could not be saved"))
        self.result_detail.set_label(f"{score.correct_characters} matched characters · {score.correct_attempts} correct / {score.attempts} attempts\n"
                                     "Corrected mistakes stay in your accuracy and mistake count.")
        self.play_stack.set_visible_child_name("results")
        self._load_history()
        if self.pages.get_visible_child_name() == "play":
            self.set_default_widget(self.again)
            self.again.grab_focus()
        return GLib.SOURCE_REMOVE

    def _build_history(self):
        content = box(spacing=16)
        content.append(label("Your progress.", "hero"))
        subtitle = label("Every finished round, saved on this device.", "dim-label")
        subtitle.set_wrap(True)
        content.append(subtitle)
        self.history_filter = Gtk.DropDown.new_from_strings(["All modes"] + MODES)
        self.history_filter.set_halign(Gtk.Align.START)
        self.history_filter.update_property([Gtk.AccessibleProperty.LABEL], ["Filter history by mode"])
        self.history_filter.connect("notify::selected", lambda *_: self._load_history())
        content.append(self.history_filter)
        self.history_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.history_list.add_css_class("boxed-list")
        content.append(self.history_list)
        self.history_empty = Adw.StatusPage(title="Your first round awaits", description="Finish a round to see your progress here.",
                                            icon_name="document-open-recent-symbolic")
        content.append(self.history_empty)
        self._load_history()
        return self._wrap_page(content)

    def _load_history(self):
        if not hasattr(self, "history_list"):
            return
        child = self.history_list.get_first_child()
        while child:
            following = child.get_next_sibling()
            self.history_list.remove(child)
            child = following
        selected = self.history_filter.get_selected()
        mode = MODES[selected - 1].lower() if selected else None
        rows = self.store.history(mode)
        self.history_empty.set_visible(not rows)
        self.history_list.set_visible(bool(rows))
        from datetime import datetime
        for row in rows:
            duration = f" · {row['duration']}s" if row["mode"] == "sprint" else ""
            date = datetime.fromisoformat(row["created_at"]).astimezone().strftime("%d %b %Y, %H:%M")
            action = Adw.ActionRow(title=f"{row['mode'].title()} · {CATEGORIES.get(row['category'], row['category'])}{duration}",
                                   subtitle=f"{date} · {row['accuracy']:.1f}% accuracy · {row['mistakes']} mistakes · {row['elapsed']:.1f}s")
            action.add_suffix(label(f"{row['wpm']:.1f} WPM", "heading"))
            self.history_list.append(action)

    def _build_settings(self):
        content = box(spacing=20)
        content.append(label("Make room for focus.", "hero"))
        group = Adw.PreferencesGroup(title="Typing text", description="The exercise and input share the same font size.")
        row = Adw.ActionRow(title="Text size", subtitle="16–36 pixels")
        self.font_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 16, 36, 1)
        self.font_scale.set_size_request(190, -1)
        self.font_scale.set_draw_value(True)
        self.font_scale.set_digits(0)
        self.font_scale.set_value(self._stored_font())
        self.font_scale.update_property([Gtk.AccessibleProperty.LABEL], ["Typing text size in pixels"])
        self.font_scale.connect("value-changed", self._font_changed)
        row.add_suffix(self.font_scale)
        group.add(row)
        content.append(group)
        group = Adw.PreferencesGroup(title="At home on your desktop")
        group.add(Adw.ActionRow(title="Appearance", subtitle="Follows your system’s light and dark preference"))
        group.add(Adw.ActionRow(title="Always offline", subtitle="Exercises, settings, and history stay on this device"))
        shortcuts = Adw.ActionRow(title="Keyboard shortcuts", subtitle="Ctrl+R: restart · Ctrl+1/2/3: Play / History / Settings\nTab / Shift+Tab: move focus · Space: activate a button")
        group.add(shortcuts)
        content.append(group)
        scoring = label("WPM uses the matching characters in your final text, divided by five and by elapsed minutes. "
                        "Accuracy counts every character-entry attempt. Backspace does not count. "
                        "Practice ends when you have entered the passage length; mistakes are allowed. "
                        "In Survival, complete a correct word and its following space to earn one second. "
                        "Leaving Play keeps the clock running. Restarting discards an unfinished round.", "dim-label")
        scoring.set_wrap(True)
        content.append(scoring)
        return self._wrap_page(content)

    def _apply_font(self, value):
        self._font_provider.load_from_string(f".typing-text {{ font-family: monospace; font-size: {int(value)}px; }}")

    def _font_changed(self, scale):
        value = round(scale.get_value())
        self._apply_font(value)
        try:
            self.store.set_many({"font_size": value})
        except Exception as error:
            self._storage_error(error)

    def _page_changed(self, *_):
        page = self.pages.get_visible_child_name()
        self.set_default_widget(self.again if page == "play" and self.round and self.round.finished else None)
        if page == "history":
            self._load_history()
        elif page == "play":
            (self.again if self.round and self.round.finished else self.input_view).grab_focus()

    def _on_close(self, *_):
        if self._result_idle:
            GLib.source_remove(self._result_idle)
            self._result_idle = 0
        # A timeout at close still constitutes a completed round.
        if self.round and self.round.tick() and not self._saved:
            self._finish()
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0
        if self._scroll_idle:
            GLib.source_remove(self._scroll_idle)
            self._scroll_idle = 0
        self.store.close()
        Adw.StyleManager.get_default().disconnect(self._dark_handler)
        Gtk.StyleContext.remove_provider_for_display(self.get_display(), self._font_provider)
        Gtk.StyleContext.remove_provider_for_display(self.get_display(), self._provider)
        return False


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = Window(self)
        window.present()
        if not window.round.finished:
            window.input_view.grab_focus()


def main():
    import sys
    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        print("TypeSprint needs a graphical display. Launch it from your GNOME desktop session.", file=sys.stderr)
        raise SystemExit(1)
    app = Application()
    raise SystemExit(app.run(sys.argv))
