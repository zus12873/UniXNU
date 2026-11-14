#!/usr/bin/env python3
"""Read back the memory description that the diagnostic firmware (abl-memory-dump.patch) prints on the screen log.

    read-abl-memory.py TEXT [TEXT ...]

Each TEXT holds recognised text of frames of a screen recording, as local-tools/ocr-frames.swift writes it: plain lines,
or with --boxes the pieces of text with their place in the frame ("<frame> TAB <top> TAB <left> TAB <height> TAB <text>"),
which are put together again here into the lines of the console. The firmware prints one line per range:

    ABLMEM <node> <base> <size> <flags> <check>      a range of a /memory node
    ABLMAP <index> <base> <size> <check>             an entry of the device tree's memory reservation block
    ABLRSV <node> <base> <size> <flags> <check>      a range of a /reserved-memory node
    ABLRSV <node> dyn <size> <flags>                 a reservation without a fixed address

base and size are 10 hexadecimal digits; flags are n (no-map), d (disabled), r (reusable) or '-' in each place; check
is DumpCheck() of the patch over base and size. A line is kept only when its check value matches, so a misread digit
drops the line instead of giving a wrong range. Spaces that the recognition puts inside a number are ignored, and the
flags are read as the letters found between size and check. Lines seen in several frames are counted once. Prints the
ranges in address order and, for /memory, their total.
"""
import re
import sys
from pathlib import Path

HEX = '[0-9a-fA-F]'
# After the node name: base, size, anything that is not a hexadecimal digit (the flags) and the check value.
RANGE = re.compile(rf'(ABLMEM|ABLRSV|ABLMAP)\s+(\S+)\s+({HEX}{{10}})({HEX}{{10}})([^0-9a-fA-F]*?)({HEX}{{4}})$')
DYNAMIC = re.compile(rf'ABLRSV\s+(\S+)\s+dyn\s*({HEX}{{10}})(.*)$')
OTHER = re.compile(r'ABL(?:MEM \S+ ddr_size .*|MEM total .*|END .*)')
PIECE = re.compile(r'([^\t]+)\t([0-9.]+)\t([0-9.]+)\t([0-9.]+)\t(.*)')


def console_lines(text):
    """The lines of TEXT; pieces written by ocr-frames.swift --boxes are joined, left to right, into console lines."""
    frames, plain = {}, []
    for line in text.splitlines():
        match = PIECE.fullmatch(line)
        if match:
            frame, top, left, height, piece = match.groups()
            frames.setdefault(frame, []).append((float(top) + float(height) / 2, float(left), float(height), piece))
        else:
            plain.append(line)
    for pieces in frames.values():
        rows = []
        for middle, left, height, piece in sorted(pieces):
            # A piece belongs to the row whose middle is within half a line of its own.
            if rows and abs(middle - rows[-1][0]) < 0.5 * min(height, rows[-1][1]):
                rows[-1][2].append((left, piece))
            else:
                rows.append([middle, height, [(left, piece)]])
        plain.extend(' '.join(piece for _, piece in sorted(row[2])) for row in rows)
    return plain


def flags_of(text):
    return ''.join(letter if letter in text else '-' for letter in 'ndr')


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
        for line in console_lines(Path(name).read_text(errors='replace')):
            head = re.search(r'ABL(?:MEM|RSV|MAP)\s+\S+\s+', line)
            # Without the spaces that recognition puts inside or between the numbers.
            packed = line[head.start():head.end()] + line[head.end():].replace(' ', '') if head else line
            match = RANGE.search(packed)
            if match:
                tag, node, base, size = match.group(1), match.group(2), int(match.group(3), 16), int(match.group(4), 16)
                if check(base, size) == int(match.group(6), 16):
                    ranges.setdefault((tag, base, size), (node, flags_of(match.group(5))))
                else:
                    rejected.add(match.group(0))
                continue
            match = DYNAMIC.search(packed)
            if match:
                dynamic.setdefault(match.group(1), (int(match.group(2), 16), flags_of(match.group(3))))
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
