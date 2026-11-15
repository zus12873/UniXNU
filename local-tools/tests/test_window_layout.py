"""The memory layout of the 12 GiB sheng unit with the kernel window the 9 GiB run 0x8C0000000..0xB00000000 of DRAM bank 1,
worked out on the host from the three places that define it:

    ../uefi-sheng     MemoryMapLib.c      the firmware's memory table
    ../UniXNU-sheng   board.toml          the window's size and floor, and the memory the kernel must leave alone
    drivers/DarwinBoot MemoryWindow.h     the loader's window selection and its table of free memory outside the window

The loader's functions are the production code, compiled here as its own tests compile it. The kernel's part is a
transcription of arm_vm_outside_init in window-outside-memory-adoption.patch: the kernel adopts the listed runs that lie
below the window, less the kept ranges, and gives all of it up without a message when the runs span more than 4 GiB. Bank 1
is kept out whole, so the kernel adopts the low bank only.

    python3 -I -B -m unittest discover -s local-tools/tests -v
"""
import ctypes
import re
import struct
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from unixnu import devicetree, payload  # noqa: E402

HEADER = ROOT / 'drivers/DarwinBoot/DarwinBootPkg/Driver/MemoryWindow.h'
MAP = ROOT.parent / 'uefi-sheng/Platforms/Xiaomi/shengPkg/Library/MemoryMapLib/MemoryMapLib.c'
BOARD = ROOT.parent / 'UniXNU-sheng/board.toml'
PROFILE = 'macos-27.3-26C5035r'

BS_DATA, FREE = 4, 7
STRIDE = 48
MIB = 1 << 20
KERNEL_OFFSET = 0x4000      # the kernel's link address inside a 2 MiB block
HEAD = 0x11000000           # the loaded image and the room behind it, a generous 272 MiB
HELD_AT_TOP = 0x10000000    # model: the firmware's own allocations take the top 256 MiB of the highest free range
BANK_1 = 0x880000000
WINDOW = 0x8C0004000
LOW_RUNS = [(0xbab00000, 0xccd00000), (0xccf80000, 0xd0000000), (0xd0010000, 0xd8000000), (0xe6720000, 0xff800000)]
LOW_SPAN = (0xbaa00000, 0xff800000)

SOURCE = '''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef uint8_t UINT8; typedef uint32_t UINT32; typedef uint64_t UINT64;
typedef size_t UINTN; typedef int BOOLEAN;
#define STATIC static
#define CONST const
#define VOID void
#define TRUE 1
#define FALSE 0
#define MAX_UINT64 UINT64_MAX
#define EFI_PAGE_SIZE 4096
enum { EfiReservedMemoryType, EfiLoaderCode, EfiLoaderData, EfiBootServicesCode, EfiBootServicesData,
       EfiRuntimeServicesCode, EfiRuntimeServicesData, EfiConventionalMemory };
typedef struct { UINT32 Type; UINT64 PhysicalStart; UINT64 VirtualStart; UINT64 NumberOfPages; UINT64 Attribute; } EFI_MEMORY_DESCRIPTOR;
static UINT64 ReadUnaligned64(const UINT64 *p) { UINT64 v; memcpy(&v, p, 8); return v; }
static void WriteUnaligned64(UINT64 *p, UINT64 v) { memcpy(p, &v, 8); }
#include "MemoryWindow.h"
/* As DarwinBoot.c calls them: 2 MiB blocks, the first-ranked start; runs aligned to 64 KiB and at least 1 MiB long. */
UINT64 start(const void *map, size_t size, size_t stride, UINT64 offset, UINT64 head, UINT64 window, UINT64 floor) {
  UINT64 usable;
  return DarwinWindowStart(map, size, stride, 0x200000, offset, head, window, floor, MAX_UINT64, 0, &usable);
}
size_t outside(const void *map, size_t size, size_t stride, UINT64 base, UINT64 window, UINT8 *table, size_t capacity) {
  UINT64 bytes;
  return DarwinOutsideRanges(map, size, stride, base, window, 0x10000, 0x100000, table, capacity, &bytes);
}
'''


def firmware_free():
    """(base, size) of the system memory the firmware's table adds as free, in the table's order."""
    line = re.compile(r'^\s*\{"[^"]+",\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+),\s*AddMem,\s*SYS_MEM,\s*SYS_MEM_CAP,\s*Conv,', re.M)
    return [(int(base, 16), int(size, 16)) for base, size in line.findall(MAP.read_text())]


def memory_map(free):
    """UEFI descriptors for the free ranges, with the firmware's allocations at the top of the highest one."""
    top = max(free)
    descriptors = [(FREE, base, size) for base, size in free if (base, size) != top]
    return descriptors + [(FREE, top[0], top[1] - HELD_AT_TOP), (BS_DATA, top[0] + top[1] - HELD_AT_TOP, HELD_AT_TOP)]


def adopted(pairs, kept, phys_base, dram_base=0x80000000, twig=0x200000, limit=16):
    """The kernel's arm_vm_outside_init: the runs it adopts as (base, end) and the span they make, or ([], None)."""
    table = []

    def add(base, end, first):
        for index in range(first, len(kept)):
            low, high = kept[index][0], kept[index][0] + kept[index][1]
            if high <= low or high <= base or low >= end:
                continue
            if base < low:
                add(base, low, index + 1)
            if end > high:
                add(high, end, index + 1)
            return
        base, end = (base + 0xfff) & ~0xfff, end & ~0xfff
        if base < end and len(table) < limit:
            table.append((base, end))

    for base, size in pairs:
        if size and base >= dram_base and base + size <= phys_base:
            add(base, base + size, 0)
    if not table:
        return [], None
    low = min(base for base, _ in table) & ~(twig - 1)
    high = min((max(end for _, end in table) + twig - 1) & ~(twig - 1), phys_base & ~(twig - 1))
    return (table, (low, high)) if low < high <= low + (4 << 30) else ([], None)


def number(value):
    return int(str(value), 0)


def cells(*values):
    return struct.pack(f'>{len(values)}I', *values)


# The least hardware tree the generator takes: one DRAM range and one CPU.
HARDWARE = ('', [('compatible', b'unixnu,fixture\0'), ('model', b'fixture\0'), ('#address-cells', cells(2)), ('#size-cells', cells(2))], [
    ('memory@80000000', [('device_type', b'memory\0'), ('reg', cells(0, 0x80000000, 0, 0x80000000))], []),
    ('cpus', [('#address-cells', cells(1)), ('#size-cells', cells(0)), ('timebase-frequency', cells(19200000))], [
        ('cpu@0', [('reg', cells(0)), ('compatible', b'arm,armv8\0')], [])]),
])


def flattened(tree):
    """A version-17 flattened device tree of (name, properties, children) nodes."""
    strings, offsets = bytearray(), {}

    def text(name):
        if name not in offsets:
            offsets[name] = len(strings)
            strings.extend(name.encode() + b'\0')
        return offsets[name]

    def walk(name, properties, children):
        out = struct.pack('>I', 1) + name.encode() + b'\0'
        out += bytes(-len(out) % 4)
        for key, value in properties:
            out += struct.pack('>III', 3, len(value), text(key)) + value + bytes(-len(value) % 4)
        return out + b''.join(walk(*child) for child in children) + struct.pack('>I', 2)

    structure = walk(*tree) + struct.pack('>I', 9)
    start = 40 + 16  # the header, then an empty reservation map
    return (struct.pack('>10I', 0xd00dfeed, start + len(structure) + len(strings), start, start + len(structure), 40, 17, 16, 0,
                        len(strings), len(structure)) + bytes(16) + structure + bytes(strings))


@unittest.skipUnless(MAP.is_file() and BOARD.is_file(), 'needs ../uefi-sheng and ../UniXNU-sheng next to this repository')
class LargeWindowLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='large-window-')
        work = Path(cls.work.name)
        (work / 'layout.c').write_text(SOURCE)
        # The header's other functions are not called here.
        subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-fsanitize=undefined',
                        '-fno-sanitize-recover=all', '-shared', '-fPIC', '-I', str(HEADER.parent), str(work / 'layout.c'),
                        '-o', str(work / 'layout.dylib')], check=True)
        cls.lib = ctypes.CDLL(str(work / 'layout.dylib'))
        u64, size_t = ctypes.c_uint64, ctypes.c_size_t
        cls.lib.start.restype = u64
        cls.lib.start.argtypes = [ctypes.c_char_p, size_t, size_t, u64, u64, u64, u64]
        cls.lib.outside.restype = size_t
        cls.lib.outside.argtypes = [ctypes.c_char_p, size_t, size_t, u64, u64, ctypes.c_char_p, size_t]
        cls.adt = tomllib.loads(BOARD.read_text())['os_overrides'][PROFILE]['payload']['adt']
        cls.free = firmware_free()
        cls.bank_1 = [entry for entry in cls.free if entry[0] >= BANK_1]

    @classmethod
    def tearDownClass(cls):
        del cls.lib
        cls.work.cleanup()

    def kept(self):
        return [(number(base), number(size)) for base, _, size in (str(item).partition(':')
                                                                    for item in self.adt['owned_memory_outside_reserved'])]

    def window(self, free, size=None, floor=None):
        """Where the loader starts the window on this firmware table, with the board's size and floor unless given."""
        size = number(self.adt['owned_memory_size']) if size is None else size
        floor = number(self.adt.get('owned_memory_floor', '0')) if floor is None else floor
        blob = b''.join(struct.pack('<I4xQQQQ8x', kind, base, 0, size >> 12, 0) for kind, base, size in memory_map(free))
        return self.lib.start(blob, len(blob), STRIDE, KERNEL_OFFSET, HEAD, size, floor)

    def outside(self, free):
        """The (base, size) pairs the loader lists as free memory outside that window, in the board's table."""
        blob = b''.join(struct.pack('<I4xQQQQ8x', kind, base, 0, size >> 12, 0) for kind, base, size in memory_map(free))
        capacity = number(self.adt['owned_memory_outside_ranges'])
        table = ctypes.create_string_buffer(16 * capacity)
        count = self.lib.outside(blob, len(blob), STRIDE, self.window(free), number(self.adt['owned_memory_size']), table, capacity)
        return [struct.unpack_from('<QQ', table.raw, 16 * index) for index in range(count)]

    def adoption(self, free, kept=None):
        return adopted(self.outside(free), self.kept() if kept is None else kept, self.window(free))

    def test_firmware_table_lists_bank_1_to_the_top(self):
        self.assertEqual(self.bank_1, [(0x880000000, 0x39D00000), (0x8B9F00000, 0x01E00000), (0x8C0000000, 0x240000000)])

    def test_board_window_is_the_9_gib_run(self):
        self.assertEqual(number(self.adt['owned_memory_size']), 0x240000000)
        self.assertEqual(number(self.adt['owned_memory_floor']), 0x8C0000000)
        self.assertEqual(self.window(self.free), WINDOW)

    def test_planned_windows_start_at_their_floors(self):
        for size, floor, start in [(0x1E0000000, 0x920000000, 0x920004000), (0x180000000, 0x980000000, 0x980004000),
                                   (0x1E0000000, 0x8C0000000, 0x8C0004000), (0x200000000, 0x900000000, 0x900004000)]:
            with self.subTest(size=hex(size), floor=hex(floor)):
                self.assertEqual(self.window(self.free, size, floor), start)

    def test_generator_accepts_the_board_options(self):
        self.assertEqual(devicetree.memory_floor(self.adt), [('darwinboot-memory-floor', struct.pack('<Q', 0x8C0000000))])
        self.assertEqual(devicetree.memory_size(self.adt), [('darwinboot-memory-size', struct.pack('<Q', 0x240000000))])

    def test_generated_tree_carries_the_window_and_the_kept_ranges(self):
        # The generator's whole path from the board's options to /chosen, read back with the tool that checks a built payload.
        work = Path(self.work.name)
        (work / 'hardware.dtb').write_bytes(flattened(HARDWARE))
        (work / 'kernel.macho.adt').write_bytes(devicetree.generate(work / 'hardware.dtb', {'payload': {'adt': self.adt}}))
        result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'local-tools/adt-chosen.py'), str(work / 'kernel.macho.adt')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            'darwinboot-memory-size 8 0x240000000',
            'darwinboot-memory-excluded 1024 64 empty pairs',
            'darwinboot-memory-floor 8 0x8c0000000',
            'darwinboot-loader-inputs 64 4 empty pairs',
            'darwinboot-memory-outside 256 16 empty pairs',
            'darwinboot-memory-outside-kept 32 0xd0000000+0x10000 0x880000000+0x280000000',
        ])

    def test_kernel_adopts_only_the_low_bank(self):
        runs, span = self.adoption(self.free)
        self.assertEqual(runs, LOW_RUNS)
        self.assertEqual(span, LOW_SPAN)
        self.assertEqual(sum(end - base for base, end in runs), 0x36350000)
        self.assertTrue(all(end <= 0x100000000 for _, end in runs))

    def test_without_the_bank_1_kept_range_nothing_is_adopted(self):
        self.assertIn('0x880000000:0x280000000', self.adt['owned_memory_outside_reserved'])
        self.assertEqual(self.adoption(self.free, kept=[(0xd0000000, 0x10000)]), ([], None))

    def test_bank_1_stays_out_whatever_the_low_bank_looks_like(self):
        # One free run across the whole low bank: bank 1 is still out, and the span is exactly the low bank.
        runs, span = self.adoption([(0x80000000, 0x80000000)] + self.bank_1)
        self.assertEqual(runs, [(0x80000000, 0xd0000000), (0xd0010000, 0x100000000)])
        self.assertEqual(span, (0x80000000, 0x100000000))
        # Twenty small runs: the loader's table holds 16 ranges and the kernel adopts 14 of them.
        small = [(0x90000000 + index * 0x2000000, 16 * MIB) for index in range(20)]
        self.assertEqual(len(self.outside(small + self.bank_1)), 16)
        runs, span = self.adoption(small + self.bank_1)
        self.assertEqual(len(runs), 14)
        self.assertEqual(sum(end - base for base, end in runs), 0xE000000)
        self.assertTrue(all(end <= 0x100000000 for _, end in runs))

    def test_command_line_fits_with_the_run_arguments(self):
        arguments = tomllib.loads(BOARD.read_text())['os_overrides'][PROFILE]['payload']['kernel_args']
        self.assertIn('vm_compression_limit=1572864', arguments)
        self.assertFalse([item for item in arguments if item.split('=')[0] in ('memory-outside', 'data-reset')])
        line = payload.check_args(['vm-swapin-io=1', 'memory-outside=0'] + arguments)
        self.assertEqual(len(line), 923)


if __name__ == '__main__':
    unittest.main()
