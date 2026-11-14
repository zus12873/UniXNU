"""Black-box tests of local-tools/adt-chosen.py: each one writes a device tree with the generator's own node writer, runs
the tool as a command and reads what it prints.

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
from unixnu.devicetree import node  # noqa: E402

TOOL = ROOT / 'local-tools/adt-chosen.py'
REFUSAL = 'adt-chosen: '
CHOSEN = [
    ('random-seed', bytes(range(64))),
    ('darwinboot-memory-size', struct.pack('<Q', 0x180000000)),
    ('darwinboot-memory-excluded', bytes(16 * 64)),
    ('darwinboot-memory-floor', struct.pack('<Q', 0x980000000)),
    ('darwinboot-memory-outside', bytes(16 * 16)),
    ('darwinboot-memory-outside-kept', struct.pack('<QQQQ', 0xd0000000, 0x10000, 0x80000000, 0x800000000)),
]
TREE = node('device-tree', [('model', b'fixture\0')], [
    # A node in front of /chosen, with a property the tool must not mistake for one of /chosen.
    node('cpus', [('darwinboot-memory-floor', struct.pack('<Q', 0x1000))], [node('cpu0')]),
    node('chosen', CHOSEN, [node('memory-map', [('RAMDisk', bytes(16))]), node('manifest-properties')]),
])


class AdtChosen(unittest.TestCase):
    def run_tool(self, blob):
        with tempfile.TemporaryDirectory(prefix='adt-chosen-') as work:
            path = Path(work) / 'kernel.macho.adt'
            path.write_bytes(blob)
            return subprocess.run([sys.executable, '-I', '-B', str(TOOL), str(path)], capture_output=True, text=True)

    def test_prints_the_darwinboot_properties_of_chosen(self):
        result = self.run_tool(TREE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            'darwinboot-memory-size 8 0x180000000',
            'darwinboot-memory-excluded 1024 64 empty pairs',
            'darwinboot-memory-floor 8 0x980000000',
            'darwinboot-memory-outside 256 16 empty pairs',
            'darwinboot-memory-outside-kept 32 0xd0000000+0x10000 0x80000000+0x800000000',
        ])

    def test_refuses_truncated_tree(self):
        result = self.run_tool(TREE[:-5])
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertEqual(result.stdout, '')

    def test_refuses_tree_without_chosen(self):
        result = self.run_tool(node('device-tree', [('model', b'fixture\0')]))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
