#!/usr/bin/python3
"""Keep the standalone web exercises identical to the desktop's bundled content."""
import argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
source = (ROOT / 'typesprint/data/exercises.json').read_bytes()
target = ROOT / 'web/data/exercises.json'
if args.check:
    if not target.exists() or target.read_bytes() != source:
        raise SystemExit('Web exercises differ. Run: python3 scripts/sync-web-data.py')
    print('Desktop and web exercises match')
else:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)
    print('Synced web/data/exercises.json')
