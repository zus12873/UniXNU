"""Tests of local-tools/tablet-ssh.py: how it tells the tablet from every other host that answers on port 22.

    python3 -I -B -m unittest discover -s local-tools/tests -v

The addresses are from the documentation ranges; nothing is sent to a network.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('tablet_ssh', ROOT / 'local-tools/tablet-ssh.py')
tablet_ssh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tablet_ssh)

KEY = 'AAAAC3NzaC1lZDI1NTE5AAAAIJ0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b'
OTHER = 'AAAAC3NzaC1lZDI1NTE5AAAAIK1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c'
KNOWN = f'192.0.2.7 ssh-ed25519 {KEY}\n'


class KnownHost(unittest.TestCase):
    def test_reads_the_alias_and_the_key(self):
        self.assertEqual(tablet_ssh.known_host(KNOWN), ('192.0.2.7', {('ssh-ed25519', KEY)}))

    def test_one_host_may_have_several_keys(self):
        text = KNOWN + f'192.0.2.7 ecdsa-sha2-nistp256 {OTHER}\n# a comment\n\n'
        self.assertEqual(tablet_ssh.known_host(text), ('192.0.2.7', {('ssh-ed25519', KEY), ('ecdsa-sha2-nistp256', OTHER)}))

    def test_refuses_no_host_two_hosts_and_a_hashed_name(self):
        for text, words in (('', 'has no host'), (KNOWN + f'198.51.100.9 ssh-ed25519 {OTHER}\n', 'names 2 hosts'),
                            (f'|1|c2FsdA==|aGFzaA== ssh-ed25519 {KEY}\n', 'hashed')):
            with self.assertRaises(tablet_ssh.Refusal) as refused:
                tablet_ssh.known_host(text)
            self.assertIn(words, str(refused.exception))


class Match(unittest.TestCase):
    KEYS = {('ssh-ed25519', KEY)}

    def test_the_same_key_at_another_address_is_the_tablet(self):
        scan = f'# 203.0.113.231:22 SSH-2.0-OpenSSH_10.0\n203.0.113.231 ssh-ed25519 {KEY}\n'
        self.assertTrue(tablet_ssh.is_tablet(self.KEYS, scan))

    def test_another_key_is_another_host(self):
        self.assertFalse(tablet_ssh.is_tablet(self.KEYS, f'203.0.113.8 ssh-ed25519 {OTHER}\n'))

    def test_the_same_blob_under_another_key_type_does_not_count(self):
        self.assertFalse(tablet_ssh.is_tablet(self.KEYS, f'203.0.113.8 ssh-rsa {KEY}\n'))

    def test_no_answer_is_not_the_tablet(self):
        self.assertFalse(tablet_ssh.is_tablet(self.KEYS, ''))


class Neighbours(unittest.TestCase):
    def test_lists_answered_entries_once_and_skips_the_rest(self):
        arp = ('? (203.0.113.1) at 0:11:22:33:44:55 on en0 ifscope [ethernet]\n'
               '? (203.0.113.9) at (incomplete) on en0 ifscope [ethernet]\n'
               'tablet.local (203.0.113.231) at 66:77:88:99:aa:bb on en0 ifscope [ethernet]\n'
               '? (203.0.113.1) at 0:11:22:33:44:55 on en0 ifscope [ethernet]\n'
               '? (203.0.113.255) at ff:ff:ff:ff:ff:ff on en0 ifscope [ethernet]\n'
               '? (224.0.0.251) at 1:0:5e:0:0:fb on en0 ifscope permanent [ethernet]\n')
        self.assertEqual(tablet_ssh.neighbours(arp), ['203.0.113.1', '203.0.113.231'])


class Candidates(unittest.TestCase):
    def test_the_remembered_address_comes_first_and_only_once(self):
        self.assertEqual(tablet_ssh.candidates('203.0.113.231', ['203.0.113.1', '203.0.113.231']),
                         ['203.0.113.231', '203.0.113.1'])

    def test_no_remembered_address(self):
        self.assertEqual(tablet_ssh.candidates(None, ['203.0.113.1']), ['203.0.113.1'])


class Subnet(unittest.TestCase):
    def test_every_other_host_of_a_small_subnet(self):
        hosts = tablet_ssh.subnet_hosts('203.0.113.20', '0xffffff00')
        self.assertEqual(len(hosts), 253)
        self.assertNotIn('203.0.113.20', hosts)
        self.assertEqual((hosts[0], hosts[-1]), ('203.0.113.1', '203.0.113.254'))

    def test_a_large_subnet_is_not_swept(self):
        self.assertEqual(tablet_ssh.subnet_hosts('198.18.0.20', '0xffff0000'), [])


if __name__ == '__main__':
    unittest.main()
