"""The board option owned_memory_size of scripts/unixnu/devicetree.py: the size of the kernel window, handed to the loader
as /chosen/darwinboot-memory-size. The generator and the loader accept the same range, 256 MiB to 9 GiB.

    python3 -I -B -m unittest discover -s local-tools/tests -v
"""
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from unixnu import devicetree  # noqa: E402
from unixnu.util import Error  # noqa: E402

WINDOW_SIZE_HEADER = ROOT / 'drivers/DarwinBoot/DarwinBootPkg/Driver/WindowSize.h'
# The loader's own test of DarwinWindowSizeValid: it asserts 9 GiB is accepted and 9 GiB + 2 MiB is not.
WINDOW_SIZE_TEST = ROOT / 'drivers/DarwinBoot/Test/window-size.c'


class MemorySize(unittest.TestCase):
    def refused(self, value):
        with self.assertRaises(Error) as caught:
            devicetree.memory_size({'owned_memory_size': value})
        self.assertTrue(str(caught.exception).startswith('Owned memory must be 256 MiB to 9 GiB'), str(caught.exception))

    def test_absent_gives_no_property(self):
        self.assertEqual(devicetree.memory_size({}), [])

    def test_accepts_the_bounds(self):
        for value in ('0x10000000', '0x180000000', '0x200000000', '0x240000000', 0x1E0000000):
            size = int(str(value), 0)
            self.assertEqual(devicetree.memory_size({'owned_memory_size': value}),
                             [('darwinboot-memory-size', struct.pack('<Q', size))], value)

    def test_refuses_above_9_gib(self):
        for value in ('0x240200000', '0x280000000'):
            self.refused(value)

    def test_refuses_too_small_and_off_grid(self):
        for value in ('0xfe00000', '0x10001000'):
            self.refused(value)

    def test_loader_bound_matches_the_generator(self):
        text = WINDOW_SIZE_HEADER.read_text()
        self.assertIn('0x240000000ULL', text)
        self.assertNotIn('0x200000000ULL', text)

    def test_loader_test_of_the_bound_passes(self):
        # By behaviour: the loader's test program, built from the header as it is, runs its asserts and exits 0.
        self.assertIn('0x240000000ULL', WINDOW_SIZE_TEST.read_text())
        with tempfile.TemporaryDirectory(prefix='window-size-') as work:
            program = Path(work) / 'window-size'
            subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', str(WINDOW_SIZE_TEST), '-o', str(program)],
                           check=True, capture_output=True)
            result = subprocess.run([str(program)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
