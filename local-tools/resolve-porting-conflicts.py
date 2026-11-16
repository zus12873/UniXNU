#!/usr/bin/env python3
"""Resolve merge conflicts in a device repository's porting.toml key by key (integration of other branches, 2026-11-15).

    resolve-porting-conflicts.py REPO [--file porting.toml] [--base COMMIT] [--dry-run]

Run during a merge that stopped on porting.toml. The record keeps each area's lists on one line (`findings = [...]`), so two
branches that both add a finding conflict on the whole line. For every conflict hunk whose lines are all `key = value` of one
area, this takes the three versions of that key from the merge's index stages (1 base, 2 ours, 3 theirs):

- only one side changed it from the base: that side's value;
- both changed a list: theirs, then the items ours added that theirs does not hold (nothing is dropped that either side added);
- both changed a scalar to different values: left as a conflict.

Hunks with table headers ([[area.evidence]]) or keys outside one area are left untouched and listed, for a hand merge. The file
is rewritten only when every hunk it touched parsed back; the result is checked with tomllib. Lists are written as one-line
arrays of basic strings, as the record stores them.
"""
import argparse
import json
import re
import subprocess
import sys
import tomllib

HUNK = re.compile(r'^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n', re.S | re.M)
KEY = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*) = ')
AREA_ID = re.compile(r'^id = "([^"]+)"$', re.M)


def stage(repo, number, path):
    return tomllib.loads(subprocess.run(['git', '-C', repo, 'show', f':{number}:{path}'], check=True, capture_output=True,
                                        text=True).stdout)


def areas(record):
    return {a['id']: a for a in record.get('area', [])}


def render(key, value):
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return f'{key} = ' + json.dumps(value, ensure_ascii=False) + '\n'
    if isinstance(value, str):
        return f'{key} = ' + json.dumps(value, ensure_ascii=False) + '\n'
    raise ValueError(f'{key}: only strings and string lists are written')


def merge_value(key, base, ours, theirs):
    if ours == base:
        return theirs, 'theirs'
    if theirs == base or ours == theirs:
        return ours, 'ours'
    if isinstance(ours, list) and isinstance(theirs, list):
        base = base if isinstance(base, list) else []
        added = [item for item in ours if item not in theirs and item not in base]
        return theirs + added, f'union (+{len(added)} of ours)'
    return None, 'both changed'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('repo')
    parser.add_argument('--file', default='porting.toml')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--base', help='commit whose file is the base, when the merge has several bases and git\'s '
                                       'virtual base (index stage 1) still holds conflict markers')
    args = parser.parse_args()
    path = f'{args.repo}/{args.file}'
    text = open(path, encoding='utf-8').read()
    if args.base:
        base = areas(tomllib.loads(subprocess.run(['git', '-C', args.repo, 'show', f'{args.base}:{args.file}'], check=True,
                                                  capture_output=True, text=True).stdout))
    else:
        base = areas(stage(args.repo, 1, args.file))
    ours, theirs = (areas(stage(args.repo, n, args.file)) for n in (2, 3))
    out, last, left = [], 0, 0
    for match in HUNK.finditer(text):
        out.append(text[last:match.start()])
        last = match.end()
        before = text[:match.start()]
        ids = AREA_ID.findall(before)
        area = ids[-1] if ids else None
        ours_lines, theirs_lines = match.group(1).splitlines(), match.group(2).splitlines()
        keys = [KEY.match(line).group(1) if KEY.match(line) else None for line in ours_lines + theirs_lines]
        line_no = before.count('\n') + 1
        if area is None or None in keys or '[' in ''.join(l[:1] for l in ours_lines + theirs_lines):
            out.append(match.group(0))
            left += 1
            print(f'line {line_no}: left for a hand merge (area {area}, not plain key lines)')
            continue
        resolved, ok = [], True
        for key in dict.fromkeys(keys):
            value, how = merge_value(key, base.get(area, {}).get(key), ours.get(area, {}).get(key), theirs.get(area, {}).get(key))
            if value is None:
                ok = False
                print(f'line {line_no}: {area}.{key}: {how}, left for a hand merge')
                break
            resolved.append(render(key, value))
            print(f'line {line_no}: {area}.{key}: {how}')
        if ok:
            out.append(''.join(resolved))
        else:
            out.append(match.group(0))
            left += 1
    out.append(text[last:])
    result = ''.join(out)
    if left == 0:
        tomllib.loads(result)
    if not args.dry_run:
        open(path, 'w', encoding='utf-8').write(result)
    print(f'{args.file}: {left} hunk(s) left for a hand merge' + (' (dry run)' if args.dry_run else ''))
    return 0 if left == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
