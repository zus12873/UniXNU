"""The board option owned_memory_floor of scripts/unixnu/devicetree.py: the lowest address the kernel window may start at,
handed to the loader as /chosen/darwinboot-memory-floor.

    python3 -I -B -m unittest discover -s local-tools/tests -v
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from unixnu import devicetree  # noqa: E402
from unixnu.util import Error  # noqa: E402

# The options the floor depends on: a window size, and the excluded-range table that makes the loader select a window.
BASE = {'owned_memory_size': '0x180000000', 'owned_memory_excluded_ranges': 64}
FLOOR = 0x980000000


def options(floor, **changes):
    result = dict(BASE, owned_memory_floor=floor, **changes)
    return {key: value for key, value in result.items() if value is not None}


class MemoryFloor(unittest.TestCase):
    def refused(self, table):
        with self.assertRaises(Error) as caught:
            devicetree.memory_floor(table)
        self.assertTrue(str(caught.exception).startswith('Owned memory floor'), str(caught.exception))

    def test_absent_gives_no_property(self):
        self.assertEqual(devicetree.memory_floor(BASE), [])

    def test_accepts_hex_string_decimal_string_and_integer(self):
        self.assertEqual(FLOOR, 40802189312)
        for spelling in ('0x980000000', '40802189312', 40802189312):
            with self.subTest(spelling=spelling):
                self.assertEqual(devicetree.memory_floor(options(spelling)),
                                 [('darwinboot-memory-floor', bytes.fromhex('0000008009000000'))])
        self.assertEqual(bytes.fromhex('0000008009000000'), struct.pack('<Q', FLOOR))

    def test_refuses_zero_negative_and_too_large(self):
        for value in (0, '0', -0x200000, 2 ** 64):
            with self.subTest(value=value):
                self.refused(options(value))

    def test_refuses_value_off_the_2_mib_grid(self):
        for value in ('0x980001000', 0x100000):
            with self.subTest(value=value):
                self.refused(options(value))

    def test_refuses_non_number(self):
        for value in ('top', True):
            with self.subTest(value=value):
                self.refused(options(value))

    def test_requires_size_and_excluded_table(self):
        self.refused(options('0x980000000', owned_memory_size=None))
        self.refused(options('0x980000000', owned_memory_excluded_ranges=None))


if __name__ == '__main__':
    unittest.main()
