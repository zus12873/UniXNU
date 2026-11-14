#!/usr/bin/env python3
"""Read back the memory description that the diagnostic firmware (abl-memory-dump.patch) prints on the screen log.

    read-abl-memory.py TEXT [TEXT ...]

Each TEXT is the recognised text of one frame of a screen recording (local-tools/ocr-frames.swift writes them). The
firmware prints one line per range:

    ABLMEM <node> <base> <size> <flags> <check>      a range of a /memory node
    ABLMAP <index> <base> <size> <check>             an entry of the device tree's memory reservation block
    ABLRSV <node> <base> <size> <flags> <check>      a range of a /reserved-memory node
    ABLRSV <node> dyn <size> <flags>                 a reservation without a fixed address

base and size are 10 hexadecimal digits; flags are n (no-map), d (disabled), r (reusable) or '-' in each place; check
is DumpCheck() of the patch over base and size. A line is kept only when its check value matches, so a misread digit
drops the line instead of giving a wrong range. Lines seen in several frames are counted once. Prints the ranges in
address order and, for /memory, their total.
"""
import re
import sys
from pathlib import Path

HEX = '[0-9a-fA-F]'
RANGE = re.compile(rf'(ABLMEM|ABLRSV)\s+(\S+)\s+({HEX}{{10}})\s+({HEX}{{10}})\s+([-ndr]{{3}})\s+({HEX}{{4}})\b')
MAP = re.compile(rf'(ABLMAP)\s+(\d+)\s+({HEX}{{10}})\s+({HEX}{{10}})\s+({HEX}{{4}})\b')
DYNAMIC = re.compile(rf'ABLRSV\s+(\S+)\s+dyn\s+({HEX}{{10}})\s+([-ndr]{{3}})')
OTHER = re.compile(r'ABL(?:MEM \S+ ddr_size .*|MEM total .*|END .*)')


def check(base, size):
    """DumpCheck() of abl-memory-dump.patch."""
    total = 0
    for value in (base, size):
        for index in range(8):
            total = (total * 31 + ((value >> (8 * index)) & 0xff)) & 0xffffffff
    return (total ^ (total >> 16)) & 0xffff


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ranges, dynamic, other, rejected = {}, {}, {}, set()
    for name in sys.argv[1:]:
        for line in Path(name).read_text(errors='replace').splitlines():
            match = RANGE.search(line) or MAP.search(line)
            if match:
                groups = match.groups()
                tag, node, base, size = groups[0], groups[1], int(groups[2], 16), int(groups[3], 16)
                flags = groups[4] if tag != 'ABLMAP' else '---'
                if check(base, size) == int(groups[-1], 16):
                    ranges.setdefault((tag, base, size), (node, flags))
                else:
                    rejected.add(match.group(0))
                continue
            match = DYNAMIC.search(line)
            if match:
                dynamic.setdefault(match.group(1), (int(match.group(2), 16), match.group(3)))
                continue
            match = OTHER.search(line)
            if match:
                other[match.group(0)] = other.get(match.group(0), 0) + 1
    for tag in ('ABLMEM', 'ABLMAP', 'ABLRSV'):
        rows = sorted((base, size, *ranges[key]) for key in ranges for t, base, size in [key] if t == tag)
        print(f'{tag}: {len(rows)} ranges')
        for base, size, node, flags in rows:
            print(f'  {base:#014x} .. {base + size:#014x}  {size / (1 << 20):10.2f} MiB  {flags}  {node}')
        if tag == 'ABLMEM':
            print(f'  total {sum(row[1] for row in rows) / (1 << 30):.3f} GiB')
    print(f'ABLRSV without a fixed address: {len(dynamic)}')
    for node, (size, flags) in sorted(dynamic.items()):
        print(f'  {size / (1 << 20):10.2f} MiB  {flags}  {node}')
    print('other lines (times seen):')
    for line, count in sorted(other.items()):
        print(f'  {count:3d}  {line}')
    # A rejected reading matters only when no frame gave the same range correctly.
    print(f'readings dropped for a wrong check value: {len(rejected)}')
    for line in sorted(rejected):
        print(f'  {line}')


if __name__ == '__main__':
    main()
