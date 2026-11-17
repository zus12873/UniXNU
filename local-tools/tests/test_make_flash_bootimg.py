"""Black-box tests of local-tools/make-flash-bootimg.py: each one builds a small header-v4 boot image whose ramdisk is a
FAT32 volume, runs the tool as a command and inspects the image it writes.

    python3 -I -B -m unittest discover -s local-tools/tests -v

Needs GNU mtools (mformat, mcopy) on PATH, as the tool itself does.
"""
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / 'make-flash-bootimg.py'
MIB = 1 << 20
PAGE = 4096
MTOOLS_ENV = dict(os.environ, MTOOLS_SKIP_CHECK='1', TZ='UTC')
KERNEL = bytes((i * 7 + 3) & 0xff for i in range(5000))
# Not payload.py's SHENGESP / 53484e47, so a tool that writes those constants instead of the source's values is caught.
LABEL, SERIAL = 'FIXTURE1', 0x1234abcd
# Header fields the tool must carry over untouched.
OS_VERSION = 0x1c000000
CMDLINE = b'fixture-cmdline keep=1'
REFUSAL = 'make-flash-bootimg: '
FILES = {
    'EFI/UniXNU/unixnu.toml': b'[boot]\ntimeout = 5\n',
    'EFI/UniXNU/Payloads/kernel.macho': bytes(range(256)) * (3 * MIB // 256),
    'EFI/UniXNU/Payloads/kernel.macho.crypto-hmac.json': b'{"hmac": "fixture"}\n',
}
# Stands in for mcopy: on a write into the volume (-Q) it changes the file being written, as a faulty copy would, then
# runs the real mcopy. Extractions (no -Q) pass through untouched.
FAULTY_MCOPY = '''import os, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
if '-Q' in args:
    entry = Path(args[-2])
    target = entry if entry.is_file() else next(p for p in sorted(entry.rglob('*')) if p.is_file())
    with target.open('ab') as stream:
        stream.write(b'!')
sys.exit(subprocess.call([os.environ['REAL_MCOPY'], *args]))
'''


def pages(size):
    return -(-size // PAGE) * PAGE


def make_volume(image, size_mib, files):
    """A FAT32 volume made the way scripts/unixnu/payload.py makes the payload volume."""
    with tempfile.TemporaryDirectory() as stage:
        stage = Path(stage)
        for name, content in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        subprocess.run(['mformat', '-C', '-F', '-T', str(size_mib * 2048), '-v', LABEL, '-N', f'{SERIAL:08x}', '-i', str(image), '::'],
                       env=MTOOLS_ENV, check=True, capture_output=True)
        for entry in sorted(stage.iterdir()):
            subprocess.run(['mcopy', '-i', str(image), '-s', '-Q', '-m', str(entry), '::/'], env=MTOOLS_ENV, check=True, capture_output=True)


def make_source(path, fat_mib=48, files=FILES, version=4, signature=0):
    """A boot image: one header page, the kernel, the volume as the ramdisk and, when asked, a signature region."""
    volume = path.with_suffix('.fat')
    make_volume(volume, fat_mib, files)
    ramdisk = volume.read_bytes()
    volume.unlink()
    header = bytearray(PAGE)
    struct.pack_into('<8sIIII', header, 0, b'ANDROID!', len(KERNEL), len(ramdisk), OS_VERSION, 1584)
    struct.pack_into('<I', header, 40, version)
    header[44:44 + len(CMDLINE)] = CMDLINE
    struct.pack_into('<I', header, 1580, signature)
    path.write_bytes(bytes(header) + KERNEL.ljust(pages(len(KERNEL)), b'\0') + ramdisk.ljust(pages(len(ramdisk)), b'\0') + bytes(signature))
    return path


def run_tool(*args, env=None):
    return subprocess.run([sys.executable, '-I', str(TOOL), *map(str, args)], capture_output=True, text=True, env=env)


def volume_files(volume_bytes):
    """Every file of a volume as {path: sha256}, read back with mcopy."""
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        (work / 'volume.img').write_bytes(volume_bytes)
        subprocess.run(['mcopy', '-i', str(work / 'volume.img'), '-s', '-n', '::/EFI', str(work / 'out')], env=MTOOLS_ENV, check=True, capture_output=True)
        return {'EFI/' + p.relative_to(work / 'out').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (work / 'out').rglob('*') if p.is_file()}


class MakeFlashBootimg(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.dir = Path(self.work.name)
        self.out = self.dir / 'flash.img'

    def plant_stale_output(self):
        """An OUTPUT left by an earlier run: a refused run must remove it, so that it cannot be flashed by mistake."""
        self.out.write_bytes(b'image from an earlier run')

    def assertRefused(self, result, word):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn(word, result.stderr)
        self.assertFalse(self.out.exists(), 'a refused run left OUTPUT behind')

    def test_repack_keeps_kernel_and_files(self):
        source = make_source(self.dir / 'source.img')
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 0, result.stderr)
        image = self.out.read_bytes()
        magic, kernel_size, ramdisk_size = struct.unpack_from('<8sII', image, 0)
        self.assertEqual(magic, b'ANDROID!')
        self.assertEqual(struct.unpack_from('<I', image, 40)[0], 4)
        self.assertEqual(kernel_size, 5000)
        self.assertEqual(ramdisk_size, 41943040)
        self.assertEqual(struct.unpack_from('<I', image, 1580)[0], 0)
        self.assertEqual(len(image), 4096 + 8192 + 41943040)
        self.assertEqual(image[4096:4096 + 8192], KERNEL + bytes(8192 - 5000))
        self.assertEqual(volume_files(image[4096 + 8192:]), {name: hashlib.sha256(content).hexdigest() for name, content in FILES.items()})

    def test_header_page_unchanged_except_ramdisk_size(self):
        source = make_source(self.dir / 'source.img')
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = bytearray(source.read_bytes()[:PAGE])
        struct.pack_into('<I', expected, 12, 40 * MIB)
        self.assertEqual(self.out.read_bytes()[:PAGE], bytes(expected))

    def test_volume_label_and_serial_preserved(self):
        source = make_source(self.dir / 'source.img')
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 0, result.stderr)
        boot_sector = self.out.read_bytes()[4096 + 8192:][:512]
        self.assertEqual(boot_sector[71:82], LABEL.encode().ljust(11))
        self.assertEqual(struct.unpack_from('<I', boot_sector, 67)[0], SERIAL)

    def test_refuses_output_larger_than_partition(self):
        source = make_source(self.dir / 'source.img')
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 40 * MIB), 'partition')

    def test_refuses_when_files_do_not_fit(self):
        source = make_source(self.dir / 'source.img', files={'EFI/UniXNU/Payloads/kernel.macho': bytes(45 * MIB)})
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB), 'fit')

    def test_refuses_volume_that_is_not_fat32(self):
        # 32 MiB of 512-byte clusters is 64496 clusters, just under the 65525 that FAT32 needs.
        source = make_source(self.dir / 'source.img')
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 32, '--partition-bytes', 42 * MIB), 'FAT32')

    def test_refuses_changed_cluster_size(self):
        source = make_source(self.dir / 'source.img', fat_mib=96)
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB), 'cluster')

    def test_rejects_source_that_is_not_v4(self):
        source = make_source(self.dir / 'source.img', version=0)
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB), 'header v4')

    def test_rejects_source_with_signature(self):
        source = make_source(self.dir / 'source.img', signature=4096)
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB), 'signature')

    def test_refuses_when_read_back_differs(self):
        source = make_source(self.dir / 'source.img')
        shim = self.dir / 'shim'
        shim.mkdir()
        (shim / 'mcopy').write_text(f'#!{sys.executable} -I\n' + FAULTY_MCOPY)
        (shim / 'mcopy').chmod(0o755)
        env = dict(os.environ, PATH=f'{shim}{os.pathsep}{os.environ["PATH"]}', REAL_MCOPY=shutil.which('mcopy'))
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB, env=env), 'differ')

    def test_refuses_same_source_and_output(self):
        source = make_source(self.dir / 'source.img')
        original = source.read_bytes()
        os.link(source, self.dir / 'link.img')
        for output in (source, self.dir / 'link.img'):
            with self.subTest(output=output.name):
                result = run_tool(source, output, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
                self.assertIn('same', result.stderr)
                self.assertEqual(source.read_bytes(), original)
                self.assertEqual(output.read_bytes(), original)

    def test_missing_mtools_removes_stale_output(self):
        path = os.pathsep.join(('/usr/bin', '/bin'))
        if shutil.which('mformat', path=path):
            self.skipTest('mtools is installed in /usr/bin or /bin')
        source = make_source(self.dir / 'source.img')
        self.plant_stale_output()
        self.assertRefused(run_tool(source, self.out, env=dict(os.environ, PATH=path)), 'mtools')


if __name__ == '__main__':
    unittest.main()
