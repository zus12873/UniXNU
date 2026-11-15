"""The bootstrap page-table pool reserved by patches/xnu-12377/native-4k-bootstrap-capacity.patch: the kernel maps its
whole memory window twice before the MMU is on, and the pool must hold both mappings for the planned windows.

    python3 -I -B -m unittest discover -s local-tools/tests -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'patches/xnu-12377/native-4k-bootstrap-capacity.patch'
LINK = 0xfffffff007004000
GENERATOR_BOUND = 0x240000000
GIB = 1 << 30
MIB2 = 0x200000

# (physical base, size) of the current 6 GiB window and the larger planned ones.
WINDOWS = [(0x980004000, 0x180000000), (0x920004000, 0x1E0000000), (0x8C0004000, 0x240000000),
           (0x900004000, 0x200000000)]


def regions(base, size):
    """The number of 1 GiB regions touched by [base rounded down to 2 MiB, + size)."""
    start = base - base % MIB2
    return (start + size - 1) // GIB - start // GIB + 1


def bootstrap_pages(phys_base, size, virt_base=None):
    """Pages the two mappings need: two roots, plus one level-2 page per 1 GiB region of each mapping."""
    if virt_base is None:
        virtual = -(-size // GIB) + 1
    else:
        virtual = regions(virt_base, size)
    return 2 + regions(phys_base, size) + virtual


def patch_pages():
    text = PATCH.read_text()
    found = re.findall(r'^\+#define BOOTSTRAP_TABLE_SIZE \(ARM_PGBYTES \* (\d+)\)$', text, re.M)
    assert len(found) == 1, found
    return int(found[0])


class BootstrapTables(unittest.TestCase):
    def test_patch_reserves_22_pages(self):
        lines = [line for line in PATCH.read_text().splitlines()
                 if line.startswith('+#define BOOTSTRAP_TABLE_SIZE (ARM_PGBYTES * ')]
        self.assertEqual(len(lines), 1)
        self.assertEqual(patch_pages(), 22)

    def test_first_hunk_still_adds_five_lines(self):
        text = PATCH.read_text()
        start = text.index('@@ -115,6 +115,11 @@')
        end = text.index('diff --git', start)
        body = text[start:end].splitlines()[1:]
        self.assertEqual(sum(line.startswith('+') for line in body), 5)
        self.assertEqual(sum(line.startswith(' ') for line in body), 6)

    def test_planned_windows_at_the_link_address(self):
        got = [bootstrap_pages(base, size, LINK) for base, size in WINDOWS]
        self.assertEqual(got, [15, 18, 21, 19])

    def test_planned_windows_with_the_worst_virtual_base(self):
        got = [bootstrap_pages(base, size) for base, size in WINDOWS]
        self.assertEqual(got, [15, 19, 21, 19])

    def test_sixteen_pages_were_not_enough(self):
        for base, size in WINDOWS[1:]:
            with self.subTest(base=hex(base)):
                self.assertGreater(bootstrap_pages(base, size, LINK), 16)
                self.assertGreater(bootstrap_pages(base, size), 16)

    def test_capacity_covers_the_tool_bound(self):
        worst = max(bootstrap_pages(0x880000000 + k * MIB2, GENERATOR_BOUND) for k in range(512))
        self.assertEqual(worst, patch_pages())


if __name__ == '__main__':
    unittest.main()
