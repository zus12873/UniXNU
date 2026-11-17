#!/usr/bin/env python3
"""Rebuild a v4 vendor_boot without its vendor ramdisk (sheng GKI experiment).

    make-vendor-boot-noramdisk.py STOCK_VENDOR_BOOT OUT

Keeps the header fields (addresses, cmdline, name), the DTB section and the bootconfig byte for byte; sets
vendor_ramdisk_size and the ramdisk table to zero and drops those sections. With init_boot erased, the v4
initrd the ABL hands over should then start with the boot image's own ramdisk (the UniXNU payload FAT).
Restore the partition with the stock image from the ROM: fastboot flash vendor_boot_a vendor_boot.img
"""
import hashlib
import struct
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
vb = src.read_bytes()
if vb[:8] != b'VNDRBOOT' or struct.unpack_from('<I', vb, 8)[0] != 4:
    sys.exit('not a v4 vendor_boot image')
page, = struct.unpack_from('<I', vb, 12)
ramdisk_size, = struct.unpack_from('<I', vb, 24)
header_size, dtb_size = struct.unpack_from('<II', vb, 2096)
table_size, table_entries, table_entry_size, bootconfig_size = struct.unpack_from('<4I', vb, 2112)
pages = lambda n: -(-n // page) * page
offset = pages(header_size)
ramdisk_off = offset
dtb_off = ramdisk_off + pages(ramdisk_size)
table_off = dtb_off + pages(dtb_size)
bootconfig_off = table_off + pages(table_size)
dtb = vb[dtb_off:dtb_off + dtb_size]
bootconfig = vb[bootconfig_off:bootconfig_off + bootconfig_size]
if dtb[:4] != b'\xd0\x0d\xfe\xed':
    sys.exit('DTB section does not start with an FDT header')
header = bytearray(vb[:header_size])
struct.pack_into('<I', header, 24, 0)               # vendor_ramdisk_size
struct.pack_into('<II', header, 2112, 0, 0)         # ramdisk table size, entry count (entry size kept)
pad = lambda b: b + bytes(pages(len(b)) - len(b))
image = pad(bytes(header)) + pad(dtb) + pad(bootconfig)
out.write_bytes(image)
print(f'{out}: page {page}, dtb {dtb_size}, bootconfig {bootconfig_size} ({bootconfig!r}), '
      f'dropped ramdisk {ramdisk_size} and table {table_entries}x{table_entry_size}; {len(image)} bytes, '
      f'sha256 {hashlib.sha256(image).hexdigest()}')
