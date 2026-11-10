#!/usr/bin/python3
"""Keep standalone web exercises and coaching content identical to the desktop."""
import argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
for name in ('exercises.json', 'feedback.json'):
    source = (ROOT / 'typesprint/data' / name).read_bytes()
    target = ROOT / 'web/data' / name
    if args.check:
        if not target.exists() or target.read_bytes() != source:
            raise SystemExit(f'Web {name} differs. Run: python3 scripts/sync-web-data.py')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source)
print('Desktop and web content match' if args.check else 'Synced exercises and feedback')
