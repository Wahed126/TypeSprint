# Contributing

Use focused changes and explain the behavior they change. Keep Python timing
and scoring independent of GTK and keep web rules independent of the DOM.
A rule change should update both engines and their controlled-clock tests.

## Desktop

Install the Ubuntu runtime dependencies from the README. Run:

```bash
/usr/bin/python3 -m unittest tests.test_engine tests.test_storage tests.test_build -v
TYPESPRINT_GUI_TESTS=1 /usr/bin/python3 -m unittest tests.test_gtk -v
```

The package test needs `dpkg-dev`; GTK integration needs a graphical session or
Xvfb. Use temporary databases when testing so your own history is preserved.

## Web

```bash
cd web
npm ci
npm test
npx playwright install --with-deps chromium
npm run test:browser
npm run build
```

Keep the lockfile committed. The delivered site must stay independent of
node_modules, servers, and third-party APIs. Preserve normal input composition,
keyboard focus, text underlines, high contrast, and reduced-motion support.

## Shared content and release checks

```bash
/usr/bin/python3 scripts/sync-web-data.py
/usr/bin/python3 scripts/sync-web-data.py --check
/usr/bin/python3 scripts/build-desktop.py
```

Do not commit databases, credentials, `.env` files, browser profiles, caches,
node_modules, generated builds, or local screenshots. CI tests both versions
and provides build artifacts. Document checks actually run and any unverified
behavior in pull requests. Do not claim a passing hosted workflow before it runs.

A project license has not yet been selected. Coordinate licensing with the owner
before submitting work intended for public redistribution.
