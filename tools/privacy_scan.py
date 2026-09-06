#!/usr/bin/env python3
"""Refuse to let private names, ids or paths into the public repo.

The denylist lives OUTSIDE the repo (default: ~/.config/family-tree-kit/denylist.txt, one
term per line, case-insensitive; lines starting with # are comments). Build it from the
real tree: every given-name+surname pair, every surname that is not a dictionary word or a
place, every xref that matters, home directory paths, platform tree ids. Terms match on
word boundaries, so keep them at least four characters or expect noise. Run this as a pre-commit hook or before every push.

Exit 1 with the offending file:line on any hit. Fixture and doc files are scanned too,
because "it is only a doc" is how the first leak happens.

usage: python3 tools/privacy_scan.py [--denylist PATH] [paths...]   (default: all git-tracked files)
"""
import argparse
import os
import re
import subprocess
import sys


def tracked_files():
    out = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True).stdout
    return [p for p in out.split('\n') if p]


def load_denylist(path):
    terms = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith('#'):
                terms.append(line)
    return terms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--denylist', default=os.path.expanduser('~/.config/family-tree-kit/denylist.txt'))
    ap.add_argument('paths', nargs='*')
    a = ap.parse_args()
    if not os.path.exists(a.denylist):
        sys.exit(f'no denylist at {a.denylist}; refusing to pass an unscanned tree')
    terms = load_denylist(a.denylist)
    pat = re.compile(r'\b(?:' + '|'.join(re.escape(t) for t in terms) + r')\b', re.I)
    files = a.paths or tracked_files()
    hits = 0
    for f in files:
        if not os.path.isfile(f):
            continue
        with open(f, encoding='utf-8', errors='replace') as fh:
            for n, line in enumerate(fh, 1):
                m = pat.search(line)
                if m:
                    hits += 1
                    print(f'{f}:{n}: "{m.group(0)}"')
    print(f'{len(files)} files scanned against {len(terms)} terms: {hits} hit(s)')
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main()
