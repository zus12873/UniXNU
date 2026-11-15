"""Black-box tests of local-tools/make-payload-variant.py: each one builds a small FAT payload volume, runs the tool as a
command and reads the files of the volume it writes.

    python3 -I -B -m unittest discover -s local-tools/tests -v

Needs GNU mtools (mformat, mcopy, mtype) on PATH, as the tool itself does.
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from unixnu.devicetree import node  # noqa: E402
from test_make_flash_bootimg import MTOOLS_ENV, make_volume, volume_files  # noqa: E402

TOOL = ROOT / 'local-tools/make-payload-variant.py'
ADT_TOOL = ROOT / 'local-tools/adt-chosen.py'
REFUSAL = 'make-payload-variant: '
ADT_PATH = 'EFI/UniXNU/Payloads/kernel.macho.adt'
TOML_PATH = 'EFI/UniXNU/unixnu.toml'
KERNEL_PATH = 'EFI/UniXNU/Payloads/kernel.macho'
ARGS = 'debug=0x14e vm_compression_limit=1572864'
ADT = node('device-tree', [('model', b'fixture\0')], [
    # A node in front of /chosen with a property of the same name as one of /chosen.
    node('cpus', [('darwinboot-memory-floor', struct.pack('<Q', 0x1000))], [node('cpu0')]),
    node('chosen', [
        ('random-seed', bytes(range(64))),
        ('darwinboot-memory-size', struct.pack('<Q', 0x240000000)),
        ('darwinboot-memory-excluded', bytes(1024)),
        ('darwinboot-memory-floor', struct.pack('<Q', 0x8C0000000)),
    ], [node('memory-map', [('RAMDisk', bytes(16))])]),
])
KERNEL = bytes((i * 13 + 5) & 0xff for i in range(1 << 20))


def toml(args=ARGS):
    return f'[[entry]]\nname = "one"\nargs = "{args}"\n\n[[entry]]\nname = "two"\nargs = "{args}"\n'.encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class MakePayloadVariant(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.dir = Path(work.name)
        self.base = self.dir / 'base.img'
        self.out = self.dir / 'out.img'

    def make_base(self, args=ARGS, adt=ADT, toml_bytes=None):
        make_volume(self.base, 64, {ADT_PATH: adt, TOML_PATH: toml_bytes or toml(args), KERNEL_PATH: KERNEL})
        self.base_sha = sha256(self.base.read_bytes())

    def run_tool(self, *args, base=None, out=None):
        return subprocess.run([sys.executable, '-I', '-B', str(TOOL), str(base or self.base), str(out or self.out), *args],
                              capture_output=True, text=True)

    def read(self, image, path):
        return subprocess.run(['mtype', '-i', str(image), f'::/{path}'], env=MTOOLS_ENV, check=True, capture_output=True).stdout

    def adt_chosen(self, blob):
        path = self.dir / 'check.adt'
        path.write_bytes(blob)
        result = subprocess.run([sys.executable, '-I', '-B', str(ADT_TOOL), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.splitlines()

    def assertRefused(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.out.exists(), 'a refused run left OUT behind')
        self.assertFalse(self.out.with_name(self.out.name + '.tmp').exists(), 'a refused run left OUT.tmp behind')
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)

    def test_sets_two_properties_and_prepends_an_argument(self):
        self.make_base()
        result = self.run_tool('--set', 'darwinboot-memory-size=0x1E0000000', '--set', 'darwinboot-memory-floor=0x920000000',
                               '--arg', 'memory-outside=0')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.out.read_bytes()
        self.assertEqual(result.stdout.splitlines()[-1], f'{self.out}: {len(data)} bytes, sha256 {sha256(data)}, '
                         'adt: darwinboot-memory-size=0x1e0000000 darwinboot-memory-floor=0x920000000, args: memory-outside=0')
        adt = self.read(self.out, ADT_PATH)
        self.assertEqual(self.adt_chosen(adt), [
            'darwinboot-memory-size 8 0x1e0000000',
            'darwinboot-memory-excluded 1024 64 empty pairs',
            'darwinboot-memory-floor 8 0x920000000',
        ])
        self.assertEqual(len(adt), len(ADT))
        # The cpus node in front of /chosen keeps its own darwinboot-memory-floor: the two trees differ only in /chosen.
        cpus_end = ADT.index(b'chosen\0')
        self.assertEqual(adt[:cpus_end], ADT[:cpus_end])
        self.assertEqual(self.read(self.out, TOML_PATH), toml(f'memory-outside=0 {ARGS}'))
        self.assertEqual(sha256(self.read(self.out, KERNEL_PATH)), sha256(KERNEL))
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)
        self.assertEqual({k: v for k, v in volume_files(data).items() if k not in (ADT_PATH, TOML_PATH)},
                         {k: v for k, v in volume_files(self.base.read_bytes()).items() if k not in (ADT_PATH, TOML_PATH)})

    def test_argument_only(self):
        self.make_base()
        result = self.run_tool('--arg', 'memory-outside=0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1].split(', ', 2)[2], 'adt: unchanged, args: memory-outside=0')
        self.assertEqual(self.read(self.out, ADT_PATH), ADT)
        self.assertEqual(self.read(self.out, TOML_PATH), toml(f'memory-outside=0 {ARGS}'))

    def test_refuses_existing_output_and_same_file(self):
        self.make_base()
        self.out.write_bytes(b'an earlier output')
        result = self.run_tool('--arg', 'a=1')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertEqual(self.out.read_bytes(), b'an earlier output')
        result = self.run_tool('--arg', 'a=1', out=self.base)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)
        self.out.unlink()
        result = self.run_tool('--arg', 'a=1', base=self.dir / 'missing.img')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)

    def test_refuses_bad_property(self):
        self.make_base()
        for text in ('darwinboot-nothing=1', 'random-seed=1', 'darwinboot-memory-excluded=1', 'darwinboot-memory-size=-1',
                     'darwinboot-memory-size=0x10000000000000000', 'darwinboot-memory-size=abc', 'darwinboot-memory-size'):
            with self.subTest(text=text):
                self.assertRefused(self.run_tool('--set', text))
        # The same name in /chosen twice.
        twice = node('device-tree', [], [node('chosen', [('darwinboot-memory-size', bytes(8))] * 2)])
        self.make_base(adt=twice)
        self.assertRefused(self.run_tool('--set', 'darwinboot-memory-size=1'))

    def test_refuses_data_reset(self):
        self.make_base()
        self.assertRefused(self.run_tool('--arg', 'data-reset=1'))
        self.make_base(args=ARGS + ' data-reset=1')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'))
        self.assertRefused(self.run_tool('--set', 'darwinboot-memory-size=1'))

    def test_refuses_data_reset_in_confirm_args(self):
        self.make_base(toml_bytes=toml() + b'\n[[entry]]\nname = "install"\nconfirm_args = ["", "data-reset=1"]\n')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'))
        self.assertRefused(self.run_tool('--set', 'darwinboot-memory-size=1'))

    def test_base_named_like_the_temporary_file_survives(self):
        self.base = self.out.with_name(self.out.name + '.tmp')
        self.make_base()
        result = self.run_tool('--arg', 'memory-outside=0')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)
        self.assertFalse(self.out.exists())

    def test_refuses_duplicate_and_malformed_arguments(self):
        self.make_base()
        for text in ('debug=0x1', 'a b=1', 'x="y"'):
            with self.subTest(text=text):
                self.assertRefused(self.run_tool('--arg', text))

    def test_refuses_line_over_1000_bytes(self):
        self.make_base(args='k=' + 'v' * 988)
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'))

    def test_refuses_nothing_to_do(self):
        self.make_base()
        self.assertRefused(self.run_tool())


if __name__ == '__main__':
    unittest.main()
