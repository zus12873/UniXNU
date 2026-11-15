#!/usr/bin/env python3
"""Derive a variant of a payload volume that differs only in a few device tree values and in the boot arguments.

    make-payload-variant.py BASE OUT [--set NAME=VALUE]... [--arg NAME=VALUE]...

BASE is a payload volume (a FAT image holding EFI/UniXNU). OUT is a copy of it in which only two files change:
  --set NAME=VALUE  the 8-byte property NAME (darwinboot-*) of /chosen in Payloads/kernel.macho.adt becomes VALUE
                    (int(VALUE, 0), 0 to 2^64-1, little endian). The file keeps its length.
  --arg NAME=VALUE  NAME=VALUE is put in front of the content of every `args = "..."` line of unixnu.toml; several
                    --arg keep their command-line order. NAME alone (no =VALUE) is allowed.
With only --arg the device tree is not rewritten, with only --set unixnu.toml is not rewritten.

It refuses, and leaves no OUT, when OUT exists or is BASE, when there is nothing to change, when a property is missing,
appears twice, is not 8 bytes long or does not start with darwinboot-, when a value is not a 64-bit integer, when an
argument is malformed, named data-reset, or named like one already on a line, when data-reset is on a line already, when
a line would pass 1000 bytes, and when the volume it wrote does not read back as BASE plus exactly those two files.
Needs GNU mtools (brew install mtools). It never writes BASE.
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
ARGUMENT = re.compile(rb'[A-Za-z0-9_.\-]+(=[A-Za-z0-9_.,/\-:=]+)?')
ARGS_OPEN = b'args = "'
MAX_ARGS_BYTES = 1000


class Refusal(Exception):
    pass


def load_reader():
    """local-tools/adt-chosen.py, the one device tree reader (its name has a hyphen, so it cannot be imported)."""
    sys.dont_write_bytecode = True
    spec = spec_from_file_location('adt_chosen', Path(__file__).resolve().with_name('adt-chosen.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.exit(f'{PREFIX}{message}')


def mtools(*command):
    result = subprocess.run([str(part) for part in command], env=MTOOLS_ENV, capture_output=True, text=True)
    if result.returncode:
        raise Refusal(f'{command[0]}: {(result.stderr or result.stdout).strip()}')


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
        values[name] = number
    return values


def parse_arguments(texts):
    arguments = []
    for text in texts:
        if not ARGUMENT.fullmatch(text.encode()):
            raise Refusal(f'--arg {text!r} does not match NAME or NAME=VALUE with the characters A-Za-z0-9_.,/:=-')
        name = text.partition('=')[0]
        if name == 'data-reset':
            raise Refusal('--arg data-reset is never added: it wipes the data volume')
        if name in (other.partition('=')[0] for other in arguments):
            raise Refusal(f'--arg {name} is given twice')
        arguments.append(text)
    return arguments


def args_lines(toml):
    """(index, line ending, content between the quotes) of every line that starts with `args = "` and ends with a quote."""
    found = []
    lines = toml.splitlines(keepends=True)
    for index, line in enumerate(lines):
        body = line.rstrip(b'\r\n')
        if body.startswith(ARGS_OPEN) and body.endswith(b'"') and len(body) > len(ARGS_OPEN):
            found.append((index, line[len(body):], body[len(ARGS_OPEN):-1]))
    return lines, found


def new_toml(toml, arguments, edit):
    lines, found = args_lines(toml)
    names = {token.partition(b'=')[0] for _, _, content in found for token in content.split()}
    if b'data-reset' in names:
        raise Refusal('an args line of unixnu.toml already has data-reset')
    if not edit:
        return toml
    if not found:
        raise Refusal('unixnu.toml has no args = "..." line')
    for argument in arguments:
        if argument.partition('=')[0].encode() in names:
            raise Refusal(f'an args line already has an argument named {argument.partition("=")[0]}')
    for index, ending, content in found:
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


def make_variant(base, out, values, arguments):
    reader = load_reader()
    temporary = out.with_name(out.name + '.tmp')
    try:
        shutil.copyfile(base, temporary)
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            old = extract_all(base, work / 'old')
            for path in (ADT, TOML):
                if path not in old:
                    raise Refusal(f'BASE has no ::/{path}')
            adt = new_adt(reader, (work / 'old' / ADT).read_bytes(), values)
            toml = new_toml((work / 'old' / TOML).read_bytes(), arguments, bool(arguments))
            for path, content in ((ADT, adt), (TOML, toml)):
                if content != (work / 'old' / path).read_bytes():
                    staged = work / 'stage' / Path(path).name
                    staged.parent.mkdir(exist_ok=True)
                    staged.write_bytes(content)
                    mtools('mcopy', '-D', 'o', '-Q', '-m', '-i', temporary, staged, f'::/{path}')
            new = extract_all(temporary, work / 'new')
            changed = {ADT: adt, TOML: toml}
            for path in (ADT, TOML):
                if (work / 'new' / path).read_bytes() != changed[path]:
                    raise Refusal(f'the {Path(path).name} read back from OUT differs from what was written')
            if {k: v for k, v in new.items() if k not in changed} != {k: v for k, v in old.items() if k not in changed}:
                raise Refusal('the other files of OUT read back different from BASE')
        data = temporary.read_bytes()
        os.replace(temporary, out)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return len(data), hashlib.sha256(data).hexdigest()


def main():
    parser = Parser(description='Derive a payload volume that differs in device tree values and boot arguments only.')
    parser.add_argument('base', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--set', action='append', default=[], metavar='NAME=VALUE')
    parser.add_argument('--arg', action='append', default=[], metavar='NAME=VALUE')
    args = parser.parse_args()
    try:
        if not args.base.is_file():
            raise Refusal(f'BASE {args.base} does not exist')
        if args.out.exists() or args.out.is_symlink():
            raise Refusal(f'OUT {args.out} exists' + (' (it is BASE)' if same_file(args.base, args.out) else ''))
        if not args.set and not args.arg:
            raise Refusal('nothing to do: give --set or --arg')
        values = parse_sets(args.set)
        arguments = parse_arguments(args.arg)
        if not shutil.which('mcopy'):
            raise Refusal('mcopy not found (brew install mtools)')
        size, digest = make_variant(args.base, args.out, values, arguments)
    except Refusal as refusal:
        sys.exit(f'{PREFIX}{refusal}')
    changes = ' '.join(f'{name}={number:#x}' for name, number in values.items()) or 'unchanged'
    print(f'{args.out}: {size} bytes, sha256 {digest}, adt: {changes}, args: {" ".join(arguments) or "unchanged"}')


if __name__ == '__main__':
    main()
