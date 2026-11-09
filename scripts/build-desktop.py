#!/usr/bin/python3
"""Build a portable source archive and an Ubuntu .deb using stdlib + dpkg-deb."""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from release_files import ROOT, release_files


def version():
    match = re.search(r'__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"', (ROOT / 'typesprint/__init__.py').read_text())
    if not match:
        raise ValueError('Expected a semantic version in typesprint/__init__.py')
    return match[1]


def source_archive(output, release_version):
    archive = output / f'typesprint-{release_version}-source.tar.gz'
    with archive.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for path in release_files():
                info = tar.gettarinfo(str(path), arcname=f'typesprint-{release_version}/{path.relative_to(ROOT)}')
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                info.mode = 0o644
                with path.open('rb') as data:
                    tar.addfile(info, data)
    return archive


def deb_package(output, release_version):
    if not shutil.which('dpkg-deb'):
        raise SystemExit('dpkg-deb is required. On Ubuntu: sudo apt install dpkg-dev')
    package = output / f'typesprint_{release_version}_all.deb'
    with tempfile.TemporaryDirectory(prefix='typesprint-deb-') as temp:
        stage = Path(temp)
        for path in release_files():
            relative = path.relative_to(ROOT)
            if relative.parts[0] in {'typesprint', 'packaging'}:
                dest = stage / 'usr/share/typesprint' / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
        binary = stage / 'usr/bin/typesprint'
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text('#!/bin/sh\ncd /usr/share/typesprint || exit 1\nexec /usr/bin/python3 -m typesprint "$@"\n')
        binary.chmod(0o755)
        app_id = 'io.github.typesprint.TypeSprint'
        desktop = stage / 'usr/share/applications' / f'{app_id}.desktop'
        desktop.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'packaging' / desktop.name, desktop)
        icon = stage / 'usr/share/icons/hicolor/scalable/apps' / f'{app_id}.svg'
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'packaging/icons' / icon.name, icon)
        docs = stage / 'usr/share/doc/typesprint'
        docs.mkdir(parents=True)
        shutil.copyfile(ROOT / 'README.md', docs / 'README.md')
        control = stage / 'DEBIAN/control'
        control.parent.mkdir()
        control.write_text(f'''Package: typesprint
Version: {release_version}
Section: games
Priority: optional
Architecture: all
Maintainer: TypeSprint contributors <noreply@users.noreply.github.com>
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0 (>= 4.12), gir1.2-adw-1 (>= 1.4), adwaita-icon-theme
Description: Offline native typing game for GNOME
 Sprint, Practice, and Survival with local history and keyboard-first controls.
''')
        for path in stage.rglob('*'):
            if path.is_dir(): path.chmod(0o755)
            elif path != binary: path.chmod(0o644)
            os.utime(path, (0, 0))
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(stage), str(package)],
                       check=True, env={**os.environ, 'SOURCE_DATE_EPOCH': '0'})
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    release_version = version()
    artifacts = [source_archive(output, release_version), deb_package(output, release_version)]
    checksums = '\n'.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}' for path in artifacts) + '\n'
    (output / 'SHA256SUMS').write_text(checksums)
    for path in artifacts: print(f'Built {path}')


if __name__ == '__main__':
    main()
