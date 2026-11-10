"""Check actual distributable contents, not implementation details."""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which('dpkg-deb'), 'dpkg-deb is needed for Ubuntu package checks')
class BuildTests(unittest.TestCase):
    def test_distributables_include_runtime_assets_and_exclude_local_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            subprocess.run([sys.executable, 'scripts/build-desktop.py', '--output', str(out)], cwd=ROOT, check=True, capture_output=True)
            archive = next(out.glob('*-source.tar.gz'))
            with tarfile.open(archive) as tar:
                names = [name.split('/', 1)[1] for name in tar.getnames()]
            for path in ['index.html', '.nojekyll', 'web/sw-template.js', 'web/sw.js', 'typesprint/data/exercises.json', 'typesprint/data/feedback.json', 'web/data/feedback.json', 'web/feedback.js', 'typesprint/app.py', 'web/index.html', 'scripts/install-desktop.py', '.github/workflows/ci.yml']:
                self.assertIn(path, names)
            for name in names:
                self.assertFalse(set(Path(name).parts) & {'node_modules', '__pycache__', '.git', '.aws', '.codex', '.agents', 'artifacts', 'dist'})
                self.assertFalse(name.endswith('.sqlite3'))
            package = next(out.glob('*.deb'))
            subprocess.run(['dpkg-deb', '-x', str(package), str(out / 'unpacked')], check=True)
            installed = out / 'unpacked'
            self.assertTrue((installed / 'usr/share/typesprint/typesprint/data/exercises.json').is_file())
            self.assertTrue((installed / 'usr/share/typesprint/typesprint/data/feedback.json').is_file())
            self.assertTrue((installed / 'usr/share/applications/io.github.typesprint.TypeSprint.desktop').is_file())
            self.assertTrue((installed / 'usr/share/icons/hicolor/scalable/apps/io.github.typesprint.TypeSprint.svg').is_file())
            self.assertTrue((installed / 'usr/bin/typesprint').stat().st_mode & 0o111)
            info = subprocess.check_output(['dpkg-deb', '-f', str(package), 'Depends'], text=True)
            self.assertIn('gir1.2-gtk-4.0', info)
            self.assertIn('gir1.2-adw-1', info)
