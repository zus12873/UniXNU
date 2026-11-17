#!/usr/bin/env python3
"""What other people's branches have that a local branch does not (the rule in .claude/rules/check-other-repos-first.md).

    compare-progress.py REPO MINE BASE PATTERN... [--since YYYY-MM-DD] [--max N]

REPO is a Git checkout, MINE the local ref, BASE the upstream ref both sides start from (upstream/main, origin/main),
PATTERN a for-each-ref pattern of the other branches (refs/remotes/crossdarwin/, refs/remotes/upstream/). Fetch first.

Upstream merges other branches by squashing, so a commit missing from MINE does not mean its content is missing. For each
branch updated since --since this compares content: the files the branch changed from its merge base with BASE, and of
those the ones whose content in MINE differs from the branch tip. A branch whose changed files all match MINE is already
in MINE. The commits listed are the branch's commits (merges left out) that touch a differing file and have no
equivalent patch in MINE. Read-only: runs git log, diff and merge-base only.
"""
import argparse
import subprocess
import sys


def git(repo, *args):
    return subprocess.run(['git', '-C', repo, *args], check=True, capture_output=True, text=True).stdout


def branches(repo, patterns, since):
    out = git(repo, 'for-each-ref', '--sort=-committerdate', '--format=%(refname)\t%(committerdate:short)', *patterns)
    for line in out.splitlines():
        ref, date = line.split('\t')
        if ref.endswith('/HEAD') or date < since:
            continue
        yield ref, date


def compare(repo, mine, base, ref, limit):
    tip_base = git(repo, 'merge-base', ref, base).strip()
    if tip_base == git(repo, 'rev-parse', ref).strip():
        # BASE itself (or a branch already in it): what it gained since MINE left it.
        tip_base = git(repo, 'merge-base', ref, mine).strip()
    changed = [p for p in git(repo, 'diff', '--name-only', '--no-renames', tip_base, ref).splitlines() if p]
    differing = []
    if changed:
        # In chunks: a branch can touch thousands of paths.
        for i in range(0, len(changed), 200):
            differing += [p for p in git(repo, 'diff', '--name-only', '--no-renames', mine, ref, '--', *changed[i:i + 200]).splitlines() if p]
    commits = []
    if differing:
        log = git(repo, 'log', '--cherry-pick', '--right-only', '--no-merges', '--date=short', '--format=%h\t%ad\t%an\t%s',
                  f'{mine}...{ref}', '--', *differing[:200])
        commits = [line.split('\t', 3) for line in log.splitlines() if line]
    return changed, differing, commits[:limit], len(commits)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('repo')
    parser.add_argument('mine')
    parser.add_argument('base')
    parser.add_argument('patterns', nargs='+')
    parser.add_argument('--since', default='0000-00-00')
    parser.add_argument('--max', type=int, default=12, help='commits listed per branch')
    args = parser.parse_args()
    behind = git(args.repo, 'rev-list', '--count', f'{args.mine}..{args.base}').strip()
    ahead = git(args.repo, 'rev-list', '--count', f'{args.base}..{args.mine}').strip()
    print(f'{args.mine}: {ahead} commits not in {args.base}, {behind} commits of {args.base} not in it')
    for ref, date in branches(args.repo, args.patterns, args.since):
        changed, differing, commits, total = compare(args.repo, args.mine, args.base, ref, args.max)
        name = ref.removeprefix('refs/remotes/')
        if not differing:
            print(f'= {name} ({date}): {len(changed)} files changed, all as in {args.mine}')
            continue
        print(f'+ {name} ({date}): {len(differing)} of {len(changed)} changed files differ; {total} commits')
        for h, d, author, subject in commits:
            print(f'    {d} {h} {author}: {subject}')
        if total > len(commits):
            print(f'    ... {total - len(commits)} more')
    return 0


if __name__ == '__main__':
    sys.exit(main())
