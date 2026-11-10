# TypeSprint for the web

This directory contains the standalone browser version of TypeSprint. It runs
Sprint (15/30/60 seconds), untimed Practice (English, German, Python, TypeScript),
and Survival (30 seconds plus one second for each correctly committed word
position). Scoring and text content match the desktop version.

## Play online

**https://wahed126.github.io/TypeSprint/web/** opens the playable game.
The repository-root Pages address redirects here when publishing from `main`.

## Build and serve

Node.js 22+ and Python 3 are sufficient; no npm packages are needed at runtime or
to build:

```bash
cd web
npm run build
npm start
```

Open http://127.0.0.1:4173. Deploy the contents of `dist/` to a static host.
Relative URLs support a GitHub Pages project path. Do not open `index.html`
through `file://`; modules and exercise loading need HTTP.

The service worker caches the complete built app after a successful first visit
over HTTPS or localhost. Later visits can work offline. Close old tabs and
reopen to activate a new deployment. Cache versions are derived from the game assets and cache names are scoped to
this app's deployment path. The build generates both `dist/sw.js` and the tracked
`sw.js` from `sw-template.js`, so direct branch-hosted play has the same offline
behavior. Run the build and commit the generated `sw.js` when changing assets;
CI verifies that it is current.

## Results feedback

After each round, a coaching card uses speed, accuracy, corrected mistakes and
elapsed time to suggest a next step. Very short samples get a warm-up message;
code gets gentler speed thresholds and advice about indentation and punctuation.
The desktop and web use the same catalog and examples. Messages are bundled and
continue to work offline.

## Controls and data

The input has initial focus. Type to start the timer. Backspace and selection
replacement correct text; corrected mistakes stay in accuracy. Ctrl+R (Cmd+R on
macOS) restarts. Tab moves focus, including in code; use four spaces for
indentation. At round end, results keep focus without activating a button. Click Play again
or press Tab then Enter/Space when ready. Browser-toolbar reload or
Ctrl+Shift+R refreshes the page.

History and settings are stored in localStorage under `typesprint.v1`. They are
separate from desktop SQLite data and are never uploaded. Clearing browser site
data removes this history. Restricted or full storage is reported in the UI;
results then remain in memory only for the current visit.

## Tests

```bash
npm test
npm ci
npx playwright install --with-deps chromium
npm run test:browser
```

`npm test` uses only Node's built-in runner. Browser tests use the locked
Playwright development dependency and automatically build/serve `dist/`.
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chrome` uses an existing browser.
No development dependencies are copied into the static build.

After changing desktop exercises or the feedback catalog, run from the repository root:

```bash
python3 scripts/sync-web-data.py
python3 scripts/sync-web-data.py --check
```

The root [README](../README.md) documents scoring, CI artifacts, optional GitHub
Pages deployment, desktop setup, and contribution instructions.
