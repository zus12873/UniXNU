#!/usr/bin/env python3
"""Wait for the tablet in fastboot, start a boot image once, and report whether the bootloader let go of it.

    boot-sheng.py IMAGE [--serial SERIAL] [--wait SECONDS]

`fastboot boot` answers OKAY as soon as the image is received; a refused image shows only afterwards, when the ABL
answers getvar again. So after the boot this keeps asking for 45 s: silence means the image is running.
A refused boot leaves the ABL answering "Load Error" to every later boot until `fastboot reboot bootloader`.
The serial is never written here (it is this unit's platform seed): pass it with --serial or connect one device.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('image', type=Path)
parser.add_argument('--serial')
parser.add_argument('--wait', type=int, default=600, help='seconds to wait for the tablet to appear in fastboot')
args = parser.parse_args()
if not args.image.is_file():
    sys.exit(f'{args.image}: no such boot image')
fastboot = ['fastboot'] + (['-s', args.serial] if args.serial else [])


def var(name, timeout=3):
    """fastboot getvar NAME, or None when the bootloader does not answer in time."""
    try:
        done = subprocess.run(fastboot + ['getvar', name], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    for line in (done.stderr + done.stdout).splitlines():
        if line.startswith(name + ':'):
            return line.split(':', 1)[1].strip()
    return None


start = time.time()
print(f'waiting up to {args.wait} s for the tablet in fastboot ...', flush=True)
while var('product') != 'sheng':
    if time.time() - start > args.wait:
        sys.exit('no tablet in fastboot: hold Power + Volume Down for about 10 s until FASTBOOT shows')
    time.sleep(1)
print(f'fastboot answered after {time.time() - start:.0f} s: slot {var("current-slot")}, unlocked {var("unlocked")}, '
      f'battery {var("battery-voltage")} mV', flush=True)
time.sleep(3)   # a boot sent right as the ABL enumerates fails with usb_write errors
boot = subprocess.run(fastboot + ['boot', str(args.image)], capture_output=True, text=True, timeout=300)
print((boot.stderr + boot.stdout).strip(), flush=True)
if boot.returncode:
    sys.exit('fastboot boot failed; run `fastboot reboot bootloader`, wait for FASTBOOT and try again')
sent = time.time()
while time.time() - sent < 45:
    if var('product', 2) == 'sheng':
        sys.exit(f'the bootloader is back after {time.time() - sent:.0f} s: it refused the image')
    time.sleep(2)
print('the bootloader stayed away for 45 s: the image is running')
