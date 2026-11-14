"""The memory layout of the 12 GiB sheng unit with the kernel window at the top of DRAM bank 1, worked out on the host from
the three places that define it:

    ../uefi-sheng     MemoryMapLib.c      the firmware's memory table
    ../UniXNU-sheng   board.toml          the window's size and floor, and the memory the kernel must leave alone
    drivers/DarwinBoot MemoryWindow.h     the loader's window selection and its table of free memory outside the window

The loader's functions are the production code, compiled here as its own tests compile it. The kernel's part is a
transcription of arm_vm_outside_init in window-outside-memory-adoption.patch: the kernel adopts the listed runs that lie
below the window, less the kept ranges, and gives all of it up without a message when the runs span more than 4 GiB.

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
from unixnu import devicetree  # noqa: E402

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
WINDOW = 0x980004000
BANK_1_RUNS = [(0x880000000, 0x8B9D00000), (0x8B9F00000, 0x8BBD00000), (0x8C0000000, 0x980000000)]
SPAN = (0x880000000, 0x980000000)

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


@unittest.skipUnless(MAP.is_file() and BOARD.is_file(), 'needs ../uefi-sheng and ../UniXNU-sheng next to this repository')
class TopWindowLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='top-window-')
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

    def window(self, free):
        """Where the loader starts the window on this firmware table, with the board's size and floor."""
        blob = b''.join(struct.pack('<I4xQQQQ8x', kind, base, 0, size >> 12, 0) for kind, base, size in memory_map(free))
        return self.lib.start(blob, len(blob), STRIDE, KERNEL_OFFSET, HEAD, number(self.adt['owned_memory_size']),
                              number(self.adt.get('owned_memory_floor', '0')))

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

    def test_window_starts_at_the_floor(self):
        self.assertEqual(self.window(self.free), WINDOW)

    def test_generator_accepts_the_board_options(self):
        self.assertEqual(devicetree.memory_floor(self.adt), [('darwinboot-memory-floor', struct.pack('<Q', 0x980000000))])

    def test_kernel_adopts_the_three_runs_below_the_window(self):
        runs, span = self.adoption(self.free)
        self.assertEqual(runs, BANK_1_RUNS)
        self.assertEqual(span, SPAN)
        self.assertEqual(sum(end - base for base, end in runs), 0xFBB00000)

    def test_everything_below_bank_1_is_kept_out(self):
        # Whatever the firmware leaves free below bank 1, even all of it: one stray run there would stretch the span
        # past 4 GiB and the kernel would adopt nothing.
        runs, span = self.adoption([(0x80000000, BANK_1 - 0x80000000)] + self.bank_1)
        self.assertEqual(runs, BANK_1_RUNS)
        self.assertEqual(span, SPAN)

    def test_without_the_new_kept_range_nothing_is_adopted(self):
        self.assertIn('0x80000000:0x800000000', self.adt['owned_memory_outside_reserved'])
        self.assertEqual(self.adoption(self.free, kept=[(0xd0000000, 0x10000)]), ([], None))

    def test_keeping_the_newly_listed_memory_out(self):
        # The comparison image of the first hardware run: the 443 MiB the measured table added on 2026-11-14 stay out.
        runs, span = self.adoption(self.free, kept=self.kept() + [(0x8A0000000, 0x20000000)])
        self.assertEqual(runs, [(0x880000000, 0x8A0000000), (0x8C0000000, 0x980000000)])
        self.assertEqual(span, SPAN)
        self.assertEqual(sum(end - base for base, end in runs), 0xE0000000)

    def test_fragmented_low_bank_keeps_the_span(self):
        bank_1_pairs = [(base, end - base) for base, end in BANK_1_RUNS]
        # Twenty small free runs in the low bank: the table keeps the largest runs, the three of bank 1 among them.
        small = [(0x90000000 + index * 0x2000000, 16 * MIB) for index in range(20)]
        self.assertLessEqual(set(bank_1_pairs), set(self.outside(small + self.bank_1)))
        # Twenty runs larger than the 30 MiB run of bank 1 push that one out of the table; the span stays.
        large = [(0x90000000 + index * 0x3000000, 40 * MIB) for index in range(20)]
        runs, span = self.adoption(large + self.bank_1)
        self.assertEqual(runs, [BANK_1_RUNS[0], BANK_1_RUNS[2]])
        self.assertEqual(span, SPAN)
        self.assertEqual(sum(end - base for base, end in runs), 0xF9D00000)


if __name__ == '__main__':
    unittest.main()
