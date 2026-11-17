"""Tests for make-bootimg-v0-template.py (run: python3 -I -B -m unittest discover -s local-tools -p 'test_make_bootimg_v0_template.py')."""
import gzip
import hashlib
import lzma
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOOL = HERE / 'make-bootimg-v0-template.py'
sys.path.insert(0, str(ROOT / 'scripts'))
from unixnu import boot_template  # noqa: E402

PIN = '8fed0304acdfac65421f8523d6be727311ee5f6f8826ac20736735de0e533124'
GUID = '1b64af87-8415-4b57-9b16-680d70913b9f'
TEMPLATE = ROOT / 'out/downloads/cd-template-218fdcce/sheng-recovery-218FDCCE-boot.img.xz'
FD = ROOT / 'out/flash/SILICIUM_UEFI.bigwin-8407c84f.fd'
PAYLOAD = Path('/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/payload/payload.bigwin-ctl6.img')
MKBOOTIMG = ROOT.parent / 'uefi-sheng/Resources/Scripts/mkbootimg.py'


def run_tool(template, fd, payload, out):
    return subprocess.run([sys.executable, '-I', '-B', str(TOOL), str(template), str(fd), str(payload), str(MKBOOTIMG),
                           str(out), '--sha256', PIN, '--loader-guid', GUID], capture_output=True, text=True)


class Refusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.payload = self.dir / 'payload.img'
        self.payload.write_bytes(b'\0' * 512 + b'args = "debug=0x14e memory-outside=0"\n')
        self.fake_template = self.dir / 'template.img.xz'
        self.fake_template.write_bytes(lzma.compress(b'not a template'))
        self.fd = self.dir / 'fw.fd'
        self.fd.write_bytes(b'\0' * 4096)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refuses_existing_output(self):
        out = self.dir / 'boot-v0-cd.test.img'
        out.write_bytes(b'keep me')
        result = run_tool(self.fake_template, self.fd, self.payload, out)
        self.assertEqual(result.returncode, 1)
        self.assertIn('exists', result.stderr)
        self.assertEqual(out.read_bytes(), b'keep me')

    def test_refuses_output_without_v0_cd_name(self):
        out = self.dir / 'boot-v4-flash.test.img'
        result = run_tool(self.fake_template, self.fd, self.payload, out)
        self.assertEqual(result.returncode, 1)
        self.assertIn('boot-v0-cd.', result.stderr)
        self.assertFalse(out.exists())

    def test_refuses_wrong_template_checksum(self):
        out = self.dir / 'boot-v0-cd.test.img'
        result = run_tool(self.fake_template, self.fd, self.payload, out)
        self.assertEqual(result.returncode, 1)
        self.assertIn('checksum', result.stderr)
        self.assertFalse(out.exists())

    def test_refuses_data_reset_payload(self):
        self.payload.write_bytes(b'\0' * 512 + b'args = "data-reset=1 debug=0x14e"\n')
        out = self.dir / 'boot-v0-cd.test.img'
        result = run_tool(self.fake_template, self.fd, self.payload, out)
        self.assertEqual(result.returncode, 1)
        self.assertIn('data-reset', result.stderr)
        self.assertFalse(out.exists())


class EndToEnd(unittest.TestCase):
    def test_end_to_end_with_cached_inputs(self):
        for path in (TEMPLATE, FD, PAYLOAD, MKBOOTIMG):
            if not path.is_file():
                self.skipTest(f'missing input {path}')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'boot-v0-cd.e2e.img'
            result = run_tool(TEMPLATE, FD, PAYLOAD, out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(': v0, kernel ', result.stdout.strip().splitlines()[-1])
            image = out.read_bytes()
        template = lzma.decompress(TEMPLATE.read_bytes())
        shim, template_fw, tree, _ = boot_template.parse_boot_image(template)
        self.assertEqual(image[:8], b'ANDROID!')
        kernel_size, _, ramdisk_size = struct.unpack_from('<3I', image, 8)
        page, header_version, os_version = struct.unpack_from('<3I', image, 36)
        self.assertEqual((header_version, page), (0, 4096))
        self.assertEqual(os_version, struct.unpack_from('<I', template, 44)[0])
        kernel = image[page:page + kernel_size]
        start = page + ((kernel_size + page - 1) // page) * page
        self.assertEqual(image[start:start + ramdisk_size], PAYLOAD.read_bytes())
        unpacker = zlib.decompressobj(16 + zlib.MAX_WBITS)
        combined = unpacker.decompress(kernel)
        self.assertTrue(unpacker.eof)
        self.assertEqual(unpacker.unused_data, tree)
        self.assertEqual(combined[:len(shim)], shim)
        firmware = combined[len(shim):]
        self.assertEqual(len(firmware), len(template_fw))
        ours = boot_template.loader_pe(FD.read_bytes(), GUID)
        self.assertEqual(boot_template.loader_pe(firmware, GUID), ours)
        self.assertNotEqual(boot_template.loader_pe(template_fw, GUID), ours)


if __name__ == '__main__':
    unittest.main()
