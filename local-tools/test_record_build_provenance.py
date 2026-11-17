#!/usr/bin/env python3
"""Tests of record-build-provenance.py: the chip ID never reaches a record, uncommitted state is reported, a leak refuses to write."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('provenance', HERE / 'record-build-provenance.py')
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


class LocalSettings(unittest.TestCase):
    def test_chip_id_is_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'unixnu.local.toml'
            path.write_text('device = "../UniXNU-sheng"\nunique_chip_id = "ABCDEF12"\nkernel_args = ["vm-swapin-io=1"]\n')
            settings, secrets = provenance.local_settings(path)
            text = json.dumps(settings)
            self.assertNotIn('ABCDEF12', text)
            self.assertEqual(settings['unique_chip_id'], {'present': True})
            self.assertEqual(settings['kernel_args'], ['vm-swapin-io=1'])
            self.assertEqual(secrets, ['ABCDEF12'])

    def test_chip_id_in_a_table_is_redacted(self):
        # unixnu.local.toml keeps its settings under [build].
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'unixnu.local.toml'
            path.write_text('[build]\nout = "/Volumes/X/out"\nunique_chip_id = "ABCDEF12"\n[other]\nlist = [{unique_chip_id = "1234ABCD"}]\n')
            settings, secrets = provenance.local_settings(path)
            text = json.dumps(settings)
            self.assertNotIn('ABCDEF12', text)
            self.assertNotIn('1234ABCD', text)
            self.assertEqual(settings['build']['unique_chip_id'], {'present': True})
            self.assertEqual(sorted(secrets), ['1234ABCD', 'ABCDEF12'])
            self.assertEqual(provenance.build_setting(settings, 'out'), '/Volumes/X/out')

    def test_missing_file(self):
        settings, secrets = provenance.local_settings(Path('/nonexistent/unixnu.local.toml'))
        self.assertEqual(settings, {'present': False})
        self.assertEqual(secrets, [])


class RepoState(unittest.TestCase):
    def test_reports_head_and_uncommitted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.email', 'test@example.invalid')
            git(repo, 'config', 'user.name', 'test')
            (repo / 'a.txt').write_text('one\n')
            git(repo, 'add', 'a.txt')
            git(repo, 'commit', '-q', '-m', 'init')
            head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
            clean = provenance.repo_state(repo)
            self.assertEqual(clean['head'], head)
            self.assertEqual(clean['uncommitted'], [])
            (repo / 'a.txt').write_text('two\n')
            dirty = provenance.repo_state(repo)
            self.assertEqual([entry['path'] for entry in dirty['uncommitted']], ['a.txt'])
            self.assertEqual(dirty['uncommitted'][0]['status'], 'M')
            self.assertEqual(len(dirty['uncommitted'][0]['sha256']), 64)


class Leak(unittest.TestCase):
    def test_refuses_a_record_holding_a_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'record.json'
            with self.assertRaises(SystemExit):
                provenance.write_record({'note': 'chip abcdef12'}, [target], ['ABCDEF12'])
            self.assertFalse(target.exists())

    def test_writes_a_clean_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = [Path(tmp) / 'one/record.json', Path(tmp) / 'two/record.json']
            provenance.write_record({'note': 'clean'}, targets, ['ABCDEF12'])
            for target in targets:
                self.assertEqual(json.loads(target.read_text()), {'note': 'clean'})


if __name__ == '__main__':
    unittest.main()
