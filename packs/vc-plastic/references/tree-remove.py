# =============================================================================
# Purpose:  Workspace removal per the trees binding's Remove procedure, read back
# Layer:    Scripts
# Owns:     (script, no public types)
# Depends:  (none)
# =============================================================================

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

BINDINGS_REL = os.path.join(".claude", "bindings", "vc-plastic.md")
PROBE_SUFFIX = ".release-probe"
ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")
CM_PATH = shutil.which("cm")
CLEAN_READ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clean-read.py")


def normalise(path):
    return path.replace("/", "\\").rstrip("\\").casefold()


def trees_section(text):
    heading = re.compile(r"^#{2,}\s*trees\b", re.IGNORECASE)
    body = None
    for line in text.splitlines():
        if body is not None and re.match(r"^#{1,6}\s", line):
            break
        if body is not None:
            body.append(line)
        elif heading.match(line):
            body = []
    return body


def absent_form(root):
    try:
        with open(os.path.join(root, BINDINGS_REL), encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, ValueError):
        return "missing", None
    lines = trees_section(text)
    if lines is None:
        return "missing", None
    stripped = [line.strip() for line in lines]
    content = [line for line in stripped
               if line and not (line.startswith("<!--") and line.endswith("-->"))]
    if not content:
        return "empty", None
    if any("TODO" in line for line in lines):
        return "TODO", None
    if len(content) == 1 and re.match(
            r"none(\s|\u2014|$)", content[0].removeprefix("- ").replace("`", "")) is not None:
        return "none", None
    return None, lines


def trees_roots(lines):
    roots = []
    for line in lines:
        if not line.strip().startswith("- Location:"):
            continue
        for token in re.findall(r"`([^`]+)`", line):
            if not re.match(r"^[A-Za-z]:[\\/]", token):
                continue
            kept = []
            for component in re.split(r"[\\/]", token):
                if "<" in component:
                    break
                kept.append(component)
            key = normalise(os.path.normpath("\\".join(kept) + "\\"))
            if not re.fullmatch(r"[a-z]:", key) and key not in roots:
                roots.append(key)
        break
    return roots


def extended(path):
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return path
    full = os.path.abspath(path)
    if full.startswith("\\\\"):
        return "\\\\?\\UNC\\" + full[2:]
    return "\\\\?\\" + full


def released(path):
    long = extended(path)
    probe = long.rstrip("\\/") + PROBE_SUFFIX
    try:
        os.rename(long, probe)
    except OSError:
        return False
    os.rename(probe, long)
    return True


def cm(*args):
    return subprocess.run([CM_PATH, *args], stdin=subprocess.DEVNULL,
                          capture_output=True, cwd=tempfile.gettempdir())


def relay(*streams):
    data = b"".join(streams)
    if not data:
        return
    sys.stdout.flush()
    sys.stdout.buffer.write(data if data.endswith(b"\n") else data + b"\n")
    sys.stdout.buffer.flush()


def is_listed(path):
    listed = cm("workspace", "list")
    if listed.returncode != 0:
        relay(listed.stdout, listed.stderr)
        return None
    wanted = normalise(path)
    for line in listed.stdout.decode("utf-8", "replace").splitlines():
        found = ABSOLUTE.search(line)
        if found and normalise(line[found.start():].strip()) == wanted:
            return True
    return False


def delete_directory(path):
    errors = []

    def retry(function, target, _error):
        try:
            os.chmod(target, stat.S_IWRITE)
            function(target)
        except OSError as error:
            errors.append(str(error))

    shutil.rmtree(extended(path), onexc=retry)
    return errors


def main(argv):
    parser = argparse.ArgumentParser(prog="tree-remove.py")
    parser.add_argument("path")
    parser.add_argument("--wait", type=int, default=30)
    args = parser.parse_args(argv[1:])
    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"absent: {path}")
        return 1
    form, lines = absent_form(os.getcwd())
    if form is not None:
        print(f"refused: ## trees in .claude/bindings/vc-plastic.md reads absent ({form})")
        return 1
    key = normalise(path)
    if not any(key.startswith(root + "\\") for root in trees_roots(lines)):
        print(f"refused: {path} lies under no trees Location")
        return 1
    if CM_PATH is None:
        print("refused: cm is not on PATH")
        return 1
    listed = is_listed(path)
    if listed is None:
        print("refused: cm workspace list failed")
        return 1
    if not listed:
        print(f"refused: {path} is not a workspace")
        return 1
    deadline = time.monotonic() + args.wait
    while not released(path):
        if time.monotonic() >= deadline:
            print(f"held: {path} is still in use after {args.wait} s")
            return 2
        time.sleep(1)
    read = subprocess.run([sys.executable, CLEAN_READ, path], stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, cwd=tempfile.gettempdir())
    if read.returncode != 0 or read.stdout:
        relay(read.stdout)
        print(f"refused: {path} is not clean")
        return 1
    removal = cm("workspace", "delete", path)
    if removal.returncode != 0:
        relay(removal.stdout, removal.stderr)
    if is_listed(path) is not False:
        print(f"refused: {path} is still listed")
        return 1
    for message in delete_directory(path):
        print(message)
    if os.path.isdir(path):
        print(f"half-removed: {path} is unlisted but its directory remains")
        return 3
    print(f"removed: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
