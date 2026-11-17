#!/usr/bin/env python3
"""Derive a variant of a payload volume that differs only in a few device tree values and in the boot arguments.

    make-payload-variant.py BASE OUT [--set NAME=VALUE]... [--arg NAME=VALUE]... [--replace-arg NAME=VALUE]...

BASE is a payload volume (a FAT image holding EFI/UniXNU). OUT is a copy of it in which only two files change:
  --set NAME=VALUE          the 8-byte property NAME (darwinboot-*) of /chosen in Payloads/kernel.macho.adt becomes VALUE
                            (int(VALUE, 0), 0 to 2^64-1, little endian). The file keeps its length. darwinboot-memory-size
                            and darwinboot-memory-floor must also pass the device tree generator's own rules
                            (scripts/unixnu/devicetree.py memory_size and memory_floor).
  --arg NAME=VALUE          NAME=VALUE is put in front of the content of every `args = "..."` line of unixnu.toml; several
                            --arg keep their command-line order. NAME alone (no =VALUE) is allowed.
  --replace-arg NAME=VALUE  the argument named NAME, which every `args = "..."` line must hold exactly once, becomes
                            NAME=VALUE where it stands. The same syntax as --arg.
With only --set unixnu.toml is not rewritten, without --set the device tree is not rewritten. The two files written get
the modification time 1980-01-01 00:00 UTC, so the same command on the same BASE gives the same OUT byte for byte.

It refuses, and leaves no OUT, when OUT or OUT.tmp exists or OUT is BASE, when there is nothing to change, when a property
is missing, appears twice, is not 8 bytes long or does not start with darwinboot-, when a value is not a 64-bit integer or
breaks the generator's rule for it, when an argument is malformed, named data-reset, named like one the kernel build
refuses (validation_disables, serverperfmode, lcks), given twice, or added under a name already on a line, when a replaced
argument is not on every line exactly once, when data-reset is anywhere in unixnu.toml, when unixnu.toml is not UTF-8 or
assigns args in another shape than `args = "..."` (column 0, nothing behind the closing quote), when a line would pass 1000
bytes, when a file cannot be read or written, and when the volume it wrote does not read back as BASE plus exactly those
two files. Needs GNU mtools (brew install mtools). It never writes BASE.
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
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PREFIX = 'make-payload-variant: '
ADT = 'EFI/UniXNU/Payloads/kernel.macho.adt'
TOML = 'EFI/UniXNU/unixnu.toml'
MTOOLS_ENV = dict(os.environ, MTOOLS_SKIP_CHECK='1', TZ='UTC')
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
ARGUMENT = re.compile(r'[A-Za-z0-9_.\-]+(=[A-Za-z0-9_.,/\-:=]+)?')
ARGS_OPEN = b'args = "'
# The one shape of an args line the tool edits, and any line that assigns args at all.
ARGS_LINE = re.compile(rb'args = "([^"]*)"')
ARGS_KEY = re.compile(rb'\s*args\s*=')
TOKEN = re.compile(rb'\S+')
MAX_ARGS_BYTES = 1000
# 1980-01-01 00:00 UTC, the first time a FAT directory entry holds: the files written carry it instead of the time of the run.
FIXED_TIME = 315532800
# scripts/seal-source-crypto-kernel.py refuses these names (compared without their leading '-'): they flip static_if keys
# at boot that the kernel's seal, computed at build time, does not model.
SEAL_BREAKING = ('validation_disables', 'serverperfmode', 'lcks')
# What memory_floor wants besides the floor, a window size and an excluded-range table size the generator accepts; it checks
# only that both are given.
FLOOR_COMPANIONS = {'owned_memory_size': 0x10000000, 'owned_memory_excluded_ranges': 64}


class Refusal(Exception):
    pass


def load_reader():
    """local-tools/adt-chosen.py, the one device tree reader (its name has a hyphen, so it cannot be imported)."""
    sys.dont_write_bytecode = True
    spec = spec_from_file_location('adt_chosen', Path(__file__).resolve().with_name('adt-chosen.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_rules():
    """scripts/unixnu/devicetree.py, whose memory_size and memory_floor are the rules the generator applies to the two values."""
    sys.dont_write_bytecode = True
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    try:
        from unixnu import devicetree
        from unixnu.util import Error
    except ImportError as error:
        raise Refusal(f'cannot load the device tree rules from {SCRIPTS}: {error}') from None
    return devicetree, Error


class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.exit(f'{PREFIX}{message}')


def mtools(*command):
    try:
        result = subprocess.run([str(part) for part in command], env=MTOOLS_ENV, capture_output=True)
    except OSError as error:
        raise Refusal(f'{command[0]}: {error.strerror or error}') from None
    if result.returncode:
        output = (result.stderr or result.stdout).decode(errors='replace').strip()
        raise Refusal(f'{command[0]} failed with status {result.returncode}: {output}')


def same_file(first, second):
    """True when both paths name one file: the same path, a symbolic link or a hard link."""
    if first.resolve() == second.resolve():
        return True
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def split_assignment(text, option):
    name, _, value = text.partition('=')
    if not _:
        raise Refusal(f'{option} {text}: expected NAME=VALUE')
    return name, value


def check_rules(text, name, number):
    """The device tree generator's own rule for darwinboot-memory-size and darwinboot-memory-floor."""
    if name == 'darwinboot-memory-size':
        options = {'owned_memory_size': number}
    elif name == 'darwinboot-memory-floor':
        options = dict(FLOOR_COMPANIONS, owned_memory_floor=number)
    else:
        return
    devicetree, Error = load_rules()
    try:
        made = (devicetree.memory_size if name == 'darwinboot-memory-size' else devicetree.memory_floor)(options)
    except Error as error:
        raise Refusal(f'--set {text}: {error}') from None
    if made != [(name, struct.pack('<Q', number))]:
        raise Refusal(f'--set {text}: the device tree generator writes no {name} for this value')


def parse_sets(texts):
    values = {}
    for text in texts:
        name, value = split_assignment(text, '--set')
        if not name.startswith('darwinboot-'):
            raise Refusal(f'--set {text}: only darwinboot-* properties may be set')
        if name in values:
            raise Refusal(f'--set {name} is given twice')
        try:
            number = int(value, 0)
        except ValueError:
            raise Refusal(f'--set {text}: {value!r} is not an integer') from None
        if not 0 <= number < 1 << 64:
            raise Refusal(f'--set {text}: the value is not between 0 and 2^64-1')
        check_rules(text, name, number)
        values[name] = number
    return values


def argument_name(text):
    return text.partition('=')[0]


def parse_arguments(texts, option):
    arguments = []
    for text in texts:
        if not ARGUMENT.fullmatch(text):
            raise Refusal(f'{option} {text!r} does not match NAME or NAME=VALUE with the characters A-Za-z0-9_.,/:=-')
        name = argument_name(text)
        if name == 'data-reset':
            raise Refusal(f'{option} data-reset is never used: it wipes the data volume')
        if name.lstrip('-') in SEAL_BREAKING:
            raise Refusal(f'{option} {name}: the kernel build refuses it, it would break the seal computed at build time '
                          '(scripts/seal-source-crypto-kernel.py)')
        if name in map(argument_name, arguments):
            raise Refusal(f'{option} {name} is given twice')
        arguments.append(text)
    return arguments


def args_lines(toml):
    """The lines of unixnu.toml and (index, line ending, content between the quotes) of every `args = "..."` line.

    A line that assigns args in another shape is refused: the tool would leave it as it is."""
    found = []
    lines = toml.splitlines(keepends=True)
    for index, line in enumerate(lines):
        body = line.rstrip(b'\r\n')
        shape = ARGS_LINE.fullmatch(body)
        if shape:
            found.append((index, line[len(body):], shape[1]))
        elif ARGS_KEY.match(body):
            raise Refusal(f'unixnu.toml line {index + 1} assigns args in another shape than args = "...": {body.decode()!r}')
    return lines, found


def replace(content, replacement, line):
    """content with its one argument named like replacement replaced by it, where it stands."""
    name = argument_name(replacement).encode()
    spans = [match.span() for match in TOKEN.finditer(content) if match[0].partition(b'=')[0] == name]
    if len(spans) != 1:
        raise Refusal(f'unixnu.toml line {line} has {len(spans)} arguments named {name.decode()}, expected 1')
    start, end = spans[0]
    return content[:start] + replacement.encode() + content[end:]


def new_toml(toml, arguments, replacements):
    if b'data-reset' in toml:
        raise Refusal('unixnu.toml already mentions data-reset (an args line, confirm_args or anything else)')
    try:
        toml.decode()
    except UnicodeDecodeError as error:
        raise Refusal(f'unixnu.toml is not valid UTF-8 (byte {error.start}: {error.reason})') from None
    if not arguments and not replacements:
        return toml
    lines, found = args_lines(toml)
    if not found:
        raise Refusal('unixnu.toml has no args = "..." line')
    names = {token.partition(b'=')[0] for _, _, content in found for token in content.split()}
    for argument in arguments:
        if argument_name(argument).encode() in names:
            raise Refusal(f'an args line already has an argument named {argument_name(argument)}')
    for index, ending, content in found:
        for replacement in replacements:
            content = replace(content, replacement, index + 1)
        new = b' '.join([argument.encode() for argument in arguments] + ([content] if content else []))
        if len(new) > MAX_ARGS_BYTES:
            raise Refusal(f'an args line would be {len(new)} bytes; the limit is {MAX_ARGS_BYTES}')
        lines[index] = ARGS_OPEN + new + b'"' + ending
    return b''.join(lines)


def new_adt(reader, blob, values):
    if not values:
        return blob
    try:
        properties = reader.find_chosen(blob)[0]
    except reader.Malformed as error:
        raise Refusal(f'the device tree: {error}') from None
    patched = bytearray(blob)
    for name, number in values.items():
        found = [(value, offset) for key, value, offset in properties if key == name]
        if len(found) != 1:
            raise Refusal(f'/chosen has {len(found)} properties named {name}, expected 1')
        if len(found[0][0]) != 8:
            raise Refusal(f'/chosen {name} is {len(found[0][0])} bytes long, expected 8')
        struct.pack_into('<Q', patched, found[0][1], number)
    return bytes(patched)


def tree(root):
    """Every directory and file below root: {relative path: sha256 of a file, None for a directory}."""
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            for path in sorted(root.rglob('*'))}


def extract_all(volume, into):
    into.mkdir()
    mtools('mcopy', '-i', volume, '-s', '-n', '-m', '::/*', into)
    return tree(into)


def make_variant(base, out, values, arguments, replacements):
    reader = load_reader()
    temporary = out.with_name(out.name + '.tmp')
    if os.path.lexists(temporary):
        raise Refusal(f'{temporary} exists' + (' (it is BASE)' if same_file(base, temporary) else '') +
                      '; it is not this run\'s, so it is left alone: remove it or give OUT another name')
    created = False
    try:
        with base.open('rb') as source:
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            except FileExistsError:
                raise Refusal(f'{temporary} appeared while this run started; it is left alone') from None
            created = True
            with os.fdopen(descriptor, 'wb') as target:
                shutil.copyfileobj(source, target, 1 << 20)
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            old = extract_all(base, work / 'old')
            for path in (ADT, TOML):
                if old.get(path) is None:
                    raise Refusal(f'BASE has no file ::/{path}')
            adt = new_adt(reader, (work / 'old' / ADT).read_bytes(), values)
            toml = new_toml((work / 'old' / TOML).read_bytes(), arguments, replacements)
            for path, content in ((ADT, adt), (TOML, toml)):
                if content != (work / 'old' / path).read_bytes():
                    staged = work / 'stage' / Path(path).name
                    staged.parent.mkdir(exist_ok=True)
                    staged.write_bytes(content)
                    os.utime(staged, (FIXED_TIME, FIXED_TIME))
                    mtools('mcopy', '-D', 'o', '-Q', '-m', '-i', temporary, staged, f'::/{path}')
            new = extract_all(temporary, work / 'new')
            changed = {ADT: adt, TOML: toml}
            for path in (ADT, TOML):
                if new.get(path) is None:
                    raise Refusal(f'OUT has no file ::/{path} when read back after the write')
                if (work / 'new' / path).read_bytes() != changed[path]:
                    raise Refusal(f'the {Path(path).name} read back from OUT differs from what was written')
            if {k: v for k, v in new.items() if k not in changed} != {k: v for k, v in old.items() if k not in changed}:
                raise Refusal('the other files of OUT read back different from BASE')
        data = temporary.read_bytes()
        os.replace(temporary, out)
        created = False
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise
    return len(data), hashlib.sha256(data).hexdigest()


def describe(error):
    """An OSError as `path: reason`, the way a refusal names what failed."""
    paths = ' -> '.join(str(path) for path in (error.filename, error.filename2) if path is not None)
    return f'{paths}: {error.strerror}' if paths and error.strerror else str(error)


def main():
    parser = Parser(description='Derive a payload volume that differs in device tree values and boot arguments only.')
    parser.add_argument('base', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--set', action='append', default=[], metavar='NAME=VALUE')
    parser.add_argument('--arg', action='append', default=[], metavar='NAME=VALUE')
    parser.add_argument('--replace-arg', action='append', default=[], metavar='NAME=VALUE')
    args = parser.parse_args()
    try:
        if not args.base.is_file():
            raise Refusal(f'BASE {args.base} does not exist')
        if args.out.exists() or args.out.is_symlink():
            raise Refusal(f'OUT {args.out} exists' + (' (it is BASE)' if same_file(args.base, args.out) else ''))
        if not args.set and not args.arg and not args.replace_arg:
            raise Refusal('nothing to do: give --set, --arg or --replace-arg')
        values = parse_sets(args.set)
        arguments = parse_arguments(args.arg, '--arg')
        replacements = parse_arguments(args.replace_arg, '--replace-arg')
        both = set(map(argument_name, arguments)) & set(map(argument_name, replacements))
        if both:
            raise Refusal(f'{" ".join(sorted(both))} is given to --arg and --replace-arg')
        if not shutil.which('mcopy'):
            raise Refusal('mcopy not found (brew install mtools)')
        size, digest = make_variant(args.base, args.out, values, arguments, replacements)
    except Refusal as refusal:
        sys.exit(f'{PREFIX}{refusal}')
    except OSError as error:
        sys.exit(f'{PREFIX}{describe(error)}')
    changes = ' '.join(f'{name}={number:#x}' for name, number in values.items()) or 'unchanged'
    print(f'{args.out}: {size} bytes, sha256 {digest}, adt: {changes}, args: {" ".join(arguments) or "unchanged"}, '
          f'replaced: {" ".join(replacements) or "unchanged"}')


if __name__ == '__main__':
    main()
