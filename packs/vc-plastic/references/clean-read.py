# =============================================================================
# Purpose:  Read-only Clean read of a Plastic workspace, byte-identical changes dropped
# Layer:    Scripts
# Owns:     (script, no public types)
# Depends:  (none)
# =============================================================================

import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile

PREFIX = "clean-read: "
VERBS = ("status", "cat")
HEADER = re.compile(r"STATUS (\d+)(?: |$)")
ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")
SIMILARITY = re.compile(r"\d+(?:\.\d+)?%")
MOVE_KINDS = ("MV", "CH+MV", "LM")
PLAIN_CHANGE = ["False", "NO_MERGES"]
CP_OEMCP = 1
CM_PATH = shutil.which("cm")


class Failure(Exception):
    def __init__(self, label, cause):
        super().__init__(f"{label}: {cause}")


def decode(data):
    return data.decode("utf-8", "surrogateescape")


def shown(line):
    return line.strip() or "no output"


def said(result):
    for stream in (result.stderr, result.stdout):
        for line in decode(stream).splitlines():
            if line.strip():
                return line.strip()
    return f"exit {result.returncode}"


def cm(verb, *args):
    if verb not in VERBS:
        raise Failure("refused verb", verb)
    try:
        result = subprocess.run([CM_PATH, verb, *args], stdin=subprocess.DEVNULL,
                                capture_output=True, cwd=tempfile.gettempdir())
    except OSError as error:
        raise Failure(f"cm {verb}", str(error))
    if result.returncode != 0:
        raise Failure(f"cm {verb}", said(result))
    return result.stdout


def lines_of(data):
    return [(raw, decode(raw).rstrip("\r\n"))
            for raw in data.splitlines(keepends=True) if raw.strip()]


def short_read(path):
    lines = []
    for raw, text in lines_of(cm("status", path, "--short", "--compact")):
        if not ABSOLUTE.match(text):
            raise Failure("unrecognised line", shown(text))
        lines.append((raw, os.path.normcase(text)))
    return lines


def is_move(parts):
    if len(parts) < 6 or not SIMILARITY.fullmatch(parts[1]):
        return False
    paths = " ".join(parts[2:-2])
    starts = [match.start() for match in ABSOLUTE.finditer(paths)]
    return len(starts) == 2 and starts[0] == 0 and paths[starts[1] - 1] == " "


def machine_read(path):
    data = cm("status", path, "--machinereadable")
    texts = [decode(raw).rstrip("\r\n") for raw in data.splitlines(keepends=True)]
    first = texts[0] if texts else ""
    header = HEADER.match(first)
    if header is None:
        raise Failure("malformed header", shown(first))
    candidates = []
    for line in texts[1:]:
        if not line.strip():
            continue
        parts = line.split(" ")
        if parts[0] in MOVE_KINDS:
            if not is_move(parts):
                raise Failure("unrecognised line", shown(line))
            continue
        item = " ".join(parts[1:-2])
        if len(parts) < 4 or not ABSOLUTE.match(item):
            raise Failure("unrecognised line", shown(line))
        if parts[0] == "CH" and parts[-2:] == PLAIN_CHANGE:
            candidates.append(item)
    return header.group(1), candidates


def oem_form(name):
    if os.name != "nt":
        return None
    convert = ctypes.windll.kernel32.WideCharToMultiByte
    size = convert(CP_OEMCP, 0, name, len(name), None, 0, None, None)
    buffer = ctypes.create_string_buffer(size)
    convert(CP_OEMCP, 0, name, len(name), buffer, size, None, None)
    return buffer.raw[:size]


def on_disk(item, root):
    printed = item.encode("utf-8", "surrogateescape")
    lowered, utf8, oem = printed.lower(), root.encode("utf-8"), oem_form(root)
    if lowered.startswith(utf8.lower() + b"\\"):
        real, rest = decode(printed[:len(utf8)]), printed[len(utf8) + 1:]
    elif oem is not None and lowered.startswith(oem.lower() + b"\\"):
        real, rest = root, printed[len(oem) + 1:]
    else:
        return item
    current = root
    for comp in rest.split(b"\\"):
        try:
            entries = os.listdir(current)
        except OSError:
            return item
        wanted, forms = comp.lower(), {entry: oem_form(entry) for entry in entries}
        by_utf8 = {entry for entry in entries if entry.encode("utf-8").lower() == wanted}
        by_oem = {entry for entry, form in forms.items()
                  if form is not None and form.lower() == wanted}
        matches = by_utf8 | by_oem
        if not matches:
            return item
        if len(matches) > 1:
            raise Failure("ambiguous name", item)
        (entry,) = matches
        current = os.path.join(current, entry)
        real = real + "\\" + (decode(comp) if entry in by_utf8 else entry)
    return real


def identical(candidates, changeset, root):
    dropped = set()
    directory = tempfile.mkdtemp()
    try:
        for index, item in enumerate(candidates):
            real = on_disk(item, root)
            base = os.path.join(directory, f"base-{index}")
            cm("cat", f"{real}#cs:{changeset}", f"--file={base}")
            if not os.path.isfile(base):
                raise Failure("base not written", item)
            try:
                with open(real, "rb") as handle:
                    current = handle.read()
            except OSError as error:
                raise Failure("workspace file unreadable", f"{item}: {error}")
            with open(base, "rb") as handle:
                if handle.read() == current:
                    dropped.add(os.path.normcase(item))
            os.remove(base)
    finally:
        shutil.rmtree(directory, ignore_errors=True)
    return dropped


def clean_read(argv):
    if len(argv) != 1:
        raise Failure("usage", f"{len(argv)} arguments")
    path = os.path.abspath(argv[0])
    if not os.path.isdir(path):
        raise Failure("not a directory", path)
    if CM_PATH is None:
        raise Failure("cm not found", "not on PATH")
    lines = short_read(path)
    if not lines:
        return
    changeset, candidates = machine_read(path)
    keys = {key for _raw, key in lines}
    for item in candidates:
        if os.path.normcase(item) not in keys:
            raise Failure("candidate not in the short read", item)
    dropped = identical(candidates, changeset, path) if candidates else set()
    sys.stdout.buffer.write(b"".join(raw for raw, key in lines if key not in dropped))
    sys.stdout.buffer.flush()


def main(argv):
    try:
        clean_read(argv)
        return 0
    except Failure as failure:
        line = str(failure)
    except Exception as error:
        line = f"unexpected error: {type(error).__name__}: {error}"
    sys.stdout.buffer.write((PREFIX + line + "\n").encode("utf-8", "surrogateescape"))
    sys.stdout.buffer.flush()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
