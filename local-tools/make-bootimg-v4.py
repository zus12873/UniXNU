#!/usr/bin/env python3
"""Repack the kernel of a header-v0 boot image as header v4 with an empty signature region (diagnostic).

    make-v4-test.py V0_IMAGE MKBOOTIMG OUT [RAMDISK]

The v0 kernel blob (BootShim + firmware volume, gzip, appended DTB) is copied byte for byte. mkbootimg writes a
4096-byte signature region for v4; the erhai record found that refused (Load Error) and an empty region started.
So signature_size (+1580) is set to 0 and the trailing signature page, which must be all zeros, is dropped.
"""
import hashlib
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

v0, mkbootimg, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ramdisk = Path(sys.argv[4]) if len(sys.argv) > 4 else None
data = v0.read_bytes()
if data[:8] != b'ANDROID!' or struct.unpack_from('<I', data, 40)[0] != 0:
    sys.exit('input is not a header v0 boot image')
kernel_size, _, ramdisk_size = struct.unpack_from('<III', data, 8)
page = struct.unpack_from('<I', data, 36)[0]
kernel = data[page:page + kernel_size]
with tempfile.TemporaryDirectory() as work:
    work = Path(work)
    (work / 'kernel').write_bytes(kernel)
    rd = ramdisk or work / 'ramdisk'
    if not ramdisk:
        rd.write_bytes(b'')
    subprocess.run([sys.executable, str(mkbootimg), '--header_version', '4', '--kernel', str(work / 'kernel'),
                    '--ramdisk', str(rd), '-o', str(work / 'v4.img')], check=True)
    image = bytearray((work / 'v4.img').read_bytes())
assert image[:8] == b'ANDROID!' and struct.unpack_from('<I', image, 40)[0] == 4
k, r, _osv, header_size = struct.unpack_from('<4I', image, 8)
signature = struct.unpack_from('<I', image, 1580)[0]
pages = lambda n: -(-n // 4096) * 4096
expected = 4096 + pages(k) + pages(r) + signature
if len(image) != expected or k != kernel_size:
    sys.exit(f'unexpected v4 layout: {len(image)} != {expected}')
if signature:
    tail = image[-signature:]
    if any(tail):
        sys.exit('signature region is not empty zeros')
    del image[-signature:]
    struct.pack_into('<I', image, 1580, 0)
if image[4096:4096 + k] != kernel:
    sys.exit('kernel bytes differ')
out.write_bytes(image)
print(f'{out}: v4, kernel {k}, ramdisk {r}, signature 0, {len(image)} bytes, sha256 {hashlib.sha256(image).hexdigest()}')
