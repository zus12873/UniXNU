#!/usr/bin/env python3
"""Repack a header-v4 boot image so that it fits a boot partition: the same kernel and the same payload files in a smaller FAT32 volume.

    make-flash-bootimg.py SOURCE OUTPUT [--fat-mib N] [--partition-bytes BYTES]

SOURCE is an image that already starts with `fastboot boot` (out/flash/boot-v4-payload.img): one header page, the kernel
(BootShim + firmware volume) and the UniXNU payload volume as the ramdisk. scripts/unixnu/payload.py will not make that
volume smaller than its files / 0.95, which is 191 MiB for macOS 27.3 and one MiB too many for the 192 MiB boot_a of
sheng. The files themselves take 181 MiB, so this tool moves them, unchanged, into a volume of --fat-mib (190) made with
the same mformat and mcopy arguments, and writes the header again with only ramdisk_size changed.

It refuses, and leaves no OUTPUT, when the source is not a v4 image with an empty signature region, when the new volume
would not be FAT32 or would use another cluster size than the source, when the files do not fit or come back different,
and when the image is larger than --partition-bytes. Needs GNU mtools (brew install mtools). It never flashes anything.
"""
import argparse
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

PAGE = 4096
MIB = 1 << 20
SECTOR = 512
FAT32_MIN_CLUSTERS = 65525
HEADER_V4_BYTES = 1584
MTOOLS_ENV = dict(os.environ, MTOOLS_SKIP_CHECK='1', TZ='UTC')


class Refusal(Exception):
    pass


def pages(size):
    return -(-size // PAGE) * PAGE


def mtools(*command):
    result = subprocess.run([str(part) for part in command], env=MTOOLS_ENV, capture_output=True, text=True)
    if result.returncode:
        raise Refusal(f'{command[0]}: {(result.stderr or result.stdout).strip()}')
    return result.stdout


def read_source(path):
    """The header page, the kernel pages and the ramdisk of a v4 image whose signature region is empty."""
    data = path.read_bytes()
    if data[:8] != b'ANDROID!' or len(data) < PAGE or struct.unpack_from('<I', data, 40)[0] != 4:
        raise Refusal(f'{path} is not a header v4 boot image')
    kernel_size, ramdisk_size = struct.unpack_from('<II', data, 8)
    signature = struct.unpack_from('<I', data, 1580)[0]
    if signature:
        raise Refusal(f'{path} has a signature region of {signature} bytes; only an empty one is known to start')
    if struct.unpack_from('<I', data, 20)[0] != HEADER_V4_BYTES or len(data) != PAGE + pages(kernel_size) + pages(ramdisk_size):
        raise Refusal(f'{path} does not have the layout its header v4 describes')
    kernel_end = PAGE + pages(kernel_size)
    return data[:PAGE], data[PAGE:kernel_end], data[kernel_end:kernel_end + ramdisk_size], kernel_size


def geometry(boot_sector):
    """Cluster bytes, cluster count, label and serial number of a FAT32 volume."""
    bytes_per_sector, per_cluster, reserved, fats, _root, total16 = struct.unpack_from('<HBHBHH', boot_sector, 11)
    fat16_sectors = struct.unpack_from('<H', boot_sector, 22)[0]
    if boot_sector[510:512] != b'\x55\xaa' or bytes_per_sector != SECTOR or not per_cluster or fat16_sectors:
        raise Refusal('the ramdisk is not a FAT32 volume')
    total = total16 or struct.unpack_from('<I', boot_sector, 32)[0]
    clusters = (total - reserved - fats * struct.unpack_from('<I', boot_sector, 36)[0]) // per_cluster
    return per_cluster * SECTOR, clusters, boot_sector[71:82].decode('ascii').rstrip(), struct.unpack_from('<I', boot_sector, 67)[0]


def extract(volume, into):
    into.mkdir()
    mtools('mcopy', '-i', volume, '-s', '-n', '-m', '::/*', into)


def tree(root):
    """Every directory and file below root: {relative path: sha256 of a file, None for a directory}."""
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            for path in sorted(root.rglob('*'))}


def repack(source, output, fat_mib, partition_bytes):
    output.unlink(missing_ok=True)
    header, kernel, ramdisk, kernel_size = read_source(source)
    image_bytes = PAGE + len(kernel) + fat_mib * MIB
    if image_bytes > partition_bytes:
        raise Refusal(f'with a {fat_mib} MiB volume the image is {image_bytes} bytes; the partition holds {partition_bytes}')
    old_cluster, old_clusters, label, serial = geometry(ramdisk[:SECTOR])
    if old_clusters < FAT32_MIN_CLUSTERS:
        raise Refusal('the ramdisk is not a FAT32 volume')
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        (work / 'old.img').write_bytes(ramdisk)
        extract(work / 'old.img', work / 'files')
        files = tree(work / 'files')
        volume = work / 'new.img'
        mtools('mformat', '-C', '-F', '-T', fat_mib * MIB // SECTOR, '-v', label, '-N', f'{serial:08x}', '-i', volume, '::')
        cluster, clusters, _, _ = geometry(volume.read_bytes()[:SECTOR])
        if clusters < FAT32_MIN_CLUSTERS:
            raise Refusal(f'a {fat_mib} MiB volume has {clusters} clusters; FAT32 needs at least {FAT32_MIN_CLUSTERS}')
        if cluster != old_cluster:
            raise Refusal(f'a {fat_mib} MiB volume has {cluster}-byte clusters; the cluster size of the source is {old_cluster}')
        for entry in sorted((work / 'files').iterdir()):
            try:
                mtools('mcopy', '-i', volume, '-s', '-Q', '-m', entry, '::/')
            except Refusal as error:
                raise Refusal(f'the files do not fit a {fat_mib} MiB volume ({error})') from None
        extract(volume, work / 'check')
        if tree(work / 'check') != files:
            raise Refusal('the files read back from the new volume differ from the source')
        free = int(re.sub(r'\D', '', re.search(r'([\d ]+) bytes free', mtools('mdir', '-i', volume, '::/')).group(1)))
        new_header = bytearray(header)
        struct.pack_into('<I', new_header, 12, fat_mib * MIB)
        temporary = output.with_name(output.name + '.tmp')
        with temporary.open('wb') as stream:
            stream.write(new_header)
            stream.write(kernel)
            with volume.open('rb') as new_volume:
                shutil.copyfileobj(new_volume, stream, 16 * MIB)
    if temporary.stat().st_size != image_bytes:
        temporary.unlink()
        raise Refusal(f'wrote {temporary.stat().st_size} bytes, expected {image_bytes}')
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    os.replace(temporary, output)
    count = sum(1 for value in files.values() if value)
    print(f'volume: {label}, serial {serial:08x}, {cluster}-byte clusters, {clusters} clusters, {count} files, {free / MIB:.1f} MiB free')
    print(f'partition: {partition_bytes} bytes, {partition_bytes - image_bytes} to spare')
    print(f'{output}: v4, kernel {kernel_size}, ramdisk {fat_mib * MIB}, signature 0, {image_bytes} bytes, sha256 {digest}')


def main():
    parser = argparse.ArgumentParser(description='Repack a header-v4 boot image with a smaller payload volume.')
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fat-mib', type=int, default=190)
    parser.add_argument('--partition-bytes', type=lambda text: int(text, 0), default=192 * MIB)
    args = parser.parse_args()
    for name in ('mformat', 'mcopy', 'mdir'):
        if not shutil.which(name):
            sys.exit(f'make-flash-bootimg: {name} not found (brew install mtools)')
    try:
        repack(args.source, args.output, args.fat_mib, args.partition_bytes)
    except Refusal as refusal:
        sys.exit(f'make-flash-bootimg: {refusal}')


if __name__ == '__main__':
    main()
