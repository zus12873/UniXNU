#!/usr/bin/env python3
"""Build a UniXNU payload that boots the sheng log reader (UniXNU-sheng package/linux-log) through our UEFI firmware.

    make-linux-reader-payload.py --boot boot_sheng_singleboot.img --reader sheng-log-reader-v0.img --out reader-payload.img
                                 [--size-mib 64] [--append ARG ...]

The 12 GiB unit's bootloader refuses the reader as a header v0 image (it returns to fastboot after 4 s, with the release device
tree and with its board-id set to 0 0), while it boots our firmware as v4 (make-bootimg-v4.py). So the firmware starts Linux:
the payload's unixnu.toml has one `type = "linux"` entry, and the UniXNU boot manager installs the entry's device tree as the
EFI DTB table, hands the initrd over as LINUX_EFI_INITRD_MEDIA and starts the kernel's EFI stub with the command line.

- the kernel: the release image's gzip kernel, decompressed (an arm64 Image with its PE/COFF EFI stub);
- the device tree: the one appended to that gzip stream (the mainline sheng tree), unchanged;
- the initrd: the ramdisk of the reader image build-linux-log-boot.py made (busybox, init, rebootbl, nvmem-reboot-mode.ko).

The volume is written as scripts/unixnu/payload.py writes a payload (mformat -C -F, mcopy). Pack it with
`make-bootimg-v4.py <output>/boot/boot-bigwin.img ../uefi-sheng/Resources/Scripts/mkbootimg.py OUT reader-payload.img`.
"""
import argparse
import os
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ARGS = 'rdinit=/init console=tty0 loglevel=4 consoleblank=0 clk_ignore_unused pd_ignore_unused'
TOML = '''version = 1
[boot]
timeout = 2
fallback_timeout = 2
default = "reader"
[kits]
autoload = false
[[entry]]
id = "reader"
title = "sheng log reader (Linux)"
type = "linux"
path = "Linux/Image"
dtb = "Linux/sheng.dtb"
initrd = "Linux/initrd.cpio.gz"
args = "{args}"
[[entry]]
id = "reset"
title = "Restart"
type = "action"
action = "reset"
'''


def sections(path):
    image = path.read_bytes()
    if image[:8] != b'ANDROID!':
        raise SystemExit(f'{path}: not an Android boot image')
    kernel_size, _, ramdisk_size, _, _, _, _, page, version, _ = struct.unpack_from('<10I', image, 8)
    if version != 0:
        raise SystemExit(f'{path}: expected header v0')
    kernel = image[page:page + kernel_size]
    start = page + (kernel_size + page - 1) // page * page
    return kernel, image[start:start + ramdisk_size]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--boot', required=True, type=Path, help='ianchb/sm8550-mainline boot_sheng_singleboot.img')
    ap.add_argument('--reader', required=True, type=Path, help='the v0 reader image from build-linux-log-boot.py')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--size-mib', type=int, default=64)
    ap.add_argument('--append', action='append', default=[], help='additional kernel command-line argument')
    a = ap.parse_args()
    gz, _ = sections(a.boot)
    if gz[:2] != b'\x1f\x8b':
        raise SystemExit('the release kernel is not a gzip stream')
    unzip = zlib.decompressobj(31)
    kernel = unzip.decompress(gz)
    dtb = unzip.unused_data
    if kernel[:2] != b'MZ' or kernel[56:60] != b'ARMd':
        raise SystemExit('the kernel is not an arm64 Image with an EFI stub')
    if dtb[:4] != b'\xd0\x0d\xfe\xed':
        raise SystemExit('no device tree follows the gzip stream')
    dtb = dtb[:struct.unpack_from('>I', dtb, 4)[0]]
    _, initrd = sections(a.reader)
    if initrd[:2] != b'\x1f\x8b':
        raise SystemExit('the reader image has no gzip initramfs')
    args = ' '.join([ARGS, *a.append])
    if '"' in args or '\\' in args:
        raise SystemExit('the command line cannot hold quotes or backslashes')
    env = dict(os.environ, MTOOLS_SKIP_CHECK='1', TZ='UTC')
    with tempfile.TemporaryDirectory(prefix='.reader-payload-', dir=a.out.parent) as scratch:
        stage = Path(scratch) / 'stage'
        linux = stage / 'EFI/UniXNU/Linux'
        linux.mkdir(parents=True)
        (stage / 'EFI/UniXNU/unixnu.toml').write_text(TOML.format(args=args))
        (linux / 'Image').write_bytes(kernel)
        (linux / 'sheng.dtb').write_bytes(dtb)
        (linux / 'initrd.cpio.gz').write_bytes(initrd)
        candidate = Path(scratch) / a.out.name
        subprocess.run(['mformat', '-C', '-F', '-T', str(a.size_mib * 2048), '-v', 'SHENGLOG', '-N', '53484e47', '-i', str(candidate), '::'],
                       env=env, check=True, capture_output=True)
        subprocess.run(['mcopy', '-i', str(candidate), '-s', '-Q', '-m', str(stage / 'EFI'), '::/'], env=env, check=True, capture_output=True)
        candidate.replace(a.out)
    print(f'{a.out}: {a.size_mib} MiB, kernel {len(kernel)} bytes, dtb {len(dtb)}, initrd {len(initrd)}, args "{args}"')


if __name__ == '__main__':
    main()
