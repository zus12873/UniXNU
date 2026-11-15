"""Black-box tests of local-tools/make-payload-variant.py: each one builds a small FAT payload volume, runs the tool as a
command and reads the files of the volume it writes.

    python3 -I -B -m unittest discover -s local-tools/tests -v

Needs GNU mtools (mformat, mcopy, mtype, mdel) on PATH, as the tool itself does.
"""
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from unixnu.devicetree import node  # noqa: E402
from test_make_flash_bootimg import FAULTY_MCOPY, MTOOLS_ENV, make_volume, volume_files  # noqa: E402

TOOL = ROOT / 'local-tools/make-payload-variant.py'
ADT_TOOL = ROOT / 'local-tools/adt-chosen.py'
REFUSAL = 'make-payload-variant: '
ADT_PATH = 'EFI/UniXNU/Payloads/kernel.macho.adt'
TOML_PATH = 'EFI/UniXNU/unixnu.toml'
KERNEL_PATH = 'EFI/UniXNU/Payloads/kernel.macho'
ARGS = 'debug=0x14e vm_compression_limit=1572864'


def make_adt(size=0x240000000, floor=0x8C0000000):
    return node('device-tree', [('model', b'fixture\0')], [
        # A node in front of /chosen with a property of the same name as one of /chosen.
        node('cpus', [('darwinboot-memory-floor', struct.pack('<Q', 0x1000))], [node('cpu0')]),
        node('chosen', [
            ('random-seed', bytes(range(64))),
            # 8 bytes long, so only its name keeps it from being set.
            ('fixture-eight-bytes', struct.pack('<Q', 0x1234)),
            ('darwinboot-memory-size', struct.pack('<Q', size)),
            ('darwinboot-memory-excluded', bytes(1024)),
            ('darwinboot-memory-floor', struct.pack('<Q', floor)),
            # A darwinboot-* 8-byte property without rules of its own: any 64-bit value goes.
            ('darwinboot-fixture-word', struct.pack('<Q', 5)),
        ], [node('memory-map', [('RAMDisk', bytes(16))])]),
    ])


ADT = make_adt()
KERNEL = bytes((i * 13 + 5) & 0xff for i in range(1 << 20))

# Stands in for mcopy: a write into the volume (-Q) does what was asked and also overwrites another file of the volume.
CHANGES_ANOTHER_FILE = '''import os, subprocess, sys, tempfile
args = sys.argv[1:]
status = subprocess.call([os.environ['REAL_MCOPY'], *args])
if '-Q' in args and not status:
    with tempfile.NamedTemporaryFile() as other:
        other.write(b'not the kernel')
        other.flush()
        status = subprocess.call([os.environ['REAL_MCOPY'], '-D', 'o', '-Q', '-i', args[args.index('-i') + 1], other.name,
                                  '::/EFI/UniXNU/Payloads/kernel.macho'])
sys.exit(status)
'''
# Stands in for mcopy: a write into the volume (-Q) does what was asked, then deletes the file it wrote.
DELETES_THE_WRITTEN_FILE = '''import os, subprocess, sys
args = sys.argv[1:]
status = subprocess.call([os.environ['REAL_MCOPY'], *args])
if '-Q' in args and not status:
    status = subprocess.call([os.environ['REAL_MDEL'], '-i', args[args.index('-i') + 1], args[-1]])
sys.exit(status)
'''
# Stands in for mcopy: a write into the volume (-Q) fails with a message that is not UTF-8.
FAILS_ON_WRITE = '''import os, subprocess, sys
args = sys.argv[1:]
if '-Q' in args:
    sys.stderr.buffer.write(b'mcopy: disk full \\xff\\xfe\\n')
    sys.exit(1)
sys.exit(subprocess.call([os.environ['REAL_MCOPY'], *args]))
'''


def toml(args=ARGS, second=None):
    return (f'[[entry]]\nname = "one"\nargs = "{args}"\n\n'
            f'[[entry]]\nname = "two"\nargs = "{args if second is None else second}"\n').encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class MakePayloadVariant(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.dir = Path(work.name)
        self.base = self.dir / 'base.img'
        self.out = self.dir / 'out.img'
        self.temporary = self.dir / 'out.img.tmp'

    def make_base(self, args=ARGS, adt=ADT, toml_bytes=None):
        make_volume(self.base, 64, {ADT_PATH: adt, TOML_PATH: toml_bytes or toml(args), KERNEL_PATH: KERNEL})
        self.base_sha = sha256(self.base.read_bytes())

    def run_tool(self, *args, base=None, out=None, env=None):
        return subprocess.run([sys.executable, '-I', '-B', str(TOOL), str(base or self.base), str(out or self.out), *args],
                              capture_output=True, text=True, env=env)

    def shim(self, source):
        """An environment whose PATH finds a stand-in for mcopy first."""
        shim = self.dir / 'shim'
        shim.mkdir(exist_ok=True)
        (shim / 'mcopy').write_text(f'#!{sys.executable} -I\n' + source)
        (shim / 'mcopy').chmod(0o755)
        return dict(os.environ, PATH=f'{shim}{os.pathsep}{os.environ["PATH"]}', REAL_MCOPY=shutil.which('mcopy'),
                    REAL_MDEL=shutil.which('mdel'))

    def read(self, image, path):
        return subprocess.run(['mtype', '-i', str(image), f'::/{path}'], env=MTOOLS_ENV, check=True, capture_output=True).stdout

    def adt_chosen(self, blob):
        path = self.dir / 'check.adt'
        path.write_bytes(blob)
        result = subprocess.run([sys.executable, '-I', '-B', str(ADT_TOOL), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.splitlines()

    def last_line(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.out.read_bytes()
        line = result.stdout.splitlines()[-1]
        prefix = f'{self.out}: {len(data)} bytes, sha256 {sha256(data)}, '
        self.assertTrue(line.startswith(prefix), line)
        return line[len(prefix):]

    def accepted(self, *args, **options):
        """The part of the last line behind the sha256 of an accepted run, which is then undone for the next one."""
        result = self.run_tool(*args, **options)
        try:
            return self.last_line(result)
        finally:
            self.assertFalse(self.temporary.exists() or self.temporary.is_symlink(), 'an accepted run left OUT.tmp behind')
            self.out.unlink(missing_ok=True)

    def assertRefused(self, result, word=None, out=None, temporary_left=False):
        out = out or self.out
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        if word is not None:
            self.assertIn(word, result.stderr)
        self.assertFalse(out.exists() or out.is_symlink(), 'a refused run left OUT behind')
        if not temporary_left:
            temporary = out.with_name(out.name + '.tmp')
            self.assertFalse(temporary.exists() or temporary.is_symlink(), 'a refused run left OUT.tmp behind')
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)

    def test_sets_two_properties_and_prepends_an_argument(self):
        self.make_base()
        result = self.run_tool('--set', 'darwinboot-memory-size=0x1E0000000', '--set', 'darwinboot-memory-floor=0x920000000',
                               '--arg', 'memory-outside=0')
        self.assertEqual(self.last_line(result), 'adt: darwinboot-memory-size=0x1e0000000 darwinboot-memory-floor=0x920000000, '
                         'args: memory-outside=0, replaced: unchanged')
        data = self.out.read_bytes()
        adt = self.read(self.out, ADT_PATH)
        self.assertEqual(self.adt_chosen(adt), [
            'darwinboot-memory-size 8 0x1e0000000',
            'darwinboot-memory-excluded 1024 64 empty pairs',
            'darwinboot-memory-floor 8 0x920000000',
            'darwinboot-fixture-word 8 0x5',
        ])
        self.assertEqual(len(adt), len(ADT))
        # The cpus node in front of /chosen keeps its own darwinboot-memory-floor: the two trees differ only in /chosen.
        cpus_end = ADT.index(b'chosen\0')
        self.assertEqual(adt[:cpus_end], ADT[:cpus_end])
        # Byte for byte the tree the generator's node writer makes with the two new values.
        self.assertEqual(adt, make_adt(size=0x1E0000000, floor=0x920000000))
        self.assertEqual(self.read(self.out, TOML_PATH), toml(f'memory-outside=0 {ARGS}'))
        self.assertEqual(sha256(self.read(self.out, KERNEL_PATH)), sha256(KERNEL))
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)
        self.assertEqual({k: v for k, v in volume_files(data).items() if k not in (ADT_PATH, TOML_PATH)},
                         {k: v for k, v in volume_files(self.base.read_bytes()).items() if k not in (ADT_PATH, TOML_PATH)})

    def test_argument_only(self):
        self.make_base()
        result = self.run_tool('--arg', 'memory-outside=0')
        self.assertEqual(self.last_line(result), 'adt: unchanged, args: memory-outside=0, replaced: unchanged')
        self.assertEqual(self.read(self.out, ADT_PATH), ADT)
        self.assertEqual(self.read(self.out, TOML_PATH), toml(f'memory-outside=0 {ARGS}'))

    def test_set_only_leaves_the_arguments(self):
        self.make_base()
        result = self.run_tool('--set', 'darwinboot-memory-size=0x1E0000000')
        self.assertEqual(self.last_line(result), 'adt: darwinboot-memory-size=0x1e0000000, args: unchanged, replaced: unchanged')
        self.assertEqual(self.read(self.out, TOML_PATH), toml())
        self.assertEqual(self.read(self.out, ADT_PATH), make_adt(size=0x1E0000000))

    def test_several_arguments_keep_their_order(self):
        self.make_base()
        result = self.run_tool('--arg', 'zeta=1', '--arg', 'alpha', '--arg', 'mid=x:y')
        self.assertEqual(self.last_line(result), 'adt: unchanged, args: zeta=1 alpha mid=x:y, replaced: unchanged')
        self.assertEqual(self.read(self.out, TOML_PATH), toml(f'zeta=1 alpha mid=x:y {ARGS}'))

    def test_refuses_existing_output_and_same_file(self):
        self.make_base()
        self.out.write_bytes(b'an earlier output')
        result = self.run_tool('--arg', 'a=1')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertEqual(self.out.read_bytes(), b'an earlier output')
        self.assertFalse(self.temporary.exists(), 'a refused run left OUT.tmp behind')
        result = self.run_tool('--arg', 'a=1', out=self.base)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)
        self.assertFalse(self.base.with_name(self.base.name + '.tmp').exists(), 'a refused run left OUT.tmp behind')
        self.out.unlink()
        result = self.run_tool('--arg', 'a=1', base=self.dir / 'missing.img')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)

    def test_refuses_bad_property(self):
        self.make_base()
        for text in ('darwinboot-nothing=1', 'random-seed=1', 'darwinboot-memory-excluded=1', 'darwinboot-memory-size=-1',
                     'darwinboot-memory-size=0x10000000000000000', 'darwinboot-memory-size=abc', 'darwinboot-memory-size'):
            with self.subTest(text=text):
                self.assertRefused(self.run_tool('--set', text))
        # The same name in /chosen twice.
        twice = node('device-tree', [], [node('chosen', [('darwinboot-memory-size', bytes(8))] * 2)])
        self.make_base(adt=twice)
        self.assertRefused(self.run_tool('--set', 'darwinboot-memory-size=0x10000000'), '2 properties')

    def test_refuses_eight_byte_property_outside_darwinboot(self):
        self.make_base()
        self.assertRefused(self.run_tool('--set', 'fixture-eight-bytes=1'), 'only darwinboot-* properties')

    def test_set_follows_the_generator_rules_for_size_and_floor(self):
        self.make_base(adt=make_adt(size=0x1E0000000, floor=0x920000000))
        for text, shown in (('darwinboot-memory-size=0x10000000', 'darwinboot-memory-size=0x10000000'),
                            ('darwinboot-memory-size=0x240000000', 'darwinboot-memory-size=0x240000000'),
                            ('darwinboot-memory-floor=0x200000', 'darwinboot-memory-floor=0x200000'),
                            ('darwinboot-memory-floor=0xFFFFFFFFFFE00000', 'darwinboot-memory-floor=0xffffffffffe00000'),
                            # Other darwinboot-* values are not checked.
                            ('darwinboot-fixture-word=1', 'darwinboot-fixture-word=0x1')):
            with self.subTest(text=text):
                self.assertEqual(self.accepted('--set', text), f'adt: {shown}, args: unchanged, replaced: unchanged')
        for text, word in (('darwinboot-memory-size=0xfe00000', '256 MiB to 9 GiB'),
                           ('darwinboot-memory-size=0x10001000', '256 MiB to 9 GiB'),
                           ('darwinboot-memory-size=0x240200000', '256 MiB to 9 GiB'),
                           ('darwinboot-memory-size=0', 'generator'),
                           ('darwinboot-memory-floor=0', 'Owned memory floor'),
                           ('darwinboot-memory-floor=0x920001000', 'Owned memory floor')):
            with self.subTest(text=text):
                self.assertRefused(self.run_tool('--set', text), word)

    def test_refuses_data_reset(self):
        self.make_base()
        self.assertRefused(self.run_tool('--arg', 'data-reset=1'))
        self.assertRefused(self.run_tool('--replace-arg', 'data-reset=1'), 'data-reset')
        self.make_base(args=ARGS + ' data-reset=1')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'))
        self.assertRefused(self.run_tool('--set', 'darwinboot-memory-size=0x10000000'), 'data-reset')
        self.assertRefused(self.run_tool('--replace-arg', 'debug=0x1'), 'data-reset')

    def test_refuses_data_reset_in_confirm_args(self):
        self.make_base(toml_bytes=toml() + b'\n[[entry]]\nname = "install"\nconfirm_args = ["", "data-reset=1"]\n')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'))
        self.assertRefused(self.run_tool('--set', 'darwinboot-memory-size=0x10000000'), 'data-reset')

    def test_base_named_like_the_temporary_file_survives(self):
        self.base = self.out.with_name(self.out.name + '.tmp')
        self.make_base()
        result = self.run_tool('--arg', 'memory-outside=0')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith(REFUSAL), result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(sha256(self.base.read_bytes()), self.base_sha)
        self.assertFalse(self.out.exists())

    def test_refuses_duplicate_and_malformed_arguments(self):
        self.make_base()
        for text in ('debug=0x1', 'a b=1', 'x="y"', 'é=1'):
            with self.subTest(text=text):
                self.assertRefused(self.run_tool('--arg', text))
        self.assertRefused(self.run_tool('--arg', 'a=1', '--arg', 'a=2'), 'given twice')

    def test_refuses_arguments_that_break_the_kernel_seal(self):
        # scripts/seal-source-crypto-kernel.py refuses these names, compared without their leading '-'.
        self.make_base(args=ARGS + ' lcks=1')
        for option in ('--arg', '--replace-arg'):
            for text in ('validation_disables=1', '-serverperfmode', '--lcks=1', 'lcks=0'):
                with self.subTest(option=option, text=text):
                    self.assertRefused(self.run_tool(f'{option}={text}'), 'seal')
        self.assertEqual(self.accepted('--arg=-serverperfmode_x', '--arg', 'lcks2=1'),
                         'adt: unchanged, args: -serverperfmode_x lcks2=1, replaced: unchanged')

    def test_accepts_a_line_of_exactly_1000_bytes(self):
        # 983 bytes and 'memory-outside=0 ' in front of them.
        self.make_base(args='k=' + 'v' * 981)
        self.assertEqual(self.accepted('--arg', 'memory-outside=0'), 'adt: unchanged, args: memory-outside=0, replaced: unchanged')
        self.make_base(args='k=' + 'v' * 982)
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), '1001 bytes')

    def test_refuses_line_over_1000_bytes(self):
        self.make_base(args='k=' + 'v' * 988)
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'))

    def test_refuses_nothing_to_do(self):
        self.make_base()
        self.assertRefused(self.run_tool(), 'nothing to do')

    def test_refuses_arguments_without_an_args_line(self):
        self.make_base(toml_bytes=b'[[entry]]\nname = "one"\nconfirm_args = ["", "debug=1"]\n')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), 'no args')
        self.assertRefused(self.run_tool('--replace-arg', 'debug=0x1'), 'no args')

    def test_replaces_an_argument_in_place(self):
        self.make_base(args='debug=0x14e  vm_compression_limit=1572864 serial=3')
        self.assertEqual(self.last_line(self.run_tool('--replace-arg', 'vm_compression_limit=1048576')),
                         'adt: unchanged, args: unchanged, replaced: vm_compression_limit=1048576')
        self.assertEqual(self.read(self.out, TOML_PATH), toml('debug=0x14e  vm_compression_limit=1048576 serial=3'))
        self.assertEqual(self.read(self.out, ADT_PATH), ADT)

    def test_replaces_next_to_added_arguments_and_set_values(self):
        self.make_base()
        result = self.run_tool('--replace-arg', 'vm_compression_limit=1048576', '--arg', 'memory-outside=0',
                               '--replace-arg', 'debug', '--set', 'darwinboot-memory-size=0x1E0000000')
        self.assertEqual(self.last_line(result), 'adt: darwinboot-memory-size=0x1e0000000, args: memory-outside=0, '
                         'replaced: vm_compression_limit=1048576 debug')
        self.assertEqual(self.read(self.out, TOML_PATH), toml('memory-outside=0 debug vm_compression_limit=1048576'))
        self.assertEqual(self.read(self.out, ADT_PATH), make_adt(size=0x1E0000000))

    def test_refuses_a_replacement_that_is_not_once_on_every_line(self):
        for first, second in ((ARGS, 'debug=0x14e'), (ARGS + ' vm_compression_limit=1', ARGS), ('debug=1', 'debug=1')):
            with self.subTest(first=first, second=second):
                self.make_base(toml_bytes=toml(first, second))
                self.assertRefused(self.run_tool('--replace-arg', 'vm_compression_limit=1048576'), 'vm_compression_limit')

    def test_refuses_bad_replacements(self):
        self.make_base()
        for arguments, word in ((('--replace-arg', 'a b=1'), 'does not match'), (('--replace-arg', 'x="y"'), 'does not match'),
                                (('--replace-arg', 'debug=1', '--replace-arg', 'debug=2'), 'given twice'),
                                (('--arg', 'debug=1', '--replace-arg', 'debug=2'), '--arg and --replace-arg')):
            with self.subTest(arguments=arguments):
                self.assertRefused(self.run_tool(*arguments), word)

    def test_replacement_line_limit(self):
        # 'pad=', 985 bytes and ' x=1' are 993 bytes; x=1 becomes x= and 8 digits (1000 bytes) or 9 digits (1001 bytes).
        self.make_base(args='pad=' + 'v' * 985 + ' x=1')
        self.assertEqual(self.accepted('--replace-arg', 'x=' + '2' * 8), f'adt: unchanged, args: unchanged, replaced: x={"2" * 8}')
        self.assertRefused(self.run_tool('--replace-arg', 'x=' + '2' * 9), '1001 bytes')
        # The limit counts the line after all changes: 'a=1 ' in front and the replacement together.
        self.make_base(args='pad=' + 'v' * 983 + ' x=1')
        self.assertEqual(self.accepted('--arg', 'a=1', '--replace-arg', 'x=' + '2' * 6),
                         f'adt: unchanged, args: a=1, replaced: x={"2" * 6}')
        self.assertRefused(self.run_tool('--arg', 'a=1', '--replace-arg', 'x=' + '2' * 7), '1001 bytes')

    def test_refuses_args_lines_of_another_shape(self):
        for line in ('  args = "debug=1"', '\targs = "debug=1"', 'args="debug=1"', 'args = "debug=1" # note',
                     "args = 'debug=1'", 'args = "debug=1"  ', 'args = "a" "b"', 'args = "unterminated'):
            with self.subTest(line=line):
                self.make_base(toml_bytes=toml() + f'\n[[entry]]\nname = "three"\n{line}\n'.encode())
                self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), 'shape')
                self.assertRefused(self.run_tool('--replace-arg', 'debug=0x1'), 'shape')
                # Only a run that rewrites the arguments needs every args line in the one shape.
                self.assertEqual(self.accepted('--set', 'darwinboot-memory-size=0x1E0000000'),
                                 'adt: darwinboot-memory-size=0x1e0000000, args: unchanged, replaced: unchanged')
        # confirm_args is another key, and an empty args line is in the one shape.
        self.make_base(toml_bytes=toml() + b'\n[[entry]]\nname = "install"\nconfirm_args = ["", "x=1"]\nargs = ""\n')
        self.assertEqual(self.accepted('--arg', 'memory-outside=0'), 'adt: unchanged, args: memory-outside=0, replaced: unchanged')

    def test_refuses_stale_temporary_file(self):
        self.make_base()
        self.temporary.write_bytes(b'an earlier run')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), str(self.temporary), temporary_left=True)
        self.assertEqual(self.temporary.read_bytes(), b'an earlier run')

    def test_refuses_temporary_symlink(self):
        self.make_base()
        target = self.dir / 'target.img'
        target.write_bytes(b'someone else')
        self.temporary.symlink_to(target)
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), str(self.temporary), temporary_left=True)
        self.assertEqual(target.read_bytes(), b'someone else')
        self.assertTrue(self.temporary.is_symlink())
        target.unlink()  # now a dangling link
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), str(self.temporary), temporary_left=True)
        self.assertFalse(target.exists() or target.is_symlink())

    def test_same_command_gives_the_same_output(self):
        self.make_base()
        command = ('--set', 'darwinboot-memory-size=0x1E0000000', '--arg', 'memory-outside=0', '--replace-arg', 'debug=0x1')
        self.assertEqual(self.run_tool(*command, out=self.dir / 'first.img').returncode, 0)
        time.sleep(2.1)  # FAT keeps times in 2-second steps
        self.assertEqual(self.run_tool(*command, out=self.dir / 'second.img').returncode, 0)
        self.assertEqual(sha256((self.dir / 'first.img').read_bytes()), sha256((self.dir / 'second.img').read_bytes()))

    def test_refuses_when_the_written_file_reads_back_different(self):
        self.make_base()
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0', env=self.shim(FAULTY_MCOPY)), 'differs')

    def test_refuses_when_a_write_changes_another_file(self):
        self.make_base()
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0', env=self.shim(CHANGES_ANOTHER_FILE)), 'other files')

    def test_refuses_when_the_written_file_is_missing_in_the_read_back(self):
        self.make_base()
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0', env=self.shim(DELETES_THE_WRITTEN_FILE)), 'unixnu.toml')

    def test_refuses_failing_mcopy(self):
        self.make_base()
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0', env=self.shim(FAILS_ON_WRITE)), 'disk full')

    def test_refuses_missing_output_directory(self):
        self.make_base()
        out = self.dir / 'missing' / 'out.img'
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0', out=out), 'No such file or directory', out=out)

    def test_refuses_unreadable_base(self):
        self.make_base()
        self.base.chmod(0)
        try:
            result = self.run_tool('--arg', 'memory-outside=0')
        finally:
            self.base.chmod(0o644)
        self.assertRefused(result, 'Permission denied')

    def test_refuses_toml_that_is_not_utf8(self):
        self.make_base(toml_bytes=toml() + b'# \xff\n')
        self.assertRefused(self.run_tool('--arg', 'memory-outside=0'), 'UTF-8')


if __name__ == '__main__':
    unittest.main()
