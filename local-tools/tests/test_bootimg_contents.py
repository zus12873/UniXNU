"""Black-box tests of local-tools/bootimg-contents.py: each one writes a small header-v4 boot image, laid out the way
test_make_flash_bootimg.py lays out its sources, runs the tool as a command and reads what it prints.

    python3 -I -B -m unittest discover -s local-tools/tests -v
"""
import hashlib
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / 'bootimg-contents.py'
REFUSAL = 'bootimg-contents: '
PAGE = 4096
KERNEL = bytes((i * 7 + 3) & 0xff for i in range(5000))
RAMDISK = bytes((i * 11 + 1) & 0xff for i in range(9000))


def pages(size):
    return -(-size // PAGE) * PAGE


def make_image(path, kernel=KERNEL, ramdisk=RAMDISK, version=4, signature=0):
    """One header page, the kernel, the ramdisk and a signature region, each padded to whole pages but the last."""
    header = bytearray(PAGE)
    struct.pack_into('<8sIIII', header, 0, b'ANDROID!', len(kernel), len(ramdisk), 0x1c000000, 1584)
    struct.pack_into('<I', header, 40, version)
    struct.pack_into('<I', header, 1580, signature)
    path.write_bytes(bytes(header) + kernel.ljust(pages(len(kernel)), b'\0') + ramdisk.ljust(pages(len(ramdisk)), b'\0')
                     + bytes(signature))
    return path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class BootimgContents(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.dir = Path(work.name)

    def run_tool(self, *args):
        before = self.listing()
        result = subprocess.run([sys.executable, '-I', '-B', str(TOOL), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(self.listing(), before, 'the tool wrote into the directory')
        return result

    def listing(self):
        return {path.name: sha256(path.read_bytes()) for path in self.dir.iterdir()}

    def assertRefused(self, result, *words):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        for word in words:
            self.assertIn(word, result.stderr)

    def first_line(self, image):
        data = image.read_bytes()
        return (f'{image}: v4, kernel {len(KERNEL)} bytes sha256 {hashlib.sha256(KERNEL).hexdigest()}, '
                f'ramdisk {len(RAMDISK)} bytes sha256 {hashlib.sha256(RAMDISK).hexdigest()}, '
                f'{len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}')

    def test_describes_a_v4_image(self):
        for signature in (0, PAGE):
            with self.subTest(signature=signature):
                image = make_image(self.dir / f'boot-{signature}.img', signature=signature)
                result = self.run_tool(image)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [self.first_line(image)])
                self.assertEqual(len(image.read_bytes()), PAGE + 8192 + 12288 + signature)

    def test_payload_that_is_the_ramdisk(self):
        image = make_image(self.dir / 'boot.img')
        payload = self.dir / 'payload.img'
        payload.write_bytes(RAMDISK)
        result = self.run_tool(image, '--payload', payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [self.first_line(image), f'ramdisk is {payload}'])

    def test_refuses_payload_that_differs_in_one_byte(self):
        image = make_image(self.dir / 'boot.img')
        payload = self.dir / 'payload.img'
        payload.write_bytes(RAMDISK[:-1] + bytes([RAMDISK[-1] ^ 1]))
        self.assertRefused(self.run_tool(image, '--payload', payload), sha256(RAMDISK), sha256(payload.read_bytes()))

    def test_refuses_payload_of_another_length(self):
        image = make_image(self.dir / 'boot.img')
        payload = self.dir / 'payload.img'
        # The ramdisk and the zeros that pad it to a whole page: the same bytes the image holds, one page long.
        payload.write_bytes(RAMDISK.ljust(pages(len(RAMDISK)), b'\0'))
        self.assertRefused(self.run_tool(image, '--payload', payload), sha256(RAMDISK), sha256(payload.read_bytes()))

    def test_refuses_header_v0(self):
        self.assertRefused(self.run_tool(make_image(self.dir / 'boot.img', version=0)), 'version 0')

    def test_refuses_another_magic(self):
        image = make_image(self.dir / 'boot.img')
        image.write_bytes(b'VNDRBOOT' + image.read_bytes()[8:])
        self.assertRefused(self.run_tool(image), 'ANDROID!')

    def test_refuses_truncated_image(self):
        image = make_image(self.dir / 'boot.img', signature=PAGE)
        data = image.read_bytes()
        for size in (len(data) - 1, len(data) - PAGE, 100):
            with self.subTest(size=size):
                image.write_bytes(data[:size])
                self.assertRefused(self.run_tool(image), str(size))
        image.write_bytes(data + b'\0')
        self.assertRefused(self.run_tool(image), str(len(data) + 1))

    def test_refuses_missing_files(self):
        self.assertRefused(self.run_tool(self.dir / 'missing.img'), 'missing.img')
        image = make_image(self.dir / 'boot.img')
        self.assertRefused(self.run_tool(image, '--payload', self.dir / 'missing.img'), 'missing.img')


if __name__ == '__main__':
    unittest.main()
