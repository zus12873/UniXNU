#!/usr/bin/env python3
"""Say what a header-v4 Android boot image holds, and check which payload is its ramdisk. Reads only, writes nothing.

    bootimg-contents.py IMAGE [--payload FILE]

The image is the header page (magic ANDROID!, kernel_size and ramdisk_size at +8, header_version 4 at +40, signature_size
at +1580), the kernel from 4096, the ramdisk from 4096 + roundup(kernel_size, 4096) and the signature region behind it;
the file is exactly 4096 + roundup(kernel_size, 4096) + roundup(ramdisk_size, 4096) + signature_size bytes. Prints

    IMAGE: v4, kernel K bytes sha256 H, ramdisk R bytes sha256 H, N bytes, sha256 H

(the last pair is the whole file). With --payload FILE the ramdisk must be FILE byte for byte; then a second line says
`ramdisk is FILE`. Every boot image of one firmware has the same size, so this is how to tell which payload one carries.
It refuses, with a message on stderr and a non-zero exit, a file that is not a v4 image, sizes that do not add up to the
file's length, a ramdisk that is not FILE, and a file it cannot read.
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

PREFIX = 'bootimg-contents: '
PAGE = 4096


class Refusal(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.exit(f'{PREFIX}{message}')


def pages(size):
    return -(-size // PAGE) * PAGE


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def parts(path, data):
    """(kernel, ramdisk) of a header-v4 boot image, as views of data."""
    if data[:8] != b'ANDROID!':
        raise Refusal(f'{path} is not an Android boot image (it does not start with ANDROID!)')
    if len(data) < PAGE:
        raise Refusal(f'{path}: {len(data)} bytes, shorter than the {PAGE}-byte header page')
    kernel_size, ramdisk_size = struct.unpack_from('<II', data, 8)
    version = struct.unpack_from('<I', data, 40)[0]
    if version != 4:
        raise Refusal(f'{path}: header version {version}, expected 4')
    signature_size = struct.unpack_from('<I', data, 1580)[0]
    expected = PAGE + pages(kernel_size) + pages(ramdisk_size) + signature_size
    if len(data) != expected:
        raise Refusal(f'{path}: {len(data)} bytes, but the header gives {PAGE} + {pages(kernel_size)} + {pages(ramdisk_size)} '
                      f'+ {signature_size} = {expected} (kernel {kernel_size}, ramdisk {ramdisk_size}, signature {signature_size})')
    view = memoryview(data)
    ramdisk_at = PAGE + pages(kernel_size)
    return view[PAGE:PAGE + kernel_size], view[ramdisk_at:ramdisk_at + ramdisk_size]


def main():
    parser = Parser(description='Say what a header-v4 boot image holds; with --payload, check that FILE is its ramdisk.')
    parser.add_argument('image', type=Path)
    parser.add_argument('--payload', type=Path, metavar='FILE')
    args = parser.parse_args()
    try:
        data = args.image.read_bytes()
        kernel, ramdisk = parts(args.image, data)
        print(f'{args.image}: v4, kernel {len(kernel)} bytes sha256 {sha256(kernel)}, '
              f'ramdisk {len(ramdisk)} bytes sha256 {sha256(ramdisk)}, {len(data)} bytes, sha256 {sha256(data)}', flush=True)
        if args.payload is not None:
            payload = args.payload.read_bytes()
            if ramdisk != payload:
                raise Refusal(f'the ramdisk ({len(ramdisk)} bytes, sha256 {sha256(ramdisk)}) is not {args.payload} '
                              f'({len(payload)} bytes, sha256 {sha256(payload)})')
            print(f'ramdisk is {args.payload}')
    except Refusal as refusal:
        sys.exit(f'{PREFIX}{refusal}')
    except OSError as error:
        sys.exit(f'{PREFIX}{error.filename}: {error.strerror}' if error.filename and error.strerror else f'{PREFIX}{error}')


if __name__ == '__main__':
    main()
