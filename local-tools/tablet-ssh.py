#!/usr/bin/env python3
"""tablet-ssh.py [--find] [COMMAND ...]: an SSH session to the tablet, which is found by its host key.

The tablet's address changes with the network it joins. An address from notes can belong to a subnet this Mac reaches through
a tunnel interface, and such a route accepts a connection on every port and then closes it: that looks like a broken sshd on
the tablet. So no address is taken on trust. The hosts on this Mac's default interface that listen on port 22 are asked for
their host key (ssh-keyscan), and the one whose key is in out/ssh/known_hosts is the tablet. The remembered address is asked
first, then the ARP neighbours, then every other host of the subnet (subnets of up to 1022 hosts).

Files, all in out/ssh/ (ignored by git):
  known_hosts      one host: the name the key was first stored under, used as ssh's HostKeyAlias
  tablet_ed25519   the key the tablet accepts
  tablet-account   the login name on the tablet, one line
  tablet-address   the address found last time (written here; never printed)

--find only looks for the tablet and says whether it was found. Without a COMMAND the session is interactive.
"""
import ipaddress
import os
import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / 'out/ssh'
SWEEP_LIMIT = 1022


class Refusal(Exception):
    pass


def known_host(text):
    """(alias, {(key type, key)}) of a known_hosts file that holds one host."""
    names, keys = [], set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[0].startswith('#'):
            continue
        if fields[0].startswith('|'):
            raise Refusal('known_hosts has a hashed host name; the HostKeyAlias cannot be read from it')
        if fields[0] not in names:
            names.append(fields[0])
        keys.add((fields[1], fields[2]))
    if not names:
        raise Refusal('known_hosts has no host')
    if len(names) > 1:
        raise Refusal(f'known_hosts names {len(names)} hosts, expected the tablet alone')
    return names[0].split(',')[0], keys


def is_tablet(keys, scan):
    """Whether ssh-keyscan's output holds one of the tablet's keys."""
    for line in scan.splitlines():
        fields = line.split()
        if len(fields) >= 3 and not fields[0].startswith('#') and (fields[1], fields[2]) in keys:
            return True
    return False


def neighbours(arp):
    """The unicast addresses `arp -an` has a hardware address for, each once, in its order."""
    found = []
    for address, hardware in re.findall(r'\((\d+\.\d+\.\d+\.\d+)\) at (\S+)', arp):
        if hardware in ('(incomplete)', 'ff:ff:ff:ff:ff:ff') or ipaddress.ip_address(address).is_multicast:
            continue
        if address not in found:
            found.append(address)
    return found


def candidates(remembered, others):
    """The addresses to ask, the remembered one first."""
    order = [remembered] if remembered else []
    return order + [address for address in others if address not in order]


def subnet_hosts(address, netmask):
    """Every other host of the interface's subnet; none when the subnet has more than SWEEP_LIMIT hosts."""
    network = ipaddress.ip_network(f'{address}/{bin(int(netmask, 16)).count("1")}', strict=False)
    if network.num_addresses - 2 > SWEEP_LIMIT:
        return []
    return [str(host) for host in network.hosts() if str(host) != address]


def output(*command):
    return subprocess.run(command, capture_output=True, text=True, check=False).stdout


def listens(address):
    try:
        with socket.create_connection((address, 22), timeout=1):
            return True
    except OSError:
        return False


def find(keys, remembered):
    """The address whose sshd shows one of keys, or None."""
    interface = re.search(r'interface: (\S+)', output('route', '-n', 'get', 'default'))
    if not interface:
        raise Refusal('this Mac has no default route')
    own = re.search(r'inet (\S+) netmask (\S+)', output('ifconfig', interface[1]))
    if not own:
        raise Refusal(f'{interface[1]} has no IPv4 address')
    sweep = subnet_hosts(own[1], own[2])
    if remembered and sweep and remembered not in sweep:
        remembered = None   # the remembered address is on another subnet: whatever answers there is not asked
    asked = set()
    for group in (candidates(remembered, neighbours(output('arp', '-an', '-i', interface[1]))), sweep):
        group = [address for address in group if address not in asked]
        asked.update(group)
        with ThreadPoolExecutor(max_workers=64) as pool:
            open_hosts = [address for address, up in zip(group, pool.map(listens, group)) if up]
            scans = pool.map(lambda address: output('ssh-keyscan', '-T', '4', address), open_hosts)
            for address, scan in zip(open_hosts, scans):
                if is_tablet(keys, scan):
                    return address
    return None


def main(arguments):
    only_find = arguments[:1] == ['--find']
    command = arguments[1:] if only_find else arguments
    try:
        alias, keys = known_host((DIRECTORY / 'known_hosts').read_text())
        account_file, address_file = DIRECTORY / 'tablet-account', DIRECTORY / 'tablet-address'
        if not account_file.is_file():
            raise Refusal(f'{account_file} is missing: write the login name on the tablet into it')
        remembered = address_file.read_text().strip() if address_file.is_file() else None
        address = find(keys, remembered)
    except (Refusal, OSError) as problem:
        print(f'tablet-ssh: {problem}', file=sys.stderr)
        return 2
    if not address:
        print('tablet-ssh: no host on this network shows the tablet\'s key on port 22', file=sys.stderr)
        return 1
    address_file.write_text(address + '\n')
    if only_find:
        print('tablet-ssh: found the tablet')
        return 0
    os.execvp('ssh', ['ssh', '-i', str(DIRECTORY / 'tablet_ed25519'), '-o', 'IdentitiesOnly=yes',
                      '-o', f'UserKnownHostsFile={DIRECTORY / "known_hosts"}', '-o', f'HostKeyAlias={alias}',
                      '-o', 'StrictHostKeyChecking=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                      f'{account_file.read_text().strip()}@{address}', *command])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
