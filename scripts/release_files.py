"""Explicit release inputs, shared by archive builds and GitHub staging."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOT_FILES = {'index.html', '.nojekyll', '.gitignore', '.gitattributes', 'README.md', 'VERIFICATION.md', 'CONTRIBUTING.md', 'LICENSE'}
DIRECTORIES = {'typesprint', 'tests', 'scripts', 'packaging', 'web', '.github', 'docs'}
SKIP = {'__pycache__', 'node_modules', 'dist', 'artifacts', 'test-results', 'playwright-report', '.git', '.agents', '.aws', '.codex'}


def release_files(root=ROOT):
    for name in sorted(ROOT_FILES):
        path = root / name
        if path.is_file() and not path.is_symlink():
            yield path
    for name in sorted(DIRECTORIES):
        base = root / name
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            relative = path.relative_to(root)
            if any(part in SKIP or part.startswith('.env') for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f'Release input must not be a symlink: {relative}')
            if path.is_file() and path.suffix not in {'.pyc', '.pyo', '.sqlite3', '.db', '.log'}:
                yield path
