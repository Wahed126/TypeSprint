#!/usr/bin/python3
"""Install a per-user desktop launcher; the source directory stays in place."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess

APP_ID = "io.github.typesprint.TypeSprint"
ROOT = Path(__file__).resolve().parent.parent


def desktop_quote(value):
    # Desktop Exec syntax differs from shell syntax; % is a field-code escape.
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, help="Alternate installation root (default: ~/.local)")
    args = parser.parse_args()
    prefix = (args.prefix or Path.home() / ".local").expanduser().resolve()
    data = prefix / "share" if args.prefix else Path(os.environ.get("XDG_DATA_HOME", prefix / "share"))
    launcher = prefix / "bin" / "typesprint"
    desktop = data / "applications" / f"{APP_ID}.desktop"
    icon = data / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"
    for path in (launcher, desktop, icon):
        path.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(f"#!/bin/sh\ncd -- {shlex.quote(str(ROOT))} || exit 1\nexec /usr/bin/python3 -m typesprint \"$@\"\n")
    launcher.chmod(0o755)
    content = (ROOT / "packaging" / f"{APP_ID}.desktop").read_text()
    content = content.replace("Exec=typesprint", "Exec=" + desktop_quote(launcher))
    desktop.write_text(content)
    shutil.copyfile(ROOT / "packaging" / "icons" / f"{APP_ID}.svg", icon)
    for command in (["update-desktop-database", str(desktop.parent)],
                    ["gtk4-update-icon-cache", "-f", "-t", str(data / "icons" / "hicolor")]):
        if shutil.which(command[0]):
            subprocess.run(command, check=False)
    print(f"Installed {desktop}\nLauncher: {launcher}\nKeep the source project at {ROOT}.")


if __name__ == "__main__":
    main()
