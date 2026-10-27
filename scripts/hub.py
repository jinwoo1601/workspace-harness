#!/usr/bin/env python3
# =============================================================================
# Purpose:  Hub helpers for memory writes, the STATUS move, the memory commit, the session list, the predecessor read, the hub lock, the one-command hub write and its clearing verb
# Layer:    Scripts
# Owns:     Refusal (exception class), Held (exception class), Stray (exception class), Correctable (exception class), Migration (class), GitBackend (class), PlasticBackend (class), HubLock (class), EditAction (argparse action class)
# Depends:  (none)
# =============================================================================

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


UPDATED_LINE = re.compile(r"updated: \d{4}-\d{2}-\d{2}")

DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

DRIVE_FORM = re.compile(r"^/([A-Za-z])(?=/|$)")

SPAN = re.compile(r"`([^`]*)`")

LIST_PREFIX = "- List command:"

SYSTEM_PREFIX = "- System:"

BRANCH_LINE = re.compile(r"Branch ([^@]+)@(.+@.+)")

STATUS_HEADER = re.compile(r"STATUS (\d+)(?: |$)")

MOVE_TEXT = re.compile(r"\d+(?:\.\d+)?% (.+?) ([A-Za-z]:[\\/].*)")

ADDED_ITEM = re.compile(r"Item (.+) was correctly added")

UNBOUND_VALUES = ("todo", "none")

LIST_TIMEOUT = 30

WAIT_POLL = 2

PREDECESSOR_TOKEN = "<predecessor>"

BRIEF_TOKEN = "<brief>"

BRIEF_ESCAPE = "<<brief>>"

LOCK_NAME = "harness-hub-lock.json"

LOCK_WAIT = 10

LOCK_POLL = 0.2

LAYOUT = ("## Current", "## Deferred", "## Backlog candidates", "## Notes for future features")

AUTO_CLOSED = "Auto-closed"

ENTRY = re.compile(r"^- \*\*(?P<id>[^*]+)\*\* · (?P<verdict>[A-Z-]+) · ")

OPEN_ENTRY = re.compile(r"^- \*\*(?P<id>[^*]+)\*\* · (?P<verdict>OPEN|OPEN-DRIFTED) · "
                        r"(?P<route>(light-lane|design-branch|feature|standing-ruling|optimization-run)\b[^·]*)"
                        r" · v\d{4}-\d{2}-\d{2} — \S.*$")

OPEN_VERDICTS = ("OPEN", "OPEN-DRIFTED")

ID_KEY = re.compile(r"[A-Z]\d+")

ID_ENTRY = re.compile(r"- \*\*(`?)(?P<letter>[A-Z])(?P<number>\d+)\1(?:\*\*|\s)")

EDITS = {"entry": ("SECTION", "KEY", "FILE"), "remove-entry": ("SECTION", "KEY"),
         "section": ("SECTION", "FILE"), "note": ("FILE",), "brief": ("FILE",),
         "append": ("PATH", "FILE"), "record": ("FILE",)}

APPEND_PATHS = ("memory/backlog-candidates.md", "memory/notes-for-future-features.md",
                "memory/automode-refusals.md")

RECORD_NAME = re.compile(r"[^/\\]+\.md")

BRIEF_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[^\W_]+(?:-[^\W_]+)*\.md")

RESERVED_RECORDS = ("status.md",) + tuple(Path(path).name for path in APPEND_PATHS)


class Refusal(Exception):
    pass


class Held(Refusal):
    pass


class Stray(Refusal):
    def __init__(self, message, stray):
        super().__init__(message)
        self.stray = stray


class Correctable(Refusal):
    def __init__(self, message, part=None):
        super().__init__(message)
        self.part = part


class EditAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        edits = list(getattr(namespace, self.dest) or [])
        edits.append((option_string[2:], values))
        setattr(namespace, self.dest, edits)


class Migration:
    def __init__(self, status, note_block, backlog, notes, kept, moved):
        self.status = status
        self.note_block = note_block
        self.backlog = backlog
        self.notes = notes
        self.kept = kept
        self.moved = moved


def read_lf(path):
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def write_lf(path, text):
    path.write_bytes(text.encode("utf-8"))


def raw_bytes(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def read_input(source):
    try:
        return read_lf(Path(source))
    except (OSError, UnicodeDecodeError) as error:
        raise Refusal(f"cannot read {source}: {error}") from None


def set_updated(lines, today):
    first = next((index for index, line in enumerate(lines) if line.startswith("## ")),
                 len(lines))
    for index in range(first):
        if UPDATED_LINE.fullmatch(lines[index]):
            lines[index] = f"updated: {today.isoformat()}"


def replace_section(text, section, body, today):
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    heading = f"## {section}"
    if heading not in lines:
        raise Correctable(f"no section '{heading}' in memory/STATUS.md")
    start = lines.index(heading)
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("## ")), len(lines))
    content = body.split("\n")
    while content and not content[-1].strip():
        content.pop()
    replaced = [heading, ""] + content + ([""] if end < len(lines) else [])
    lines = lines[:start] + replaced + lines[end:]
    set_updated(lines, today)
    return "\n".join(lines) + "\n"


def entry_pattern(key):
    escaped = re.escape(key)
    return re.compile(rf"- \*\*(?:{escaped}(?:\*\*|\s)|`{escaped}`(?:\*\*|\s|:))")


def entry_line(text, key, source):
    content = text.split("\n")
    while content and not content[-1].strip():
        content.pop()
    if len(content) != 1:
        raise Refusal(f"{source} holds {len(content)} lines, not one entry line")
    if not entry_pattern(key).match(content[0]):
        raise Refusal(f"the line of {source} is not an entry for {key}")
    return content[0]


def entry_end(lines, index, end):
    index += 1
    while index < end and lines[index][:1] in (" ", "\t") and lines[index].strip():
        index += 1
    return index


def add_position(lines, start, end, key):
    if ID_KEY.fullmatch(key):
        order = (key[0], int(key[1:]))
        found = [(index, ID_ENTRY.match(lines[index])) for index in range(start, end)]
        entries = [(index, (entry["letter"], int(entry["number"])))
                   for index, entry in found if entry is not None]
        if entries:
            return next((index for index, other in entries if other > order),
                        entry_end(lines, entries[-1][0], end))
    bullets = [index for index in range(start, end) if lines[index].startswith("- ")]
    return entry_end(lines, bullets[-1], end) if bullets else None


def change_entry(text, section, key, line, today):
    lines = text.split("\n")
    heading = f"## {section}"
    if heading not in lines:
        if section != AUTO_CLOSED:
            raise Correctable(f"no section '{heading}' in memory/STATUS.md")
        if line is None:
            return text
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ([""] if lines else []) + [heading, "", line]
        if text.endswith("\n"):
            lines.append("")
        set_updated(lines, today)
        return "\n".join(lines)
    start = lines.index(heading) + 1
    end = next((index for index in range(start, len(lines))
                if lines[index].startswith("## ")), len(lines))
    pattern = entry_pattern(key)
    matches = [index for index in range(start, end) if pattern.match(lines[index])]
    if len(matches) > 1:
        raise Refusal(f"{len(matches)} entries for {key} in section '{heading}' of "
                      f"memory/STATUS.md")
    if line is None:
        if not matches:
            if section == AUTO_CLOSED:
                return text
            raise Correctable(f"no entry for {key} in section '{heading}' of memory/STATUS.md")
        del lines[matches[0]]
    elif matches:
        lines[matches[0]] = line
    else:
        position = add_position(lines, start, end, key)
        if position is None:
            last = max(index for index in range(start - 1, end) if lines[index].strip())
            if section == AUTO_CLOSED:
                closing = [""] if end < len(lines) or text.endswith("\n") else []
                del lines[last + 1:end]
            else:
                closing = [""] if last + 1 == end and end < len(lines) else []
            lines[last + 1:last + 1] = ["", line] + closing
        else:
            lines.insert(position, line)
    set_updated(lines, today)
    return "\n".join(lines)


def append_note(existing, content):
    content = content.rstrip("\n")
    if not existing:
        return content + "\n"
    return existing.rstrip("\n") + "\n\n" + content + "\n"


def section_body(lines, heading):
    start = lines.index(heading) + 1
    end = next((index for index in range(start, len(lines))
                if lines[index].startswith("## ")), len(lines))
    body = lines[start:end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body


def check_layout(lines):
    if [line for line in lines if line.startswith("## ")] != list(LAYOUT):
        raise Refusal("memory/STATUS.md is not in the four-section layout (already moved?)")


def open_ids(lines):
    entries = [ENTRY.match(line) for line in section_body(lines, "## Deferred")]
    return [entry["id"] for entry in entries
            if entry is not None and entry["verdict"] in OPEN_VERDICTS]


def check_deferred(text, opened):
    lines = text.rstrip("\n").split("\n")
    for index, line in enumerate(lines):
        if len(line) > 200:
            raise Refusal(f"line {index + 1} of the Deferred file is {len(line)} characters, "
                          f"over 200")
    blank = next((index for index, line in enumerate(lines) if not line.strip()), None)
    if blank is None:
        raise Refusal("the Deferred file has no blank line after its preamble")
    if blank > 3:
        raise Refusal(f"the Deferred file's preamble is {blank} lines, over 3")
    for index, line in enumerate(lines[:blank]):
        if ENTRY.match(line):
            raise Refusal(f"line {index + 1} of the Deferred file is an entry in the preamble")
    for index in range(blank + 1, len(lines)):
        if not lines[index].strip():
            raise Refusal(f"line {index + 1} of the Deferred file is a second blank line")
    ids = []
    for index in range(blank + 1, len(lines)):
        entry = ENTRY.match(lines[index])
        if entry is None:
            raise Refusal(f"line {index + 1} of the Deferred file is not an entry")
        if entry["verdict"] == "CLOSED":
            raise Refusal(f"line {index + 1} of the Deferred file is CLOSED entry {entry['id']}")
        if not OPEN_ENTRY.match(lines[index]):
            raise Refusal(f"line {index + 1} of the Deferred file: entry {entry['id']} is not "
                          f"in the open-entry form: OPEN or OPEN-DRIFTED, a known route, "
                          f"vYYYY-MM-DD, a title")
        ids.append(entry["id"])
    duplicated = list(dict.fromkeys(entry_id for entry_id in ids if ids.count(entry_id) > 1))
    if duplicated:
        raise Refusal(f"duplicate IDs in the Deferred file: {', '.join(duplicated)}")
    repeated = list(dict.fromkeys(entry_id for entry_id in opened if opened.count(entry_id) > 1))
    if repeated:
        raise Refusal(f"memory/STATUS.md lists open ID(s) more than once: {', '.join(repeated)}")
    if set(ids) != set(opened):
        missing = [entry_id for entry_id in opened if entry_id not in ids]
        extra = [entry_id for entry_id in ids if entry_id not in opened]
        raise Refusal(f"the Deferred file's IDs differ from the open entries of "
                      f"memory/STATUS.md: missing {', '.join(missing) or 'none'}; "
                      f"extra {', '.join(extra) or 'none'}")
    return ids


def plan_migration(status_text, deferred_text, day, today):
    lines = status_text.split("\n")
    if lines[-1] == "":
        lines.pop()
    check_layout(lines)
    kept = len(check_deferred(deferred_text, open_ids(lines)))
    deferred = section_body(lines, "## Deferred")
    entries = [ENTRY.match(line) for line in deferred]
    moved = sum(1 for entry in entries if entry is not None and entry["verdict"] == "CLOSED")
    head = lines[:lines.index("## Deferred")]
    set_updated(head, today)
    status = "\n".join(head) + "\n## Deferred\n\n" + deferred_text.rstrip("\n") + "\n"
    note_block = (f"# {day.isoformat()} — STATUS move: the Deferred register as it stood\n\n"
                  + "\n".join(deferred) + "\n")
    backlog = ("# Backlog candidates\n\n"
               + "\n".join(section_body(lines, "## Backlog candidates")) + "\n")
    notes = ("# Notes for future features\n\n"
             + "\n".join(section_body(lines, "## Notes for future features")) + "\n")
    return Migration(status, note_block, backlog, notes, kept, moved)


def normalise_path(path):
    path = DRIVE_FORM.sub(r"\1:", path)
    return path.replace("/", "\\").rstrip("\\").casefold()


def is_at_tree(cwd, tree):
    cwd, tree = normalise_path(cwd), normalise_path(tree)
    return cwd == tree or cwd.startswith(tree + "\\")


def started_after(later, earlier):
    numbers = all(isinstance(value, (int, float)) and not isinstance(value, bool)
                  for value in (later, earlier))
    return numbers and later > earlier


def list_command_in(text):
    lines = text.split("\n")
    if "## session-launch" not in lines:
        return None
    for line in lines[lines.index("## session-launch") + 1:]:
        if line.startswith("## "):
            return None
        if line.startswith(LIST_PREFIX):
            value = line[len(LIST_PREFIX):].strip()
            span = SPAN.search(value)
            if (value.casefold().startswith(UNBOUND_VALUES) or span is None
                    or span.group(1).strip().casefold() in UNBOUND_VALUES):
                return None
            return span.group(1)
    return None


def session_line(entry):
    fields = [str(entry.get(key) or "-") for key in ("id", "name", "kind")]
    return "  ".join(fields + [entry["cwd"], session_key(entry)])


def session_key(entry):
    return str(entry.get("sessionId") or "-")


def at_tree(sessions, tree):
    return [entry for entry in sessions
            if isinstance(entry, dict) and isinstance(entry.get("cwd"), str)
            and is_at_tree(entry["cwd"], tree)]


def fill_predecessor(text, source, ident):
    count = text.count(PREDECESSOR_TOKEN)
    if count != 1:
        raise Refusal(f"{source} holds {count} {PREDECESSOR_TOKEN} tokens, not one")
    fill = "" if ident == "none" else f' followed by "; predecessor {ident}"'
    return text.replace(PREDECESSOR_TOKEN, fill)


def fill_brief(text, brief):
    return BRIEF_TOKEN.join(piece if brief is None else piece.replace(BRIEF_TOKEN, brief)
                            for piece in text.split(BRIEF_ESCAPE))


def check_brief_tokens(texts, briefs):
    if briefs > 1:
        for source, text in texts:
            if any(BRIEF_TOKEN in piece for piece in text.split(BRIEF_ESCAPE)):
                raise Refusal(f"{source} holds a {BRIEF_TOKEN} token, and the write places "
                              f"{briefs} briefs, not one")


def check_record_name(name):
    if not RECORD_NAME.fullmatch(name):
        raise Refusal(f"{name} is not a .md file name without a path separator")
    folded = name.casefold()
    if folded in RESERVED_RECORDS or DATE.fullmatch(folded[:-len(".md")]):
        names = [Path(path).name for path in APPEND_PATHS]
        raise Refusal(f"memory/{name} is reserved: STATUS.md, a dated note YYYY-MM-DD.md, "
                      f"{', '.join(names[:-1])} or {names[-1]}")


def check_brief_name(name):
    if not BRIEF_NAME.fullmatch(name):
        raise Refusal(f"{name} is not a dated brief name YYYY-MM-DD-<slug>.md")


def status_set(root, section, source):
    path = root / "memory" / "STATUS.md"
    if not path.is_file():
        raise Refusal(f"no memory/STATUS.md under {root}")
    body = read_input(source)
    write_lf(path, replace_section(read_lf(path), section, body, datetime.date.today()))
    return 0


def status_line(root, section, key, source):
    path = root / "memory" / "STATUS.md"
    if not path.is_file():
        raise Refusal(f"no memory/STATUS.md under {root}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).digest()
    try:
        text = data.decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise Refusal(f"cannot read memory/STATUS.md: {error}") from None
    line = None if source is None else entry_line(read_input(source), key, source)
    changed = change_entry(text, section, key, line, datetime.date.today())
    if not path.is_file() or hashlib.sha256(path.read_bytes()).digest() != digest:
        raise Refusal("memory/STATUS.md changed since it was read; nothing written")
    write_lf(path, changed)
    return 0


def parse_day(date):
    if date is None:
        return datetime.date.today()
    try:
        if not DATE.fullmatch(date):
            raise ValueError
        return datetime.date.fromisoformat(date)
    except ValueError:
        raise Refusal(f"invalid --date {date}; expected YYYY-MM-DD") from None


def note_append(root, source, date):
    day = parse_day(date)
    memory = root / "memory"
    if not memory.is_dir():
        raise Refusal(f"no memory/ directory under {root}")
    content = read_input(source)
    path = memory / f"{day.isoformat()}.md"
    existing = read_lf(path) if path.is_file() else ""
    write_lf(path, append_note(existing, content))
    return 0


def status_migrate(root, source, date):
    day = parse_day(date)
    today = datetime.date.today()
    path = root / "memory" / "STATUS.md"
    if not path.is_file():
        raise Refusal(f"no memory/STATUS.md under {root}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).digest()
    try:
        text = data.decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise Refusal(f"cannot read memory/STATUS.md: {error}") from None
    targets = [root / "memory" / "backlog-candidates.md",
               root / "memory" / "notes-for-future-features.md"]
    for target in targets:
        if target.exists():
            raise Refusal(f"memory/{target.name} already exists")
    deferred_text = read_input(source)
    migration = plan_migration(text, deferred_text, day, today)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).digest() != digest:
        raise Refusal("memory/STATUS.md changed since it was read; nothing written")
    for target in targets:
        if target.exists():
            raise Refusal(f"memory/{target.name} already exists")
    note = root / "memory" / f"{day.isoformat()}.md"
    if note.is_file():
        try:
            read_lf(note)
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(f"cannot read memory/{day.isoformat()}.md: {error}") from None
    write_lf(targets[0], migration.backlog)
    write_lf(targets[1], migration.notes)
    write_lf(note, append_note(read_lf(note) if note.is_file() else "", migration.note_block))
    write_lf(path, migration.status)
    print(f"kept {migration.kept} open entries; moved {migration.moved} CLOSED entries and "
          f"the register's full text to memory/{day.isoformat()}.md")
    print("wrote memory/backlog-candidates.md and memory/notes-for-future-features.md")
    print(f"memory/STATUS.md: {len(data)} -> {len(migration.status.encode('utf-8'))} bytes")
    return 0


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, stdin=subprocess.DEVNULL,
                            capture_output=True)
    return (result.returncode, result.stdout.decode("utf-8", "replace"),
            result.stderr.decode("utf-8", "replace"))


def first_line(*outputs):
    for output in outputs:
        for line in output.splitlines():
            if line.strip():
                return line.strip()
    return "no output"


def memory_paths(root, paths):
    memory = (root / "memory").resolve()
    relative = []
    for path in paths:
        resolved = (root / path).resolve()
        if memory not in resolved.parents:
            raise Refusal(f"{path} is not a path below memory/")
        relative.append("memory/" + resolved.relative_to(memory).as_posix())
    return relative


def commit(root, message, paths):
    paths = memory_paths(root, paths)
    code, out, err = git(root, "add", "--", *paths)
    if code:
        raise Refusal(f"git add failed: {first_line(err, out)}")
    code, out, err = git(root, "commit", "-F", str(Path(message).resolve()), "--", *paths)
    if code:
        raise Refusal(f"nothing committed under memory/: {first_line(err, out)}")
    code, out, err = git(root, "log", "-1", "--format=%h %s")
    if code:
        raise Refusal(f"git log failed: {first_line(err, out)}")
    print(out.strip())
    return 0


def list_sessions(root):
    command = None
    for path in sorted((root / ".claude" / "bindings").glob("*.md")):
        text = read_lf(path)
        if "## session-launch" in text.split("\n"):
            command = list_command_in(text)
            break
    if command is None:
        return None
    try:
        result = subprocess.run(command, shell=True, capture_output=True, timeout=LIST_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise Refusal(f"List command timed out after {LIST_TIMEOUT}s: {command}") from None
    if result.returncode:
        raise Refusal(f"List command exited {result.returncode}: {command}")
    try:
        sessions = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        sessions = None
    if not isinstance(sessions, list):
        raise Refusal(f"List command output is not a JSON array: {command}")
    return sessions


def sessions_at(root, tree, vacant=False):
    sessions = list_sessions(root)
    if sessions is None:
        print("no List command bound", file=sys.stderr)
        return 2
    matched = at_tree(sessions, tree)
    for entry in matched:
        print(session_line(entry))
    return 3 if vacant and matched else 0


def sessions_new(root, tree, wait, since):
    saved = {line.rsplit("  ", 1)[-1].strip() for line in read_input(since).split("\n")
             if line.strip()}
    deadline = time.monotonic() + wait
    while True:
        sessions = list_sessions(root)
        if sessions is None:
            print("no List command bound", file=sys.stderr)
            return 2
        new = [entry for entry in at_tree(sessions, tree) if session_key(entry) not in saved]
        if new:
            for entry in new:
                print(session_line(entry))
            return 0
        left = deadline - time.monotonic()
        if left <= 0:
            raise Refusal(f"no new session at {tree} within {wait:g}s")
        time.sleep(min(WAIT_POLL, left))


def predecessor(root, tree, session_id):
    sessions = list_sessions(root)
    if sessions is None:
        print("no List command bound", file=sys.stderr)
        return 2
    entry = next((entry for entry in sessions
                  if isinstance(entry, dict) and entry.get("sessionId") == session_id), None)
    if entry is None:
        print("gone")
        return 0
    cwd = entry.get("cwd")
    if not (isinstance(cwd, str) and is_at_tree(cwd, tree)):
        print(f"elsewhere {cwd if isinstance(cwd, str) else '-'}")
        return 0
    if not any(other is not entry and isinstance(other, dict)
               and isinstance(other.get("cwd"), str) and is_at_tree(other["cwd"], tree)
               and started_after(other.get("startedAt"), entry.get("startedAt"))
               for other in sessions):
        print("alone")
        return 0
    if entry.get("id") in (None, ""):
        print("no-id")
        return 0
    print(f"stop {entry['id']}")
    return 0


def session_id():
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or "none"


class GitBackend:
    release_past_dirty = False
    leave_out_unchanged = False

    def __init__(self, root):
        self.root = root

    def main_name(self, value):
        return "master" if value is None else value

    def lock_dir(self):
        path = Path(self._run("read", "rev-parse", "--git-common-dir")
                    .decode("utf-8", "replace").strip())
        return path if path.is_absolute() else self.root / path

    def _run(self, step, *args):
        try:
            result = subprocess.run(["git", "-C", str(self.root), *args],
                                    stdin=subprocess.DEVNULL, capture_output=True)
        except FileNotFoundError:
            raise Refusal(f"{step}: git not found") from None
        if result.returncode:
            raise Refusal(f"{step}: " + first_line(result.stderr.decode("utf-8", "replace"),
                                                   result.stdout.decode("utf-8", "replace")))
        return result.stdout

    def branch(self):
        return self._run("read", "branch", "--show-current").decode("utf-8", "replace").strip()

    def dirty(self):
        output = self._run("read", "status", "--porcelain=v1", "-z", "--untracked-files=all")
        fields = iter(output.decode("utf-8", "replace").split("\0"))
        paths = []
        for entry in fields:
            if entry:
                paths.append(entry[3:])
                if {"R", "C"} & set(entry[:2]):
                    paths.append(next(fields))
        return paths

    def head(self):
        return self._run("read", "rev-parse", "HEAD").decode("utf-8", "replace").strip()

    def check_in(self, paths, message):
        indexed = self._run("check-in", "ls-files", "-z", "--",
                            *paths).decode("utf-8", "replace").split("\0")
        added = [path for path in paths
                 if path in indexed or os.path.lexists(self.root / path)]
        if added:
            self._run("check-in", "add", "--", *added)
        self._run("check-in", "commit", "-F", os.path.abspath(message), "--", *paths)

    def unstage(self, paths):
        self._run("check-in", "reset", "-q", "--", *paths)

    def blob(self, commit, path):
        return self._run("pin", "show", f"{commit}:{path}")

    def parent(self, commit):
        return self._run("pin", "rev-parse", f"{commit}^").decode("utf-8", "replace").strip()

    def changed(self, commit):
        output = self._run("pin", "diff-tree", "-r", "--no-commit-id", "--name-only", "-z", commit)
        return [path for path in output.decode("utf-8", "replace").split("\0") if path]

    def summary(self, commit):
        return self._run("pin", "log", "-1", "--format=%h %s",
                         commit).decode("utf-8", "replace").strip()


def run_argv(argv):
    return subprocess.run(argv, cwd=tempfile.gettempdir(), stdin=subprocess.DEVNULL,
                          capture_output=True)


def cm_lines(data):
    lines = [line[:-1] if line.endswith("\r") else line
             for line in data.decode("utf-8", "surrogateescape").split("\n")]
    return [line for line in lines if line.strip()]


class PlasticBackend:
    release_past_dirty = True
    leave_out_unchanged = True

    def __init__(self, root):
        self.root = root
        self.spec = None

    def main_name(self, value):
        name = "main" if value is None else value
        return name[1:] if name.startswith("/") else name

    def lock_dir(self):
        path = self.root / ".plastic"
        if not path.is_dir():
            raise Refusal(f"read: {os.path.abspath(self.root)} is not a Plastic workspace "
                          f"(no .plastic)")
        return path

    def _client(self):
        return [shutil.which("cm")]

    def _cm(self, step, *args):
        client = self._client()
        if client[0] is None:
            raise Refusal(f"{step}: cm not found")
        try:
            result = run_argv([*client, *args])
        except FileNotFoundError:
            raise Refusal(f"{step}: cm not found") from None
        if result.returncode:
            raise Refusal(f"{step}: " + first_line(result.stderr.decode("utf-8", "replace"),
                                                   result.stdout.decode("utf-8", "replace")))
        return result.stdout

    def branch(self):
        root = os.path.abspath(self.root)
        if not root.isascii():
            raise Refusal(f"read: {root}: non-ASCII hub root")
        lines = cm_lines(self._cm("read", "wi", root))
        match = BRANCH_LINE.fullmatch(lines[0]) if lines else None
        if match is None or len(lines) > 1:
            line = "no output" if not lines else lines[0] if match is None else lines[1]
            raise Refusal(f"read: cm wi: unrecognised line: {line}")
        self.spec = match.group(2)
        name = match.group(1)
        return name[1:] if name.startswith("/") else name

    def head(self):
        lines = cm_lines(self._cm("read", "status", os.path.abspath(self.root), "--header",
                                  "--machinereadable"))
        for line in lines:
            header = STATUS_HEADER.match(line)
            if header is not None:
                return header.group(1)
        raise Refusal(f"read: cm status: no STATUS header: {lines[0] if lines else 'no output'}")

    def dirty(self):
        root = os.path.abspath(self.root)
        if not root.isascii():
            raise Refusal(f"read: {root}: non-ASCII hub root")
        script = os.path.join(root, ".claude", "references", "vc-plastic", "clean-read.py")
        if not os.path.isfile(script):
            raise Refusal(f"read: no Clean read at {script}")
        result = run_argv([sys.executable, "-B", script, root])
        if result.returncode:
            raise Refusal("read: " + first_line(result.stdout.decode("utf-8", "replace"),
                                                result.stderr.decode("utf-8", "replace")))
        prefix = os.path.normcase(root) + os.sep
        paths = [line[len(prefix):].replace("\\", "/")
                 if os.path.normcase(line).startswith(prefix) else line
                 for line in cm_lines(result.stdout)]
        return [path for path in paths
                if not any(other.startswith(path + "/") for other in paths)]

    def _path(self, path):
        return os.path.join(os.path.abspath(self.root), *path.split("/"))

    def _status(self):
        lines = cm_lines(self._cm("check-in", "status", os.path.abspath(self.root),
                                  "--machinereadable"))
        index = next((index for index, line in enumerate(lines)
                      if STATUS_HEADER.match(line)), None)
        if index is None:
            raise Refusal(f"check-in: cm status: no STATUS header: "
                          f"{lines[0] if lines else 'no output'}")
        kinds = {}
        for line in lines[:index] + lines[index + 1:]:
            kind, _, rest = line.partition(" ")
            fields = rest.rsplit(" ", 2)
            if len(fields) != 3 or fields[1] not in ("True", "False") or fields[2] != "NO_MERGES":
                raise Refusal(f"check-in: cm status: unrecognised line: {line}")
            move = MOVE_TEXT.fullmatch(fields[0])
            if move:
                source, destination = move.groups()
                kinds[os.path.normcase(source)] = (kind, None)
                kinds[os.path.normcase(destination)] = (kind, source)
            else:
                kinds[os.path.normcase(fields[0])] = (kind, None)
        return STATUS_HEADER.match(lines[index]).group(1), kinds

    def check_in(self, paths, message):
        for path in paths:
            if not path.isascii():
                raise Refusal(f"check-in: {path}: non-ASCII name")
        n, kinds = self._status()
        memory = os.path.normcase(os.path.join(os.path.abspath(self.root), "memory")) + os.sep
        private = []
        everything = False
        for path in paths:
            kind = kinds.get(os.path.normcase(self._path(path)))
            if kind is None:
                raise Refusal(f"check-in: {path}: unlisted")
            if kind[0] == "PR":
                private.append(path)
            elif kind[0] == "LD":
                everything = True
            elif not (kind[0] in ("CH", "CO", "AD", "DE")
                      or kind[0] in ("MV", "CH+MV") and kind[1] is not None
                      and os.path.normcase(kind[1]).startswith(memory)):
                raise Refusal(f"check-in: {path}: {kind[0]}")
        files, directories = [], []
        checking_in = False
        try:
            for path in private:
                for line in cm_lines(self._cm("check-in", "add", self._path(path))):
                    item = ADDED_ITEM.fullmatch(line)
                    if item is None:
                        continue
                    if os.path.normcase(item.group(1)) == os.path.normcase(self._path(path)):
                        files.append(self._path(path))
                    else:
                        directories.append(item.group(1))
            checking_in = True
            self._cm("check-in", "ci", *(self._path(path) for path in paths),
                     *(["--all"] if everything else []),
                     f"-commentsfile={os.path.abspath(message)}")
        except Exception as error:
            if checking_in:
                try:
                    moved = self.head() != n
                except Exception:
                    moved = True
                if moved:
                    raise
            failed = []
            for item in files + sorted(directories, key=lambda item: len(Path(item).parts),
                                       reverse=True):
                try:
                    self._cm("check-in", "undo", item)
                except Exception as failure:
                    failed.append(f"{item} ({failure})")
            if failed:
                raise Refusal(f"{error}; not undone: {', '.join(failed)}") from error
            raise

    def unstage(self, paths):
        n, kinds = self._status()
        undone = []
        for path in paths:
            kind = kinds.get(os.path.normcase(self._path(path)))
            if (kind is not None and kind[0] in ("CO", "CH")
                    and raw_bytes(self.root / path) == self.blob(n, path)):
                self._cm("check-in", "undo", self._path(path))
                undone.append(path)
        if undone:
            n, kinds = self._status()
            for path in undone:
                kind = kinds.get(os.path.normcase(self._path(path)))
                if (kind is not None and kind[0] in ("CO", "CH")
                        and raw_bytes(self.root / path) == self.blob(n, path)):
                    raise Refusal(f"check-in: {path}: still {kind[0]} after cm undo")

    def _spec(self):
        if self.spec is None:
            self.branch()
        return self.spec

    def blob(self, commit, path):
        directory = tempfile.mkdtemp()
        try:
            target = os.path.join(directory, "blob")
            self._cm("pin", "cat", f"{self._path(path)}#cs:{commit}", f"--file={target}")
            try:
                return Path(target).read_bytes()
            except OSError:
                raise Refusal(f"pin: cm cat wrote no file for {path}") from None
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def parent(self, commit):
        lines = cm_lines(self._cm("pin", "find", "changeset", f"where changesetid={commit}",
                                  "--format={changesetid}|{parent}|{branch}", "--nototal",
                                  "on", "repository", f"'{self._spec()}'"))
        match = re.fullmatch(rf"{re.escape(commit)}\|(-?\d+)\|.*", lines[0]) if lines else None
        if match is None or len(lines) > 1:
            line = "no output" if not lines else lines[0] if match is None else lines[1]
            raise Refusal(f"pin: cm find: unrecognised line: {line}")
        return match.group(1)

    def changed(self, commit):
        lines = cm_lines(self._cm("pin", "log", f"cs:{commit}@rep:{self._spec()}",
                                  "--csformat={changesetid}|{newline}{items}",
                                  "--itemformat={path}|{shortstatus}|{fullstatus}{newline}"))
        if not lines or lines[0] != f"{commit}|":
            raise Refusal(f"pin: cm log: unrecognised line: {lines[0] if lines else 'no output'}")
        paths = []
        for line in lines[1:]:
            fields = line.rsplit("|", 2)
            if len(fields) != 3 or not fields[0].startswith("/"):
                raise Refusal(f"pin: cm log: unrecognised line: {line}")
            path = fields[0][1:]
            if path and not (self.root / path).is_dir():
                paths.append(path)
        return paths

    def summary(self, commit):
        lines = cm_lines(self._cm("pin", "find", "changeset", f"where changesetid={commit}",
                                  "--format={changesetid}|{comment}", "--nototal",
                                  "--encoding=utf-8", "on", "repository", f"'{self._spec()}'"))
        if not lines or not lines[0].startswith(f"{commit}|"):
            raise Refusal(f"pin: cm find: unrecognised line: "
                          f"{lines[0] if lines else 'no output'}")
        return f"cs:{commit} {lines[0][len(commit) + 1:]}"


def vc_system_in(text):
    section = False
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line.rstrip() == "## vc"
        elif section and line.startswith(SYSTEM_PREFIX):
            return line[len(SYSTEM_PREFIX):].strip()
    return None


def backend_for(root):
    for path in sorted((root / ".claude" / "bindings").glob("*.md")):
        if not path.is_file():
            continue
        try:
            value = vc_system_in(read_lf(path))
        except (OSError, UnicodeDecodeError) as error:
            raise Refusal(f"read: cannot read {path}: {error}") from None
        if value is None:
            continue
        if re.match(r"Plastic SCM", value, re.IGNORECASE):
            return PlasticBackend(root)
        if re.match(r"git\b", value, re.IGNORECASE):
            return GitBackend(root)
        raise Refusal(f"read: the vc binding's System names neither git nor Plastic SCM: "
                      f"{value}")
    return GitBackend(root)


class HubLock:
    def __init__(self, backend):
        self.path = backend.lock_dir() / LOCK_NAME

    def read(self):
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return None
        except PermissionError:
            return "being written"
        try:
            record = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "being written"
        return record if isinstance(record, dict) else "being written"

    def take(self, purpose, wait):
        record = {"session": session_id(), "pid": os.getpid(),
                  "time": datetime.datetime.now(datetime.timezone.utc)
                  .strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "purpose": purpose, "state": "active", "reason": None, "commit": None,
                  "paths": []}
        data = (json.dumps(record) + "\n").encode("utf-8")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
        deadline = time.monotonic() + wait
        while True:
            try:
                descriptor = os.open(self.path, flags)
                break
            except (FileExistsError, PermissionError):
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    time.sleep(min(LOCK_POLL, remaining))
                    continue
                holder = self.read()
                if holder is None:
                    raise Refusal(f"lock: cannot create {self.path}") from None
                if holder == "being written":
                    raise Refusal("lock: held, record being written") from None
                refusal = (f"lock: held by session {holder.get('session')} since "
                           f"{holder.get('time')}")
                if holder.get("state") == "held":
                    refusal += (f", state held, reason {holder.get('reason')}, commit "
                                f"{holder.get('commit')}")
                raise Refusal(refusal) from None
            except OSError as error:
                raise Refusal(f"lock: {error}") from None
        try:
            written = 0
            while written < len(data):
                written += os.write(descriptor, data[written:])
        except OSError as error:
            os.close(descriptor)
            os.unlink(self.path)
            raise Refusal(f"lock: {error}") from None
        os.close(descriptor)
        self.taken = record
        return record

    def not_taken(self, step):
        holder = self.read()
        if holder is None:
            who = "the lock is free"
        elif holder == "being written":
            who = "record being written"
        else:
            who = f"held by session {holder.get('session')} since {holder.get('time')}"
        return Refusal(f"{step}: the lock is not this command's take; {who}")

    def release_own(self):
        if self.read() != self.taken:
            raise self.not_taken("release")
        self._unlink()

    def hold(self, reason, commit, paths):
        if self.read() != self.taken:
            raise self.not_taken("hold")
        record = dict(self.taken, state="held", reason=reason, commit=commit,
                      paths=list(paths))
        data = (json.dumps(record) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(self.path, flags)
        except OSError as error:
            raise Refusal(f"hold: {error}") from None
        try:
            written = 0
            while written < len(data):
                written += os.write(descriptor, data[written:])
        except OSError as error:
            raise Refusal(f"hold: {error}") from None
        finally:
            os.close(descriptor)

    def release(self, session):
        holder = self.read()
        if holder is None:
            raise Refusal("release: the lock is free")
        if holder == "being written":
            raise Refusal("release: held, record being written; the override is clear --release")
        if holder.get("state") == "held":
            raise Refusal(f"release: held, reason {holder.get('reason')}, commit "
                          f"{holder.get('commit')}; the override is clear --release")
        if holder.get("session") != session or "none" in (holder.get("session"), session):
            raise Refusal(f"release: held by session {holder.get('session')} since "
                          f"{holder.get('time')}, not this session ({session}); the override "
                          f"is clear --release")
        self._unlink()

    def clear(self):
        return self._unlink()

    def _unlink(self):
        deadline = time.monotonic() + 1
        while True:
            try:
                os.unlink(self.path)
                return True
            except FileNotFoundError:
                return False
            except PermissionError as error:
                if time.monotonic() >= deadline:
                    raise Refusal(f"release: cannot remove {self.path}: {error}") from None
                time.sleep(LOCK_POLL)


def lock_take(root):
    record = HubLock(backend_for(root)).take("merge", LOCK_WAIT)
    print(json.dumps(record))
    return 0


def lock_release(root):
    HubLock(backend_for(root)).release(session_id())
    print("released")
    return 0


def plan_edits(root, resolved, day, today, next_free=False):
    current = None
    try:
        memory = root / "memory"
        if not memory.is_dir():
            raise Refusal(f"no memory/ directory under {root}")
        placed = {}
        drafted = [Path(values[0]).name for kind, values, _ in resolved if kind == "brief"]
        if next_free:
            for name in drafted:
                if name in placed:
                    continue
                stem, suffix = os.path.splitext(name)
                candidate, number = name, 1
                while ((memory / "handoffs" / candidate).exists()
                       or candidate in placed.values()
                       or candidate != name and candidate in drafted):
                    number += 1
                    candidate = f"{stem}-{number}{suffix}"
                placed[name] = candidate
        cited = (f"memory/handoffs/{placed.get(drafted[0], drafted[0])}"
                 if len(drafted) == 1 else None)
        status = "memory/STATUS.md"
        note = f"memory/{day.isoformat()}.md"
        kinds = [kind for kind, _, _ in resolved]
        reads = []
        if {"entry", "remove-entry", "section"} & set(kinds):
            if not (root / status).is_file():
                raise Refusal(f"no memory/STATUS.md under {root}")
            reads.append(status)
        if "note" in kinds:
            reads.append(note)
        for kind, values, _ in resolved:
            if kind == "append" and values[0] not in reads:
                reads.append(values[0])
        before = {}
        for path in reads:
            try:
                before[path] = read_lf(root / path) if (root / path).is_file() else ""
            except (OSError, UnicodeDecodeError) as error:
                raise Refusal(f"cannot read {path}: {error}") from None
        after = dict(before)
        for kind, values, text in resolved:
            current = edit_words(kind, values)
            if kind in ("entry", "remove-entry"):
                line = None if text is None else fill_brief(text, cited)
                after[status] = change_entry(after[status], values[0], values[1], line, today)
            elif kind == "section":
                after[status] = replace_section(after[status], values[0], text, today)
            elif kind == "note":
                after[note] = append_note(after[note], fill_brief(text, cited))
            elif kind == "append":
                after[values[0]] = append_note(after[values[0]], text)
            elif kind == "record":
                name = Path(values[0]).name
                record = f"memory/{name}"
                if any(path.casefold() == record.casefold() for path in after):
                    raise Correctable(f"two --record files named {name}")
                if (root / record).exists():
                    raise Refusal(f"{record} already exists")
                after[record] = text
            else:
                name = Path(values[0]).name
                brief = f"memory/handoffs/{placed.get(name, name)}"
                if brief in after:
                    raise Correctable(f"two --brief files named {name}")
                if (root / brief).exists():
                    raise Refusal(f"{brief} already exists")
                after[brief] = text
        changed = {path: text for path, text in after.items() if before.get(path) != text}
        if not changed:
            raise Refusal("nothing changes")
        return changed, placed, cited
    except Correctable as refusal:
        raise Correctable(f"edit: {refusal}", quoted(current) if current else None) from None
    except Refusal as refusal:
        raise Refusal(f"edit: {refusal}") from None


def edit_words(kind, values):
    words = [f"--{kind}"]
    words += [os.path.abspath(value) if metavar == "FILE" else value
              for metavar, value in zip(EDITS[kind], values)]
    return words


def quoted(words):
    return " ".join(shlex.quote(word) for word in words)


def rerun_line(args):
    words = ["py", os.path.abspath(__file__), args.command]
    if args.command == "lock":
        words.append(args.action)
    words += ["--root", os.path.abspath(args.root)]
    if args.command == "write":
        day = getattr(args, "day", None)
        if day is None and args.date is None:
            day = parse_day(None)
        words += ["--message", os.path.abspath(args.message),
                  "--date", day.isoformat() if day else args.date]
        if args.main is not None:
            words += ["--main", args.main]
        if args.predecessor:
            words.append("--predecessor")
        if args.next_free:
            words.append("--next-free")
        for kind, values in args.edits:
            words += edit_words(kind, values)
    return "re-run: " + quoted(words)


def clear_command(root):
    return quoted(["py", os.path.abspath(__file__), "clear", "--root",
                   os.path.abspath(root)])


def held(lock, root, cause, reason, commit, paths):
    message = (f"{cause}; held, reason {reason}, commit {commit or 'none'}, "
               f"paths {' '.join(paths)}")
    try:
        lock.hold(reason, commit, paths)
    except Exception as failure:
        message += f"; record not rewritten: {failure}"
    return Held(f"{message}\nclear: {clear_command(root)}")


def restore(backend, lock, paths, snapshot, made_dir, cause):
    root = backend.root
    failed = {}
    for path in paths:
        try:
            if snapshot[path] is None:
                (root / path).unlink(missing_ok=True)
            else:
                (root / path).write_bytes(snapshot[path])
        except Exception as error:
            failed[path] = str(error)
    if made_dir:
        try:
            (root / "memory" / "handoffs").rmdir()
        except OSError:
            pass
    try:
        backend.unstage(paths)
    except Exception as error:
        for path in paths:
            failed.setdefault(path, str(error))
    for path in paths:
        if path in failed:
            continue
        try:
            if raw_bytes(root / path) != snapshot[path]:
                failed[path] = "bytes differ"
        except Exception as error:
            failed[path] = str(error)
    if failed:
        listed = [path for path in paths if path in failed]
        raise held(lock, root, f"{cause}; restore failed: "
                   + ", ".join(f"{path} ({failed[path]})" for path in listed),
                   "restore-failed", None, listed)
    try:
        lock.release_own()
    except Exception as error:
        raise held(lock, root, f"{cause}; restored; {error}", "unexpected", None,
                   paths) from error
    raise Refusal(f"{cause}; restored, the lock released")


def land(backend, lock, base, paths, expected, message, snapshot, made_dir=False):
    root = backend.root
    try:
        backend.check_in(paths, message)
    except Exception as error:
        cause = str(error) if isinstance(error, Refusal) else f"check-in: {error}"
        try:
            current = backend.head()
        except Exception as failure:
            raise held(lock, root, cause, "unexpected", None, paths) from failure
        if current == base:
            restore(backend, lock, paths, snapshot, made_dir, cause)
    new = None
    try:
        new = backend.head()
        if backend.parent(new) != base:
            raise held(lock, root, f"pin: the parent of {new} is not {base}",
                       "pin-mismatch", new, paths)
        changed = set(backend.changed(new))
        if changed != set(paths):
            raise held(lock, root, f"pin: {new} changes {' '.join(sorted(changed))}, "
                       f"not {' '.join(paths)}", "pin-mismatch", new,
                       sorted(changed ^ set(paths)))
        differing = []
        for path in paths:
            try:
                data = backend.blob(new, path)
            except Refusal:
                data = None
            if data != expected[path]:
                differing.append(path)
        if differing:
            raise held(lock, root, f"pin: {' '.join(differing)} at {new} differs from the "
                       f"bytes written", "pin-mismatch", new, differing)
        summary = backend.summary(new)
        lock.release_own()
    except Held:
        raise
    except Exception as error:
        raise held(lock, root, str(error), "unexpected", new, paths) from error
    return summary


def hub_write(args):
    backend = backend_for(args.root)
    args.main = backend.main_name(args.main)
    ident = session_id()
    try:
        part = ["--date", args.date]
        args.day = parse_day(args.date)
        part = ["--message", os.path.abspath(args.message)]
        message_text = read_input(args.message)
        if not message_text.strip():
            raise Refusal(f"{args.message} is blank")
        resolved = []
        for kind, values in args.edits:
            part = edit_words(kind, values)
            if kind == "append" and values[0] not in APPEND_PATHS:
                raise Refusal(f"--append {values[0]}: not {', '.join(APPEND_PATHS[:-1])} "
                              f"or {APPEND_PATHS[-1]}")
            if kind == "record":
                try:
                    check_record_name(Path(values[0]).name)
                except Refusal as refusal:
                    raise Refusal(f"--record {values[0]}: {refusal}") from None
            if kind == "brief":
                try:
                    check_brief_name(Path(values[0]).name)
                except Refusal as refusal:
                    raise Refusal(f"--brief {values[0]}: {refusal}") from None
            if kind == "entry":
                text = entry_line(read_input(values[2]), values[1], values[2])
            elif kind == "remove-entry":
                text = None
            else:
                text = read_input(values[-1])
                if kind == "brief" and args.predecessor:
                    text = fill_predecessor(text, values[0], ident)
            resolved.append((kind, values, text))
        count = sum(kind == "brief" for kind, _, _ in resolved)
        part = ["--message", os.path.abspath(args.message)]
        check_brief_tokens([(args.message, message_text)], count)
        for kind, values, text in resolved:
            if kind in ("note", "entry"):
                part = edit_words(kind, values)
                check_brief_tokens([(values[-1], text)], count)
    except Refusal as refusal:
        raise Correctable(f"input: {refusal}", quoted(part)) from None
    lock = HubLock(backend)
    lock.take("write", LOCK_WAIT)
    try:
        branch = backend.branch()
        if branch != args.main:
            raise Refusal(f"read: on branch {branch or 'detached HEAD'}, not {args.main}")
        dirty = backend.dirty()
        if dirty:
            message = f"read: not clean: {' '.join(dirty)}"
            stray = [path for path in dirty if path.startswith("memory/")]
            if stray:
                raise Stray(message, f"stray: {' '.join(stray)} changed outside hub.py "
                            f"write; clear: {clear_command(args.root)}, then its "
                            f"--check-in on the human's word")
            raise Refusal(message)
        base = backend.head()
        edits, placed, cited = plan_edits(args.root, resolved, args.day,
                                          datetime.date.today(), args.next_free)
        paths = sorted(edits)
        try:
            snapshot = {path: raw_bytes(args.root / path) for path in paths}
        except OSError as error:
            raise Refusal(f"edit: {error}") from None
        briefs = any(path.startswith("memory/handoffs/") for path in paths)
        made_dir = briefs and not (args.root / "memory" / "handoffs").exists()
        message = args.message
        filled = fill_brief(message_text, cited)
        if filled != message_text:
            descriptor, message = tempfile.mkstemp(prefix="hub-write-", suffix=".txt")
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(filled.encode("utf-8"))
    except Exception as error:
        try:
            lock.release_own()
        except Refusal as failure:
            raise Refusal(f"{error}; {failure}") from error
        raise
    try:
        try:
            if briefs:
                (args.root / "memory" / "handoffs").mkdir(exist_ok=True)
            for path in paths:
                write_lf(args.root / path, edits[path])
        except Exception as error:
            cause = f"edit: {error}"
            restore(backend, lock, paths, snapshot, made_dir, cause)
        print(land(backend, lock, base, paths,
                   {path: edits[path].encode("utf-8") for path in paths}, message,
                   snapshot, made_dir))
    finally:
        if message != args.message:
            Path(message).unlink(missing_ok=True)
    for name in placed.values():
        print(f"brief: memory/handoffs/{name}")
    if args.predecessor and ident == "none":
        print("predecessor: none")
    return 0


def hub_clear(args):
    backend = backend_for(args.root)
    args.main = backend.main_name(args.main)
    lock = HubLock(backend)
    holder = lock.read()
    if holder is None:
        print("lock: free")
    elif holder == "being written":
        print("lock: record being written")
    else:
        fields = []
        for key in ("session", "pid", "time", "purpose", "state", "reason", "commit",
                    "paths"):
            value = holder.get(key)
            if isinstance(value, list):
                value = " ".join(str(item) for item in value)
            fields.append(f"{key} {'none' if value in (None, '') else value}")
        print("lock: " + ", ".join(fields))
    try:
        dirty = backend.dirty()
    except Refusal as refusal:
        if not (args.release and backend.release_past_dirty):
            raise
        print(f"dirty: unknown ({refusal})")
    else:
        for path in dirty:
            place = "in" if path.startswith("memory/") else "outside"
            print(f"dirty {place} memory/: {path}")
        if not dirty:
            print("dirty: none")
    if args.release:
        print("released" if lock.clear() else "release: the lock was free")
    if not args.check_in:
        return 0
    branch = backend.branch()
    if branch != args.main:
        raise Refusal(f"read: on branch {branch or 'detached HEAD'}, not {args.main}")
    lock.take("clear", LOCK_WAIT)
    message = None
    try:
        try:
            paths = sorted(path for path in backend.dirty() if path.startswith("memory/"))
            if paths:
                base = backend.head()
                try:
                    snapshot = {path: raw_bytes(args.root / path) for path in paths}
                except OSError as error:
                    raise Refusal(f"check-in: {error}") from None
                if backend.leave_out_unchanged:
                    unchanged = []
                    for path in paths:
                        try:
                            if (snapshot[path] is not None
                                    and backend.blob(base, path) == snapshot[path]):
                                unchanged.append(path)
                        except Refusal:
                            pass
                    if unchanged:
                        backend.unstage(unchanged)
                        paths = [path for path in paths if path not in unchanged]
            if paths:
                lines = [path if snapshot[path] is not None else f"{path} (deleted)"
                         for path in paths]
                descriptor, message = tempfile.mkstemp(prefix="hub-clear-", suffix=".txt")
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(("hub.py clear: check in memory/ paths\n\n"
                                  + "\n".join(lines) + "\n").encode("utf-8",
                                                                    "backslashreplace"))
        except Exception as error:
            try:
                lock.release_own()
            except Refusal as failure:
                raise Refusal(f"{error}; {failure}") from error
            raise
        if not paths:
            lock.release_own()
            print("nothing to check in")
            return 0
        print(land(backend, lock, base, paths, snapshot, message, snapshot))
        return 0
    finally:
        if message is not None:
            Path(message).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="hub.py",
        description="The hub's fragile manual steps as eleven commands: status set, status line, "
                    "status migrate, note append, commit, sessions-at, predecessor, lock take, "
                    "lock release, write and clear. "
                    "Write the hub's memory files as LF bytes, commit named paths under "
                    "memory/ alone, list the running sessions at a tree, print a "
                    "handed-off session's case, take or release the hub's lock around a "
                    "merge, make one hub write under the lock as one pinned commit, and "
                    "show, release or check in a held or dirty hub with clear. "
                    "This is the base script that runs version-control and bound commands "
                    "(git, cm, the hub's bound Clean read and the bound List command); "
                    "harness.py runs one command, doctor's read-only git check-ignore. Each "
                    "invocation is one command, so a permission allow rule can match it. "
                    "A refusal prints one line on stderr, exits 1 and leaves nothing written; "
                    "write and lock take add a re-run line, write prints, before its re-run "
                    "line, a correct: line naming the argument to correct where its own input "
                    "or edit is refused, and write and clear exit 3 when they hold the lock on "
                    "their own failure, printing a clear: line.")
    rooted = argparse.ArgumentParser(add_help=False)
    rooted.add_argument("--root", type=Path, default=Path.cwd(),
                        help="the checkout whose memory/ is read and written "
                             "(default: the current working directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser(
        "status", help="edit memory/STATUS.md",
        description="status set, status line and status migrate edit memory/STATUS.md.")
    status_actions = status.add_subparsers(dest="action", required=True)
    setter = status_actions.add_parser(
        "set", parents=[rooted], help="replace one ## section's body and date the file",
        description="status set SECTION --from FILE replaces one ##  section's body of "
                    "memory/STATUS.md and dates its updated: line. It writes UTF-8 bytes with "
                    "LF line endings, whatever the input's endings.")
    setter.add_argument("section", help="the section heading's text after '## '")
    setter.add_argument("--from", dest="source", required=True, metavar="FILE",
                        help="the file holding the new body")
    liner = status_actions.add_parser(
        "line", parents=[rooted],
        help="add, replace or remove one entry of a ## section and date the file",
        description="status line SECTION KEY --from FILE adds or replaces the one entry of that "
                    "section whose line starts - **KEY, and status line SECTION KEY --remove "
                    "removes it, reading and writing the file in one invocation and leaving "
                    "every other line as it is. In status line and write's --entry and "
                    "--remove-entry, section Auto-closed alone is created by an add at the "
                    "file's end, and a removal finding no entry or no section changes nothing; "
                    "every other section refuses both. It writes UTF-8 bytes with LF line "
                    "endings, whatever the input's endings.")
    liner.add_argument("section", help="the section heading's text after '## '; "
                                       "`Auto-closed` is created by an add, and a removal "
                                       "it lacks changes nothing")
    liner.add_argument("key", help="the entry's key: its line starts '- **KEY', "
                                   "or KEY in backticks")
    change = liner.add_mutually_exclusive_group(required=True)
    change.add_argument("--from", dest="source", metavar="FILE",
                        help="the file holding the entry's one line")
    change.add_argument("--remove", action="store_true", help="remove the entry")
    migrator = status_actions.add_parser(
        "migrate", parents=[rooted],
        help="move a four-section memory/STATUS.md to Current and the open Deferred entries, "
             "once",
        description="status migrate --deferred FILE [--date YYYY-MM-DD] moves a four-section "
                    "memory/STATUS.md once: the old ## Deferred body to the dated note, the two "
                    "registers to memory/backlog-candidates.md and "
                    "memory/notes-for-future-features.md, and FILE, one line per open entry, "
                    "into ## Deferred after ## Current.")
    migrator.add_argument("--deferred", required=True, metavar="FILE",
                          help="the file holding the new ## Deferred body: the preamble, "
                               "one blank line, one line per open entry")
    migrator.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                          help="the date of the dated note and of its block heading "
                               "(default: today)")
    note = commands.add_parser(
        "note", help="edit the dated session note",
        description="note append appends to the dated session note memory/<date>.md.")
    note_actions = note.add_subparsers(dest="action", required=True)
    appender = note_actions.add_parser(
        "append", parents=[rooted], help="append to memory/<date>.md",
        description="note append --from FILE [--date YYYY-MM-DD] appends to the dated session "
                    "note memory/<date>.md. It writes UTF-8 bytes with LF line endings, "
                    "whatever the input's endings.")
    appender.add_argument("--from", dest="source", required=True, metavar="FILE",
                          help="the file holding the text to append")
    appender.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                          help="the note's date (default: today)")
    committer = commands.add_parser(
        "commit", parents=[rooted], help="commit the named paths under memory/ and only those",
        description="commit --message FILE PATH [PATH ...] commits the named paths under "
                    "memory/ and nothing else.")
    committer.add_argument("--message", required=True, metavar="FILE",
                           help="the commit message file, passed to git as is")
    committer.add_argument("paths", nargs="+", metavar="PATH",
                           help="a path below memory/ to commit, relative to --root or absolute")
    lister = commands.add_parser(
        "sessions-at", parents=[rooted],
        help="list the running sessions whose working directory is at or under TREE",
        description="sessions-at TREE lists the running Claude sessions whose working directory "
                    "is TREE or lies under it, through the project's bound List command, one "
                    "line each, its last field the session's full id; --vacant exits 3 when "
                    "any is listed, and --wait SECONDS --since FILE re-reads the list until a "
                    "session at TREE appears whose id ends no line of FILE, an earlier run's "
                    "output redirected there, exiting 1 when the window passes.")
    lister.add_argument("tree", help="the working tree to match")
    lister.add_argument("--vacant", action="store_true",
                        help="exit 3 when any session is at TREE, after printing them")
    lister.add_argument("--wait", type=float, default=None, metavar="SECONDS",
                        help="re-read the list until a session at TREE whose id ends no line "
                             "of the --since file appears, print it and exit 0; exit 1 when "
                             "SECONDS pass; only with --since, never with --vacant")
    lister.add_argument("--since", default=None, metavar="FILE",
                        help="the output an earlier sessions-at printed, redirected to FILE, "
                             "whose ids, each line's last field, --wait does not count as "
                             "new; only with --wait")
    reader = commands.add_parser(
        "predecessor", parents=[rooted],
        help="print the case of the handed-off session SESSION_ID at TREE: gone, elsewhere, "
             "alone, no-id or stop",
        description="predecessor TREE SESSION_ID prints the case of the session SESSION_ID at "
                    "TREE from the same list: gone, elsewhere <cwd>, alone, no-id or stop <id>.")
    reader.add_argument("tree", help="the working tree the session was handed off in")
    reader.add_argument("session_id", help="the predecessor's full session id")
    locker = commands.add_parser(
        "lock", help="take or release the hub's lock around a merge",
        description="lock take takes the hub's lock file in the repository's common git "
                    "directory, or a Plastic SCM workspace's .plastic/, for a merge, and lock "
                    "release frees it for the session holding it.")
    lock_actions = locker.add_subparsers(dest="action", required=True)
    lock_actions.add_parser(
        "take", parents=[rooted],
        help="take the lock, waiting briefly while another holds it; print the record",
        description="lock take takes the hub's lock file in the repository's common git "
                    "directory, or a Plastic SCM workspace's .plastic/, for a merge.")
    lock_actions.add_parser(
        "release", parents=[rooted], help="release the lock this session holds",
        description="lock release frees the hub's lock for the session holding it.")
    writer = commands.add_parser(
        "write", parents=[rooted],
        help="under the lock, on the main branch and clean, write the edits and commit "
             "exactly them as one pinned commit",
        description="Under the lock, on the main branch and clean, write the edits and "
                    "commit exactly them as one pinned commit. On a refusal it prints the "
                    "reason, a correct: line naming the argument to correct where its own "
                    "input or edit is refused, and a re-run: line, and exits 1; holding the "
                    "lock on its own failure, it prints a clear: line and exits 3. "
                    "write --message FILE [--date YYYY-MM-DD] [--main BRANCH] [--predecessor] "
                    "[--next-free] with one or more of --entry SECTION KEY FILE, --remove-entry "
                    "SECTION KEY, --section SECTION FILE, --note FILE, --brief FILE, --append "
                    "PATH FILE, PATH memory/backlog-candidates.md, "
                    "memory/notes-for-future-features.md or memory/automode-refusals.md, and "
                    "--record FILE, which places FILE as the new memory/<its name>, applied in "
                    "order, is one hub write: it takes the lock, reads that the hub is on the "
                    "main branch and clean, writes the edits, checks in exactly the edited "
                    "paths as one commit, pins it and frees the lock, printing the commit's "
                    "short hash and subject, or on Plastic SCM cs:<n> and the comment's first "
                    "line. A failure after its first write and before a commit restores each "
                    "edited path's bytes, or its absence, unstages the paths, releases the lock "
                    "and refuses; on Plastic SCM, a failed check-in first cm undoes each item "
                    "it added, and the unstage is a cm undo of each path left checked out or "
                    "changed with its base bytes. A restore that fails holds the lock, reason "
                    "restore-failed, and a commit that fails the pin holds it, reason "
                    "pin-mismatch. --predecessor fills each brief's one <predecessor> token "
                    "with this session's id, or removes it where none is set; --next-free "
                    "places a brief whose name is taken as the first free -2, -3, … name, "
                    "chosen under the lock. Each <brief> token in the --note, --entry and "
                    "--message texts is filled with the one brief's placed path, "
                    "memory/handoffs/<name>, and each <<brief>> escape is written as a literal "
                    "<brief>; a literal brief name is left as written. --record refuses, "
                    "before the lock, a name not ending .md, holding a path separator or "
                    "reserved (STATUS.md, a dated YYYY-MM-DD.md, the --append targets), and "
                    "under it an existing target or a name given twice. --brief refuses, "
                    "before the lock, a name not of the form YYYY-MM-DD-<slug>.md, its "
                    "--next-free suffix keeping that form.")
    writer.add_argument("--message", required=True, metavar="FILE",
                        help="the commit message file, passed to git as is, save each "
                             "<brief> token filled as --brief says and each <<brief>> "
                             "written as a literal <brief>")
    writer.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                        help="the date of the note --note appends to (default: today)")
    writer.add_argument("--main", default=None, metavar="BRANCH",
                        help="the branch the hub must be on "
                             "(default: master on git, main on Plastic SCM)")
    writer.add_argument("--predecessor", action="store_true",
                        help="in each --brief text, replace the one <predecessor> token with "
                             "' followed by \"; predecessor <id>\"', <id> "
                             "CLAUDE_CODE_SESSION_ID, or remove it and print "
                             "'predecessor: none' where that is unset or empty; a brief "
                             "holding the token other than once is refused")
    writer.add_argument("--next-free", action="store_true",
                        help="place a --brief whose name is taken under memory/handoffs/ as "
                             "<stem>-2.md, -3, ..., the first free name, chosen under the "
                             "lock; print 'brief: memory/handoffs/<name>' for each brief, "
                             "the path a <brief> token is filled with, with or without "
                             "this flag; a <<brief>> is written as a literal <brief>")
    for kind, text in (
            ("entry", "add or replace the entry for KEY in a ## section of "
                      "memory/STATUS.md with FILE's one line; in Auto-closed, a missing "
                      "heading is first appended at the file's end"),
            ("remove-entry", "remove the entry for KEY from a ## section of memory/STATUS.md; "
                             "in Auto-closed, an absent entry or section changes nothing"),
            ("section", "replace a ## section's body of memory/STATUS.md with FILE's content"),
            ("note", "append FILE's content to memory/<date>.md"),
            ("brief", "place FILE under memory/handoffs/ by its name, which must be dated, "
                      "YYYY-MM-DD-<slug>.md, refused before the lock otherwise; where it is "
                      "the one brief, each <brief> token in the --note, --entry and --message "
                      "texts is filled with its placed path, memory/handoffs/<name>, a text "
                      "with no token placed as is; with two or more, a text holding the token is "
                      "refused; in any write, each <<brief>> is written as a literal "
                      "<brief> and is no token"),
            ("append", "append FILE's content to PATH, memory/backlog-candidates.md, "
                       "memory/notes-for-future-features.md or memory/automode-refusals.md, "
                       "created where absent"),
            ("record", "place FILE at memory/<its name>, a new top-level .md record; refused "
                       "where that file exists or the name is STATUS.md, a dated note "
                       "YYYY-MM-DD.md, backlog-candidates.md, "
                       "notes-for-future-features.md or automode-refusals.md")):
        writer.add_argument(f"--{kind}", dest="edits", action=EditAction,
                            nargs=len(EDITS[kind]), metavar=EDITS[kind],
                            help=text + "; repeatable, applied in command-line order")
    clearer = commands.add_parser(
        "clear", parents=[rooted],
        help="show the lock and the dirty paths; release the lock or check in the dirty "
             "memory/ paths only on their flags",
        description="clear [--release] [--check-in] [--main BRANCH] prints the lock's record, "
                    "or lock: free, and each dirty path, under memory/ or outside it; on "
                    "Plastic SCM, a dirty read that refuses under --release prints dirty: "
                    "unknown (<refusal>) and the run goes on; --release removes the lock file "
                    "whatever its record, and --check-in takes the lock and checks in the "
                    "dirty memory/ paths as one pinned commit naming them, never staging a "
                    "path outside memory/.")
    clearer.add_argument("--release", action="store_true",
                         help="remove the lock file, whatever its record")
    clearer.add_argument("--check-in", action="store_true",
                         help="under the lock, commit the dirty paths under memory/ as one "
                              "pinned commit naming them; after --release when both are given")
    clearer.add_argument("--main", default=None, metavar="BRANCH",
                         help="the branch the hub must be on for --check-in "
                              "(default: master on git, main on Plastic SCM)")
    args = parser.parse_args(argv)
    if args.command == "write" and not args.edits:
        writer.error("at least one edit is required: --entry, --remove-entry, --section, "
                     "--note, --brief, --append or --record")
    if args.command == "sessions-at":
        if (args.wait is None) != (args.since is None):
            lister.error("--wait and --since are given together or not at all")
        if args.wait is not None and args.vacant:
            lister.error("--wait takes no --vacant")

    try:
        if args.command == "status":
            if args.action == "migrate":
                return status_migrate(args.root, args.deferred, args.date)
            if args.action == "line":
                return status_line(args.root, args.section, args.key, args.source)
            return status_set(args.root, args.section, args.source)
        if args.command == "note":
            return note_append(args.root, args.source, args.date)
        if args.command == "commit":
            return commit(args.root, args.message, args.paths)
        if args.command == "predecessor":
            return predecessor(args.root, args.tree, args.session_id)
        if args.command == "lock":
            if args.action == "take":
                return lock_take(args.root)
            return lock_release(args.root)
        if args.command == "write":
            return hub_write(args)
        if args.command == "clear":
            return hub_clear(args)
        if args.wait is not None:
            return sessions_new(args.root, args.tree, args.wait, args.since)
        return sessions_at(args.root, args.tree, args.vacant)
    except Held as held:
        print(f"hub.py {args.command}: {held}", file=sys.stderr)
        if args.command == "write":
            print(rerun_line(args), file=sys.stderr)
        return 3
    except Refusal as refusal:
        if args.command == "lock":
            print(f"hub.py lock {args.action}: {refusal}", file=sys.stderr)
        else:
            print(f"hub.py {args.command}: {refusal}", file=sys.stderr)
        if args.command == "write" and isinstance(refusal, Correctable) and refusal.part:
            print(f"correct: {refusal.part}", file=sys.stderr)
        if args.command == "write" or (args.command == "lock" and args.action == "take"):
            print(rerun_line(args), file=sys.stderr)
        if isinstance(refusal, Stray):
            print(refusal.stray, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
