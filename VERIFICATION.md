# Verification — 8 November 2026

Environment: Ubuntu 26.04.1 LTS; system Python 3.14.4; GTK 4.22.4;
libadwaita 1.9.1; PyGObject 3.56.2. Graphical checks used the available GNOME
Wayland session. Tests used temporary SQLite databases, not personal history.

## Automated tests

```bash
GSETTINGS_BACKEND=memory G_DEBUG=fatal-criticals \
  PYTHONWARNINGS=ignore::DeprecationWarning TYPESPRINT_GUI_TESTS=1 \
  /usr/bin/python3 -m unittest discover -v
```

**39 tests passed**: 32 engine/storage tests and 7 native GTK integration tests.
GTK critical errors were fatal. The warning filter suppresses deprecations in
Ubuntu's PyGObject asyncio integration on Python 3.14.

Coverage includes:

- No timer before first text; a wrong first character starts it too.
- Input just before the deadline accepted; input at the deadline rejected;
  delayed callbacks preserve the exact elapsed time.
- Typo correction retains mistake attempts; WPM uses the final matching text.
- Unicode, native buffer edits, selection replacement, code indentation and
  line breaks, and error/correct/current text tags.
- Restart during a round clears input, attempts, timing, and focus; unfinished
  rounds do not enter History. A restart at the deadline or before the results
  callback preserves the completed session.
- Survival requires the correct word and separator, cannot award after expiry,
  and awards once per position even after deletion and retyping. Repeated word
  text at different positions can earn separate bonuses.
- Timed word supply grows, including for a large insertion.
- Best records stay within mode/category/Sprint-duration groups.
- Settings persist; completed sessions are readable from a fresh Python process.
- GTK results, Play again focus and default activation, mode filtering, History after reopening,
  code whitespace, 36-pixel text, and fixed exercise coordinates with the active
  line visible at small and large sizes.

## Full real-time graphical round

```bash
GSETTINGS_BACKEND=memory G_DEBUG=fatal-criticals \
  PYTHONWARNINGS=ignore::DeprecationWarning \
  /usr/bin/python3 scripts/check-desktop.py
```

Passed a real 15-second Sprint using native GTK buffer edits at intervals,
including correction, restart, focus traversal, page actions, result saving,
focused Play again, and starting the next round. The test then relaunched the UI
in a **fresh application process** and verified that the completed session was
visible on History.

Inspected snapshots at **560 × 640** in light mode and **1200 × 928** in dark
mode (the desktop constrained the requested 950-pixel height). The compact
layout keeps reference and input visible together, and stats do not move the
exercise. The GTK suite also checks code at 36 pixels at both window sizes.
Snapshots are generated in `artifacts/` by the command above when GTK exposes a
rendered frame. Some later runs could not capture an occluded window; the script
reports skipped captures and continues the independent geometry and game checks.

## Packaging and launch

```bash
/usr/bin/python3 -m compileall -q typesprint tests scripts
/usr/bin/python3 scripts/install-desktop.py --prefix '/tmp/TypeSprint desktop test'
desktop-file-validate '/tmp/TypeSprint desktop test/share/applications/io.github.typesprint.TypeSprint.desktop'
sh -n '/tmp/TypeSprint desktop test/bin/typesprint'
```

All passed. The disposable installation exercised paths containing spaces. The
installed launcher's `--help` worked from `/tmp`, and launching it with isolated
`XDG_DATA_HOME` stayed running without diagnostics until the two-second smoke
test timeout. A launch without a display produces a concise message and exit
status 1.

## Still needs human verification

Physical key events and real IME composition could not be verified: synthetic
X11 key injection did not reach GTK in this desktop session. The tests verify
GTK text insertion (including `äöüß`), deletion, focus traversal, shortcut
registration, actions, and button activation, but do not claim hardware-key
coverage. A physical-key check of Ctrl+R, Tab, Enter/Space on Play again, and a
German input method remains advisable.

Actual GNOME app-grid launch after a per-user installation, system theme
switching through GNOME Settings, and Orca/screen-reader narration were not
verified. Light/dark rendering was exercised through libadwaita's style manager.
The project does not install into the user's app menu automatically; use the
README's desktop setup command.


# GitHub and web verification — 9 November 2026

The existing desktop test record above is retained. This update adds the
standalone web version, native distribution builds, and GitHub Actions workflows.

## Checks performed

- **40 Python tests passed** with `TYPESPRINT_GUI_TESTS=1` in the graphical
  session: 32 engine/storage tests, 7 GTK integration tests, and 1 new package
  inspection test. `G_DEBUG=fatal-criticals` remained enabled.
- **24 Node tests passed** for the browser's DOM-independent engine and
  localStorage adapter, including first input, exact deadlines, correction,
  selection replacement, Unicode code points, code whitespace, Survival bonuses,
  record grouping, storage failures, and reload persistence.
- **9 Playwright tests passed** in installed Google Chrome 157 using Playwright
  1.65.0. Tests ran the built static site under `/TypeSprint/`, a repository-style
  URL path, and checked for uncaught browser errors.
- Browser tests covered native text input, Backspace, Ctrl+R, Enter on Play again,
  complete timed rounds, identical-character selection replacement, history after
  page reload, mode filtering, synthetic German composition events, literal code,
  saved font size, Tab focus traversal, fixed exercise geometry, active-character
  visibility at 560 × 640 and 1280 × 950, light/dark rendering, and offline loading
  after service-worker installation. Screenshots were visually inspected.
- Built `dist/typesprint_1.0.0_all.deb`, a clean source archive, and SHA-256
  checksums. Inspected package metadata and extracted runtime assets. The package
  test checks that private workspace directories, caches, databases, generated
  builds, and node_modules are absent from the source distribution.
- Built `web/dist/` using only Node standard-library tooling. Verified identical
  desktop/web exercise bundles, Python compilation, and valid workflow YAML.

Commands used for the web checks:

```bash
cd web
npm test
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/opt/google/chrome/chrome npm run test:browser
npm run build
```

The browser runner starts and stops its own temporary HTTP server. Its clock is
controlled for deterministic deadline checks; the earlier desktop real-time round
remains documented above. Browser input was tested through Playwright keyboard
and text APIs; composition was simulated with composition/input events.

## Hosting and remaining limits

The workflows are prepared locally; a hosted GitHub Actions run and GitHub Pages
deployment cannot be verified until a destination repository is available and
the project is pushed. The connected GitHub tool has no repository-creation
capability. A request for the destination repository URL was sent during this
work. No GitHub publication or live website deployment is claimed by these local
checks.

Chrome was tested; Firefox, Safari, physical IME input, Orca, and mobile hardware
were not. The CI definition uses Playwright's downloaded Chromium and an Ubuntu
26.04 container with Xvfb; this local run used installed Chrome and the available
GNOME session. Source-based and `.deb` builds were inspected, but the new `.deb`
was not installed over the user's existing source installation.

# Playable Pages entry point — 10 November 2026

The repository-root Pages deployment was displaying README documentation. Added
`index.html` to open the game in `web/` and `.nojekyll` to publish its static
assets unchanged. The standalone GitHub Actions artifact still opens the game
directly at its deployment root. The README now links straight to the game.

The browser build generates the tracked `web/sw.js` and artifact `dist/sw.js`
from `sw-template.js`, using the same content hash. This gives branch-hosted and
artifact-hosted play the same versioned offline behavior. CI checks that the
tracked generated worker is current.

Local checks for this change:

- **10 Playwright browser tests passed**, including a new repository-root server
  that reproduces branch-based Pages publishing and verifies redirect, typing,
  completed Practice, saved History, and offline reload.
- The package inspection test passed and now checks that source distributions
  include the root entry point, `.nojekyll`, worker template, and generated worker.
- The web build passed; source and artifact service workers match byte for byte.

These checks use temporary browser storage and local servers. Hosted deployment
and live-site checks are reported separately at handoff.
