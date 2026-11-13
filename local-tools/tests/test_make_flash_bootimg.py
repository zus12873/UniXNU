"""Black-box tests of local-tools/make-flash-bootimg.py: each one builds a small header-v4 boot image whose ramdisk is a
FAT32 volume, runs the tool as a command and inspects the image it writes.

    python3 -I -m unittest discover -s local-tools/tests -v

Needs GNU mtools (mformat, mcopy) on PATH, as the tool itself does.
"""
import hashlib
import os
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
FILES = {
    'EFI/UniXNU/unixnu.toml': b'[boot]\ntimeout = 5\n',
    'EFI/UniXNU/Payloads/kernel.macho': bytes(range(256)) * (3 * MIB // 256),
    'EFI/UniXNU/Payloads/kernel.macho.crypto-hmac.json': b'{"hmac": "fixture"}\n',
}


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
        subprocess.run(['mformat', '-C', '-F', '-T', str(size_mib * 2048), '-v', 'SHENGESP', '-N', '53484e47', '-i', str(image), '::'],
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
    struct.pack_into('<8sIIII', header, 0, b'ANDROID!', len(KERNEL), len(ramdisk), 0, 1584)
    struct.pack_into('<I', header, 40, version)
    struct.pack_into('<I', header, 1580, signature)
    path.write_bytes(bytes(header) + KERNEL.ljust(pages(len(KERNEL)), b'\0') + ramdisk.ljust(pages(len(ramdisk)), b'\0') + bytes(signature))
    return path


def run_tool(*args):
    return subprocess.run([sys.executable, '-I', str(TOOL), *map(str, args)], capture_output=True, text=True)


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

    def test_volume_label_and_serial_preserved(self):
        source = make_source(self.dir / 'source.img')
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 0, result.stderr)
        boot_sector = self.out.read_bytes()[4096 + 8192:][:512]
        self.assertEqual(boot_sector[71:82], b'SHENGESP   ')
        self.assertEqual(struct.unpack_from('<I', boot_sector, 67)[0], 0x53484e47)

    def test_refuses_output_larger_than_partition(self):
        source = make_source(self.dir / 'source.img')
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 40 * MIB)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('partition', result.stderr)
        self.assertFalse(self.out.exists())

    def test_refuses_when_files_do_not_fit(self):
        source = make_source(self.dir / 'source.img', files={'EFI/UniXNU/Payloads/kernel.macho': bytes(45 * MIB)})
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('fit', result.stderr)
        self.assertFalse(self.out.exists())

    def test_refuses_volume_that_is_not_fat32(self):
        source = make_source(self.dir / 'source.img')
        result = run_tool(source, self.out, '--fat-mib', 16, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('FAT32', result.stderr)
        self.assertFalse(self.out.exists())

    def test_refuses_changed_cluster_size(self):
        source = make_source(self.dir / 'source.img', fat_mib=96)
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('cluster', result.stderr)
        self.assertFalse(self.out.exists())

    def test_rejects_source_that_is_not_v4(self):
        source = make_source(self.dir / 'source.img', version=0)
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('header v4', result.stderr)
        self.assertFalse(self.out.exists())

    def test_rejects_source_with_signature(self):
        source = make_source(self.dir / 'source.img', signature=4096)
        result = run_tool(source, self.out, '--fat-mib', 40, '--partition-bytes', 42 * MIB)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('signature', result.stderr)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
