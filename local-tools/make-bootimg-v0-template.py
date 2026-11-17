#!/usr/bin/env python3
"""Wrap a UniXNU payload and our DarwinBoot in the community's qualified v0 boot template.

The community (CrossDarwin boot/sheng-firmware-compat) boots sheng through a SHA-256-pinned Android v0 image: an
ARM64 shim, the board firmware volume and a device tree, gzip-compressed as one kernel. Its `unixnu bootimg` keeps
that transport and swaps only the DarwinBoot module for the current build (scripts/unixnu/boot_template.py). This
tool does the same outside `unixnu bootimg`, so the ramdisk can be any payload volume and nothing in <output>/boot
or out/flash is replaced: the image goes to a new path named boot-v0-cd.*, is read back and checked, and only then
takes its name.

usage: make-bootimg-v0-template.py TEMPLATE_XZ FD PAYLOAD MKBOOTIMG OUT --sha256 PIN --loader-guid GUID
"""
import argparse
import gzip
import hashlib
import lzma
import os
import re
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from unixnu import boot_template  # noqa: E402
from unixnu.util import Error  # noqa: E402

PAGE = 4096
ARGS_LINE = re.compile(rb'args = "([^"\n]*)"')


class Refusal(Exception):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def check_output(out):
    if not out.name.startswith('boot-v0-cd.') or out.suffix != '.img':
        raise Refusal(f'{out}: the output name must start with boot-v0-cd. and end with .img')
    if out.exists() or out.is_symlink():
        raise Refusal(f'{out}: already exists; refusing to replace it')


def check_payload(payload):
    data = payload.read_bytes()
    for line in ARGS_LINE.findall(data):
        if b'data-reset=' in line:
            raise Refusal(f'{payload}: an args line carries data-reset; such an image erases user data')
    return data


def load_template(path, pin):
    if sha256(path) != pin:
        raise Refusal(f'{path}: template checksum differs from the pin {pin}')
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    data = decoder.decompress(path.read_bytes(), max_length=256 << 20)
    if not decoder.eof or decoder.unused_data:
        raise Refusal(f'{path}: template exceeds 256 MiB or has trailing data')
    return data


def mkbootimg_args(image):
    args = []
    for key in ('header_version', 'base', 'kernel_offset', 'ramdisk_offset', 'tags_offset', 'pagesize',
                'os_version', 'os_patch_level'):
        if key in image:
            value = image[key]
            args += [f'--{key}', hex(value) if isinstance(value, int) and key.endswith(('base', 'offset')) else str(value)]
    return args


def verify(path, shim, firmware, tree, payload, encoded_os, pe, guid):
    data = path.read_bytes()
    if data[:8] != b'ANDROID!':
        raise Refusal('built image has no Android magic')
    kernel_size, _, ramdisk_size = struct.unpack_from('<3I', data, 8)
    page, header_version, os_version = struct.unpack_from('<3I', data, 36)
    if header_version != 0 or page != PAGE:
        raise Refusal(f'built image is header v{header_version}, page {page}; expected v0, page {PAGE}')
    if os_version != encoded_os:
        raise Refusal('built image OS metadata differs from the template')
    kernel = data[page:page + kernel_size]
    start = page + ((kernel_size + page - 1) // page) * page
    if data[start:start + ramdisk_size] != payload:
        raise Refusal('built image ramdisk differs from the payload')
    unpacker = zlib.decompressobj(16 + zlib.MAX_WBITS)
    combined = unpacker.decompress(kernel)
    if not unpacker.eof or unpacker.unused_data != tree or combined != shim + firmware:
        raise Refusal('gzip, firmware and appended device tree do not round-trip')
    if boot_template.loader_pe(firmware, guid) != pe:
        raise Refusal('the loader in the built firmware is not the requested one')
    return kernel_size, ramdisk_size, len(data), hashlib.sha256(data).hexdigest()


def build(args):
    out = Path(args.out)
    check_output(out)
    payload = check_payload(Path(args.payload))
    template = load_template(Path(args.template), args.sha256)
    shim, firmware, tree, image = boot_template.parse_boot_image(template)
    source = Path(args.fd).read_bytes()
    if len(source) != len(firmware):
        raise Refusal(f'firmware volume sizes differ: {args.fd} is {len(source)} bytes, the template {len(firmware)}')
    guid = str(__import__('uuid').UUID(args.loader_guid))
    pe = boot_template.loader_pe(source, guid)
    firmware, report = boot_template.replace_loader(firmware, pe, guid)
    encoded_os = struct.unpack_from('<I', template, 44)[0]
    with tempfile.TemporaryDirectory(prefix='.v0-cd-', dir=out.parent) as scratch:
        scratch = Path(scratch)
        kernel_path = scratch / 'Image.gz-dtb'
        kernel_path.write_bytes(gzip.compress(shim + firmware, mtime=0) + tree)
        candidate = scratch / 'boot.img'
        command = [sys.executable, '-I', '-B', args.mkbootimg, '--kernel', str(kernel_path), '--ramdisk', args.payload,
                   '-o', str(candidate)] + mkbootimg_args(image)
        done = subprocess.run(command, capture_output=True, text=True)
        if done.returncode != 0:
            raise Refusal(f'mkbootimg failed: {done.stderr.strip() or done.stdout.strip()}')
        kernel_size, ramdisk_size, total, digest = verify(candidate, shim, firmware, tree, payload, encoded_os, pe, guid)
        if out.exists() or out.is_symlink():
            raise Refusal(f'{out}: appeared while building; refusing to replace it')
        os.link(candidate, out)
    print(f'{out}: v0, kernel {kernel_size}, ramdisk {ramdisk_size}, {total} bytes, sha256 {digest}, '
          f'loader sha256 {report["loader_sha256"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('template')
    parser.add_argument('fd')
    parser.add_argument('payload')
    parser.add_argument('mkbootimg')
    parser.add_argument('out')
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--loader-guid', required=True)
    args = parser.parse_args()
    try:
        build(args)
    except (Refusal, Error, OSError, ValueError, lzma.LZMAError) as error:
        print(f'make-bootimg-v0-template: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
