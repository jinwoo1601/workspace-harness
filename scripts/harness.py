#!/usr/bin/env python3
# =============================================================================
# Purpose:  Base repository command line: the thirteen commands list, validate, scaffold, add, doctor, upgrade, promote, outline, usage_report, budget, bounds, close-class and automode
# Layer:    Scripts
# Owns:     Row (named tuple), Slot (named tuple), BudgetItem (named tuple), Entry (named tuple), AutomodeEntry (named tuple), AutomodeRead (named tuple), AutomodeRefusal (named tuple), PromoteMapping (named tuple), UsageSession (named tuple), FrontmatterError (exception class), Pack (dataclass), Composition (dataclass), ClassificationError (exception class), Project (dataclass), Outcome (dataclass), UpgradeRun (dataclass)
# Depends:  (none)
# =============================================================================

import argparse
import ast
import datetime
import difflib
import hashlib
import io
import json
import ntpath
import os
import posixpath
import re
import stat
import statistics
import subprocess
import sys
import tempfile
import tokenize
from collections import Counter, defaultdict, namedtuple
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath

try:
    import yaml
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError:
    print("harness.py requires PyYAML and jsonschema (pip install pyyaml jsonschema)",
          file=sys.stderr)
    sys.exit(2)


DEFAULT_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_NAMES = ("pack", "agent", "skill", "manifest")

MANIFEST_REL = ".claude/harness.json"

HARNESS_VERSION = "1.1.0"

MANAGED_START = "<!-- harness:managed:start -->"

MANAGED_END = "<!-- harness:managed:end -->"

BINDING_PREFIX = "<!-- harness:binding:"

BINDING_START = "<!-- harness:binding:start {key} {source} -->"

BINDING_END = "<!-- harness:binding:end {key} -->"

BINDING_START_LINE = re.compile(
    r"<!-- harness:binding:start ([a-z][a-z0-9-]*) "
    r"(absent|\.claude/bindings/[a-z][a-z0-9-]*\.md) -->")

BINDING_END_LINE = re.compile(r"<!-- harness:binding:end ([a-z][a-z0-9-]*) -->")

BINDING_KEY_LINE = re.compile(r"^- `([a-z][a-z0-9-]*)` \(")

TOP_HEADING = re.compile(r"#{1,2} ")

ABSENCE_REASONS = ("unfilled", "no-file", "no-section")

STATUS_WORDS = ("DONE", "PARTIAL", "BLOCKED", "NO-BINDING")

FORBIDDEN_SETTINGS_KEYS = ("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "teammateMode",
                           "claudeMdExcludes")

EXCLUDED_TAILS = (".claude/rules/CONSTITUTION.md", "CLAUDE.md")

LIST_KEYS = ("description", "triggers", "requires", "conflicts", "bindings", "presets")

PACK_REFERENCE = re.compile(
    r"(?<![\w./-])(?:core|packs/[a-z][a-z0-9-]*)(?:/[A-Za-z0-9._-]+)+")

HOOK_REFERENCE = re.compile(r"\.claude/references/([a-z][a-z0-9-]*)/([A-Za-z0-9._-]+)")

DRIVE_PREFIX = re.compile(r"[A-Za-z]:/")

PACK_KINDS = ("core", "vc", "workflow", "platform", "docs", "craft", "knowledge", "workspace")

PACK_IDENTIFIER = "^[a-z][a-z0-9-]*$"

PROMOTE_STUB_DESCRIPTION = ("A pack promoted from a project; describe what it is for and "
                            "when a project composes it.")

SKILL_DESCRIPTION_MAX = 250

AGENT_DESCRIPTION_MAX = 200

CLOSED_DEFERRAL = re.compile(r"^- \*\*[A-Z]+\d+[a-z]?\*\* · CLOSED · ")

DOCTOR_RULING = re.compile(r"^- ([A-Z]+) (\S+) (\d+) (\d{4}-\d{2}-\d{2})$")

RULABLE_CODES = ("CHANGELOG", "DEFERRED")

ATX_HEADING = re.compile(r"#{1,6} ")

CODE_FENCE = re.compile(r"\s*(```|~~~)")

BUDGET_SLOTS = (("board", "STATUS budget", "status"),
                ("process-docs", "Architecture-doc body budget", "body"),
                ("process-docs", "Plan-file budget", "plan"),
                ("process-docs", "Brief budget", "brief"))

UNBOUND_VALUES = ("todo", "none")

SLOT_KB = re.compile(r"(?<![\d.,])(\d+) KB\b")

SLOT_SPAN = re.compile(r"`([^`]*)`")

SLOT_CHARACTERS = re.compile(r"(\d+)\b")

LINE_CAP = 200

AGENT_BINDING_SENTENCE = re.compile(
    r"\bif (?:the|either) binding is absent, (?:report that in the first line and "
    r"(?:stop|proceed generically)|proceed generically)", re.IGNORECASE)

HUB_CHECKOUT = re.compile(r"the main checkout is `([^`]+)`")

DRIVE_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")

AUTOMODE_TAG = "Harness:"

AUTOMODE_PLACEHOLDERS = ("root", "trees.hub", "trees.location", "vc.system", "vc.default-branch")

AUTOMODE_PLACEHOLDER = re.compile(r"\{\{([^{}]*)\}\}")

AUTOMODE_PATHS = tuple(re.compile(pattern + r"""[^\s`"'<>|]*""") for pattern in (
    r"(?<![A-Za-z0-9\\])[A-Za-z]:[\\/]+[A-Za-z0-9_]",
    r"(?<![\w.~/\\:}-])/[A-Za-z]/[A-Za-z0-9_]",
    r"(?<![\\:A-Za-z0-9_.$-])\\\\[A-Za-z0-9_.$-]+\\"))

AUTOMODE_SETTINGS = (".claude", "settings.json")

AUTOMODE_ROW_PATH = "~/" + "/".join(AUTOMODE_SETTINGS)

AUTOMODE_DEFAULTS = "$defaults"

AUTOMODE_KEYS = ("allow", "environment")

AUTOMODE_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID")

AUTOMODE_SLOTS = {"trees.hub": ("trees", "Hub"), "trees.location": ("trees", "Location"),
                  "vc.system": ("vc", "System"), "vc.default-branch": ("vc", "Main branch")}

BOUNDS_CLASSES = ("slim", "prose", "trivial")

CLOSE_CLASSES = ("delegated", "audited")

CLOSE_TRIGGERS = (("binding", (".claude/bindings/*.md", "bindings/*.template.md", "claude.md")),
                  ("settings", (".claude/settings*.json", "settings.template.json")),
                  ("fragment", ("automode.template.md",)))

CLOSE_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

READ_SUBCOMMANDS = (("harness", ("list", "validate", "doctor", "outline", "budget", "bounds",
                                 "upgrade --dry-run")),
                    ("hub", ("sessions-at", "predecessor")))

WRITE_SUBCOMMANDS = (("hub", ("write",)),)

BUDGET_NOUNS = {"body": "architecture-doc bodies of open features",
                "plan": "plan files of open features", "brief": "briefs"}

SCRATCH_DIR = ".scratch"

SCRATCH_OLD = ".claude/scratch"

SCRATCH_PROBE = SCRATCH_DIR + "/probe"

SCRATCH_GIT_WAIT = 5

USAGE_WEIGHTS = {"input_tokens": 1.0, "cache_creation_input_tokens": 2.0,
                 "cache_read_input_tokens": 0.1, "output_tokens": 5.0}

Row = namedtuple("Row", "code path message")

Slot = namedtuple("Slot", "budget pattern reason")

BudgetItem = namedtuple("BudgetItem", "state label path detail size budget pattern cause")

Entry = namedtuple("Entry", "rel data error text")

AutomodeEntry = namedtuple("AutomodeEntry", "line section text")

AutomodeRead = namedtuple("AutomodeRead", "scanned base composed refusal")

AutomodeRefusal = namedtuple("AutomodeRefusal", "reason details after_banner")

PromoteMapping = namedtuple("PromoteMapping", "tail member item label name")

UsageSession = namedtuple("UsageSession", "sid calls cost cwd first version turns bash subagents")


class FrontmatterError(Exception):
    pass


@dataclass
class Pack:
    name: str
    kind: str
    directory: Path
    rel: str
    data: dict
    agents: dict
    skills: dict
    files: list
    agent_entries: list
    skill_entries: list
    pack_error: str | None
    texts: dict


def _rel(root, path):
    return Path(path).relative_to(root).as_posix()


def _normalize_dates(value):
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_dates(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_dates(item) for item in value]
    return value


def _frontmatter_closing(lines):
    if lines[0] != "---":
        return None
    return next((index for index in range(1, len(lines)) if lines[index] == "---"), None)


def parse_frontmatter(text):
    lines = text.split("\n")
    if lines[0] != "---":
        raise FrontmatterError("no frontmatter (file does not begin with ---)")
    closing = _frontmatter_closing(lines)
    if closing is None:
        raise FrontmatterError("no closing --- for the frontmatter")
    try:
        data = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"yaml error: {exc}") from exc
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter is not a mapping")
    return _normalize_dates(data)


def read_frontmatter(path):
    return parse_frontmatter(Path(path).read_text(encoding="utf-8"))


def load_schemas(root):
    schemas = {}
    for name in SCHEMA_NAMES:
        rel = f"schemas/{name}.schema.json"
        try:
            schema = json.loads((root / rel).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except OSError as exc:
            raise FrontmatterError(
                rel, f"not a valid JSON Schema: {exc.strerror}") from exc
        except json.JSONDecodeError as exc:
            raise FrontmatterError(rel, f"not a valid JSON Schema: {exc}") from exc
        except SchemaError as exc:
            raise FrontmatterError(
                rel, f"not a valid JSON Schema: {exc.message}") from exc
        schemas[name] = schema
    return schemas


def _string(value, fallback=""):
    return value if isinstance(value, str) else fallback


def _entry(rel, texts, unreadable):
    if rel not in texts:
        return Entry(rel, None, unreadable[rel], "")
    text = texts[rel]
    try:
        return Entry(rel, parse_frontmatter(text), None, text)
    except FrontmatterError as exc:
        return Entry(rel, None, str(exc), text)


def _shipped(rel):
    return "__pycache__" not in rel.split("/") and not rel.endswith(".pyc")


def _is_agent_rel(rel, rel_directory):
    path = PurePosixPath(rel)
    return path.suffix == ".md" and path.parent == PurePosixPath(rel_directory) / "agents"


def _is_skill_rel(rel, rel_directory):
    path = PurePosixPath(rel)
    return (path.name == "SKILL.md"
            and path.parent.parent == PurePosixPath(rel_directory) / "skills")


def discover_packs(root):
    directories = []
    if (root / "core" / "PACK.md").is_file():
        directories.append(root / "core")
    for child in (root / "packs").glob("*"):
        if (child / "PACK.md").is_file():
            directories.append(child)
    packs = []
    for directory in sorted(directories, key=lambda item: item.name):
        rel_directory = _rel(root, directory)
        files = []
        texts = {}
        unreadable = {}
        for path in directory.rglob("*"):
            if path.is_dir():
                continue
            rel = _rel(root, path)
            if not _shipped(rel):
                continue
            if path.is_file():
                files.append(rel)
            if not rel.endswith((".md", ".json")):
                continue
            try:
                texts[rel] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                unreadable[rel] = f"unreadable: {exc}"
        files.sort()
        walked = sorted(set(texts) | set(unreadable))
        pack_entry = _entry(f"{rel_directory}/PACK.md", texts, unreadable)
        data = pack_entry.data if pack_entry.data is not None else {}
        agent_entries = [_entry(rel, texts, unreadable) for rel in walked
                         if _is_agent_rel(rel, rel_directory)]
        skill_entries = [_entry(rel, texts, unreadable) for rel in walked
                         if _is_skill_rel(rel, rel_directory)]
        agents = {}
        for entry in agent_entries:
            if entry.data is not None:
                agents[_string(entry.data.get("name"), PurePosixPath(entry.rel).stem)] = (
                    entry.rel, entry.data)
        skills = {}
        for entry in skill_entries:
            if entry.data is not None:
                skills[_string(entry.data.get("name"), PurePosixPath(entry.rel).parent.name)] = (
                    entry.rel, entry.data)
        packs.append(Pack(
            name=_string(data.get("name"), directory.name),
            kind=_string(data.get("kind")),
            directory=directory,
            rel=rel_directory,
            data=data,
            agents=agents,
            skills=skills,
            files=files,
            agent_entries=agent_entries,
            skill_entries=skill_entries,
            pack_error=pack_entry.error,
            texts=texts,
        ))
    return packs


def load_presets(root):
    presets = []
    for path in sorted((root / "presets").glob("*.json")):
        rel = _rel(root, path)
        try:
            presets.append((rel, json.loads(path.read_text(encoding="utf-8")), None))
        except json.JSONDecodeError as exc:
            presets.append((rel, None, f"invalid JSON: {exc}"))
    return presets


def _preset_problems(data):
    if not isinstance(data, dict):
        return ["preset is not a JSON object"]
    problems = []
    if not isinstance(data.get("description"), str):
        problems.append("preset has no description")
    packs = data.get("packs")
    if not isinstance(packs, list) or not all(isinstance(item, str) for item in packs):
        problems.append("preset packs is not a list of pack names")
    return problems


def _preset_name(rel, data):
    return _string(data.get("name"), Path(rel).stem)


def load_manifest(root):
    try:
        return MANIFEST_REL, json.loads((root / MANIFEST_REL).read_text(encoding="utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        return MANIFEST_REL, None, f"invalid JSON: {exc}"
    except OSError as exc:
        return MANIFEST_REL, None, f"unreadable: {exc}"


def ledger_hash(data):
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(normalized).hexdigest()


def _sorted(rows):
    return sorted(rows, key=lambda row: (row.path, row.message))


def _schema_message(error):
    dotted = ".".join(str(part) for part in error.path)
    return f"{dotted}: {error.message}" if dotted else error.message


def _schema_rows(rel, data, schema):
    errors = sorted(Draft202012Validator(schema).iter_errors(data),
                    key=lambda item: list(item.path))
    return [Row("SCHEMA", rel, _schema_message(error)) for error in errors]


def _entry_rows(entry, schema):
    if entry.data is None:
        return [Row("SCHEMA", entry.rel, entry.error)]
    return _schema_rows(entry.rel, entry.data, schema)


def check_schemas(packs, schemas, presets):
    rows = []
    for pack in packs:
        rel = f"{pack.rel}/PACK.md"
        if pack.pack_error is not None:
            rows.append(Row("SCHEMA", rel, pack.pack_error))
        else:
            rows += _schema_rows(rel, pack.data, schemas["pack"])
        for entry in pack.agent_entries:
            rows += _entry_rows(entry, schemas["agent"])
        for entry in pack.skill_entries:
            rows += _entry_rows(entry, schemas["skill"])
    for rel, data, error in presets:
        if error is not None:
            rows.append(Row("SCHEMA", rel, error))
            continue
        rows += [Row("SCHEMA", rel, problem) for problem in _preset_problems(data)]
    return rows


def check_manifest(data, schemas, rel):
    return _schema_rows(rel, data, schemas["manifest"])


def check_v3(packs):
    rows = []
    provider = {}
    for pack in packs:
        for name in pack.agents:
            provider[name] = pack.name
    for pack in packs:
        requires = pack.data.get("requires") or []
        for skill, (rel, data) in pack.skills.items():
            if data.get("kind") != "orchestration":
                continue
            for agent in data.get("agents") or []:
                if agent in pack.agents:
                    continue
                other = provider.get(agent)
                if other is None:
                    rows.append(Row("V3", rel, (
                        f"orchestration skill {skill} dispatches {agent}, "
                        f"which is not an agent of pack {pack.name}")))
                elif other not in requires:
                    rows.append(Row("V3", rel, (
                        f"orchestration skill {skill} dispatches {agent} of pack {other}, "
                        f"which pack {pack.name} does not require")))
    return _sorted(rows)


def _duplicate_rows(pairs, label):
    rows = []
    first = {}
    for name, rel in pairs:
        if name in first:
            rows.append(Row("V4", rel, f"duplicate {label} name {name} (also in {first[name]})"))
        else:
            first[name] = rel
    return rows


def check_v4(packs):
    rows = []
    agent_pairs = []
    skill_pairs = []
    for pack in packs:
        for entry in pack.agent_entries:
            if entry.data is None:
                continue
            name = entry.data.get("name")
            if isinstance(name, str):
                agent_pairs.append((name, entry.rel))
                stem = PurePosixPath(entry.rel).stem
                if name != stem:
                    rows.append(Row("V4", entry.rel, (
                        f"agent name {name} does not match file basename {stem}")))
        for entry in pack.skill_entries:
            if entry.data is None:
                continue
            name = entry.data.get("name")
            if isinstance(name, str):
                skill_pairs.append((name, entry.rel))
                directory = PurePosixPath(entry.rel).parent.name
                if name != directory:
                    rows.append(Row("V4", entry.rel, (
                        f"skill name {name} does not match directory name {directory}")))
    rows += _duplicate_rows(sorted(agent_pairs, key=lambda pair: pair[1]), "agent")
    rows += _duplicate_rows(sorted(skill_pairs, key=lambda pair: pair[1]), "skill")
    return _sorted(rows)


def _binding_section(text, key):
    heading = re.compile(r"^#{2,}\s*" + re.escape(key) + r"\b", re.IGNORECASE)
    body = None
    for line in text.splitlines():
        if body is not None and re.match(r"^#{1,6}\s", line):
            break
        if body is not None:
            body.append(line)
        elif heading.match(line):
            body = []
    return body


def _skill_binding_keys(data):
    if not isinstance(data, dict) or not isinstance(data.get("bindings"), list):
        return []
    keys = []
    for entry in data["bindings"]:
        if isinstance(entry, str) and entry not in keys:
            keys.append(entry)
    return keys


def _bindings_section_span(lines):
    fence = None
    start = None
    for index, line in enumerate(lines):
        marker = CODE_FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1) == fence:
                fence = None
        elif fence is None:
            if start is None:
                if line.rstrip() == "## Bindings":
                    start = index
            elif TOP_HEADING.match(line):
                return start, index
    return None if start is None else (start, len(lines))


def _reference_binding_keys(text):
    lines = text.split("\n")
    span = _bindings_section_span(lines)
    if span is None:
        return []
    start, end = span
    keys = []
    fence = None
    for line in lines[start + 1:end]:
        if line.startswith(BINDING_PREFIX):
            break
        marker = CODE_FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1) == fence:
                fence = None
        elif fence is None:
            key = BINDING_KEY_LINE.match(line)
            if key and key.group(1) not in keys:
                keys.append(key.group(1))
    return keys


def _binding_body(text, key):
    lines = _binding_section(text, key)
    if lines is None:
        return None
    kept = [index for index, line in enumerate(lines) if line.strip()]
    return "\n".join(lines[kept[0]:kept[-1] + 1]) if kept else ""


def _render_binding_block(key, source, body):
    lines = [BINDING_START.format(key=key, source=source)]
    if body:
        lines.append(body)
    lines.append(BINDING_END.format(key=key))
    return "\n".join(lines)


def _render_absent_block(key, reason, pack=None):
    if reason not in ABSENCE_REASONS or (reason != "unfilled" and pack is None):
        raise ValueError(f"absence reason {reason} with pack {pack}")
    rel = f".claude/bindings/{pack}.md"
    why = {"unfilled": "no composed pack fills it",
           "no-file": f"`{rel}` does not exist",
           "no-section": f"`{rel}` has no `## {key}` section"}[reason]
    return _render_binding_block(key, "absent", (
        f"- Absent: no `{key}` section answers this key in this project — {why}; "
        f"read `{key}` as absent, as the lines above say."))


def _read_binding_blocks(text):
    blocks = {}
    broken = {}
    current = None
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.startswith(BINDING_PREFIX):
            if current is not None:
                current[3].append(line)
            continue
        start = BINDING_START_LINE.fullmatch(line)
        end = BINDING_END_LINE.fullmatch(line)
        if start:
            key = start.group(1)
            if current is not None:
                broken.setdefault(number, f"line {number}: start {key} while {current[0]} is open")
            if key in blocks:
                broken.setdefault(number, f"line {number}: {key} appears twice")
            current = (key, start.group(2), number, [])
        elif end:
            key = end.group(1)
            if current is None:
                broken[number] = f"line {number}: end {key} without a start"
            elif key != current[0]:
                broken[number] = f"line {number}: end {key} while {current[0]} is open"
                current = None
            else:
                if current[0] not in blocks:
                    blocks[key] = (current[1], "\n".join(current[3]))
                current = None
        else:
            broken[number] = f"line {number}: malformed marker"
    if current is not None:
        broken.setdefault(current[2], f"line {current[2]}: {current[0]} is not closed")
    return blocks, [broken[number] for number in sorted(broken)]


def _insert_binding_blocks(text, blocks):
    if not blocks:
        return text
    joined = "\n\n".join(blocks)
    lines = text.split("\n")
    span = _bindings_section_span(lines)
    if span is None:
        head = text
        if text and not text.endswith("\n"):
            head += "\n"
        if text:
            head += "\n"
        return f"{head}## Bindings\n\n{joined}\n"
    start, end = span
    own = lines[start:end]
    while not own[-1].strip():
        own.pop()
    return "\n".join(lines[:start] + own + ["", joined, ""] + lines[end:])


def _bindings_text(root, key, owner, filler=None, fallback=None):
    rel = f".claude/bindings/{(filler or {}).get(key, owner)}.md"
    path = root / rel
    if not path.is_file() and fallback is not None:
        path = fallback / rel
    return path.read_text(encoding="utf-8") if path.is_file() else None


UNREADABLE = object()


def _guarded_bindings_text(root, key, owner, filler=None, fallback=None):
    try:
        return _bindings_text(root, key, owner, filler, fallback)
    except (OSError, UnicodeDecodeError):
        return UNREADABLE


def _composed_kind(destination):
    parts = destination.split("/")
    if parts[:2] != [".claude", "skills"]:
        return None
    if len(parts) == 4 and parts[3] == "SKILL.md":
        return "skill"
    if len(parts) == 5 and parts[3] == "references" and parts[4].endswith(".md"):
        return "reference"
    return None


def _bindings_view(target, rels, texts, composed, fillers, ledger, fallback):
    view = {}
    for rel in sorted(rels):
        name, path, text = rel, target / rel, None
        try:
            if path.is_file():
                text = path.read_bytes().decode("utf-8")
                pack = _bindings_pack(rel, composed)
                if ledger is not None and rel in texts and pack is not None:
                    keys = [key for key in _declared_bindings(pack)
                            if fillers.get(key) == pack.name]
                    text = grow_bindings_file(text, pack, keys)[0]
            elif ledger is None or rel not in ledger:
                text = texts.get(rel)
            if text is None and fallback is not None and (fallback / rel).is_file():
                path = fallback / rel
                name = _recorded_path(path, target) or Path(path).as_posix()
                text = path.read_bytes().decode("utf-8")
        except OSError as exc:
            return {}, f"{name} cannot be read: {exc.strerror}"
        except UnicodeDecodeError:
            return {}, f"{name} cannot be read: not UTF-8 text"
        view[rel] = None if text is None else (name, text)
    return view, None


def _compose_bindings(target, composed, sources, texts, fillers, beneath, fallback, ledger):
    filler_map = {key: value for key, value in beneath.items() if isinstance(value, str)}
    filler_map.update(fillers)
    reading = []
    for destination in sorted(sources):
        kind = _composed_kind(destination)
        if kind is None:
            continue
        source = sources[destination]
        provider = _provider(source, composed)
        pack = next(pack for pack in composed if pack.name == provider)
        text = pack.texts.get(source)
        if text is None:
            return {}, f"{source} cannot be read: discovery could not read it"
        if kind == "skill":
            keys = _skill_binding_keys(next(
                (data for rel, data in pack.skills.values() if rel == source), None))
        else:
            keys = _reference_binding_keys(text)
        if keys:
            reading.append((destination, text, keys))
    rels = {f".claude/bindings/{filler_map[key]}.md"
            for _destination, _text, keys in reading for key in keys if key in filler_map}
    view, refusal = _bindings_view(target, rels, texts, composed, fillers, ledger, fallback)
    if refusal is not None:
        return {}, refusal
    result = {}
    for destination, text, keys in reading:
        blocks = []
        for key in keys:
            if key not in filler_map:
                blocks.append(_render_absent_block(key, "unfilled"))
                continue
            filler = filler_map[key]
            rel = f".claude/bindings/{filler}.md"
            if view[rel] is None:
                blocks.append(_render_absent_block(key, "no-file", filler))
                continue
            name, bindings = view[rel]
            body = _binding_body(bindings, key)
            if body is None:
                blocks.append(_render_absent_block(key, "no-section", filler))
            elif any(line.startswith(BINDING_PREFIX) for line in body.split("\n")):
                return {}, (f"{name} cannot be composed: its ## {key} section holds a line "
                            f"beginning {BINDING_PREFIX}")
            else:
                blocks.append(_render_binding_block(key, rel, body))
        result[destination] = _insert_binding_blocks(text, blocks)
    return result, None


def _drive_path(text):
    if not DRIVE_ABSOLUTE.match(text):
        return None
    path = ntpath.normpath(text).replace("\\", "/").rstrip("/")
    return None if len(path) == 2 else path


def _recorded_path(path, start):
    try:
        return Path(os.path.relpath(path, start)).as_posix()
    except ValueError:
        return _drive_path(str(path))


def _trees_section(root, filler):
    named = (filler or {}).get("trees", "core")
    if not (isinstance(named, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", named)
            and ".." not in named):
        named = "core"
    text = _bindings_text(root, "trees", "core", {"trees": named})
    return _binding_section(text, "trees") if text is not None else None


def _trees_absent(lines):
    if lines is None:
        return True
    stripped = [line.strip() for line in lines]
    content = [line for line in stripped
               if line and not (line.startswith("<!--") and line.endswith("-->"))]
    if not content:
        return True
    if any("TODO" in line for line in lines):
        return True
    return len(content) == 1 and re.match(
        r"none(\s|\u2014|$)", content[0].removeprefix("- ").replace("`", "")) is not None


def _trees_hub(lines):
    line = next((line for line in lines or [] if line.startswith("- Hub:")), None)
    match = HUB_CHECKOUT.search(line) if line else None
    return match.group(1) if match else None


def _trees_location(lines):
    roots = []
    for line in lines or []:
        if not line.strip().startswith("- Location:"):
            continue
        for token in re.findall(r"`([^`]+)`", line):
            if not DRIVE_ABSOLUTE.match(token):
                continue
            kept = []
            for component in re.split(r"[\\/]", token):
                if "<" in component:
                    break
                kept.append(component)
            path = _drive_path("\\".join(kept) + "\\")
            if path is not None and path not in roots:
                roots.append(path)
        break
    return roots


def _trees_hub_path(root, filler):
    filler = filler if isinstance(filler, dict) else {}
    try:
        lines = _trees_section(root, filler)
    except (OSError, UnicodeDecodeError):
        return None
    hub = _trees_hub(lines)
    return Path(hub) if hub is not None else None


def _manifest_base(root, manifest):
    written = manifest["base"]
    base = (root / written).resolve()
    if base.is_dir():
        return base
    hub = _trees_hub_path(root, manifest.get("bindings"))
    if hub is None:
        return base
    candidate = (hub / written).resolve()
    return candidate if candidate.is_dir() else base


def check_v5(root, packs, filler=None, fallback=None, texts=None):
    filler = filler or {}
    rows = []
    texts = {} if texts is None else texts
    for pack in packs:
        rel = f"{pack.rel}/PACK.md"
        for binding in pack.data.get("bindings") or []:
            if not isinstance(binding, dict) or binding.get("required") is not True:
                continue
            key = binding.get("key")
            if not isinstance(key, str):
                continue
            bindings_rel = f".claude/bindings/{filler.get(key, pack.name)}.md"
            if bindings_rel not in texts:
                texts[bindings_rel] = _guarded_bindings_text(root, key, pack.name, filler,
                                                             fallback)
            text = texts[bindings_rel]
            if text is UNREADABLE:
                rows.append(Row("V5", rel, (
                    f"required binding {key} cannot be read: {bindings_rel} "
                    f"is unreadable or not UTF-8 text")))
                continue
            body = _binding_section(text, key) if text is not None else None
            if body is None:
                rows.append(Row("V5", rel, (
                    f"required binding {key} has no section in {bindings_rel}")))
            elif not any(line.strip() for line in body) or any("TODO" in line for line in body):
                rows.append(Row("V5", rel, (
                    f"required binding {key} is still TODO in {bindings_rel}")))
    return _sorted(rows)


def _design_docs_reading(body):
    prefix = "- Design docs:"
    line = next((line for line in body if line.startswith(prefix)), None)
    if line is None:
        return "no Design docs line"
    value = line[len(prefix):].replace("`", "").lstrip()
    match = re.match(r"^(todo|none)\b", value, re.IGNORECASE)
    if match is None:
        return None
    return "Design docs reads TODO" if match.group(1).casefold() == "todo" else (
        "Design docs reads none")


def _path_form_reading(body):
    answers = [line for line in body if line.startswith("- ")]
    if len(answers) == 1 and re.match(r"none(\s|—|$)", answers[0][2:], re.IGNORECASE):
        return None
    prefix = "- Path form:"
    line = next((line for line in body if line.startswith(prefix)), None)
    if line is None:
        return "no Path form line"
    value = line[len(prefix):]
    if re.match(r"^todo\b", value.replace("`", "").lstrip(), re.IGNORECASE):
        return None
    if any("<root>" in span for span in re.findall(r"`([^`]*)`", value)):
        return None
    if "already prints" in value.casefold():
        return None
    return "Path form names no conversion of <root>"


def _provides(pack):
    provides = pack.data.get("provides")
    return provides if isinstance(provides, dict) else {}


def _declares_settings(pack):
    settings = _provides(pack).get("settings")
    return settings if isinstance(settings, str) else None


def _declares_automode(pack):
    automode = _provides(pack).get("automode")
    return automode if isinstance(automode, str) else None


def check_v13(packs):
    rows = []
    for pack in packs:
        rel = f"{pack.rel}/PACK.md"
        for binding in pack.data.get("bindings") or []:
            if not isinstance(binding, dict):
                continue
            file = binding.get("file")
            if not isinstance(file, str):
                continue
            if f"{pack.rel}/{file}" not in pack.files:
                rows.append(Row("V13", rel, f"bindings file {file} does not exist"))
        settings = _declares_settings(pack)
        if settings is not None and f"{pack.rel}/{settings}" not in pack.files:
            rows.append(Row("V13", rel, f"settings file {settings} does not exist"))
        automode = _declares_automode(pack)
        if automode is not None and f"{pack.rel}/{automode}" not in pack.files:
            rows.append(Row("V13", rel, f"automode file {automode} does not exist"))
        for name in _provides(pack).get("references") or []:
            if not isinstance(name, str):
                continue
            if f"{pack.rel}/references/{name}" not in pack.files:
                rows.append(Row("V13", rel, f"reference file {name} does not exist"))
        for check in _provides(pack).get("preflight-checks") or []:
            if not isinstance(check, str):
                continue
            definition = f"references/{check}.md"
            if f"{pack.rel}/{definition}" not in pack.files:
                rows.append(Row("V13", rel, (
                    f"preflight check {check} has no definition file {definition}")))
                continue
            text = pack.texts.get(f"{pack.rel}/{definition}") or ""
            heading = next((line for line in text.splitlines() if line.strip()), "")
            expected = f"# {check} — the check's definition"
            if heading.strip() != expected:
                rows.append(Row("V13", rel, (
                    f"preflight check {check} definition {definition} "
                    f"does not open with {expected}")))
    return _sorted(rows)


def _forbidden_settings(value, dotted):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{dotted}.{key}" if dotted else f"{key}"
            if key in FORBIDDEN_SETTINGS_KEYS:
                found.append((key, path))
            found += _forbidden_settings(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += _forbidden_settings(item, f"{dotted}.{index}" if dotted else f"{index}")
    return found


def check_v14(packs):
    rows = []
    for pack in packs:
        settings = _provides(pack).get("settings")
        if not isinstance(settings, str):
            continue
        rel = f"{pack.rel}/{settings}"
        text = pack.texts.get(rel)
        if text is None:
            continue
        try:
            document = json.loads(text)
        except json.JSONDecodeError as exc:
            rows.append(Row("V14", rel, f"declared settings template is not valid JSON: {exc}"))
            continue
        if not isinstance(document, dict) or not isinstance(document.get("permissions"), dict):
            rows.append(Row("V14", rel, "settings template has no permissions object"))
        for key, dotted in _forbidden_settings(document, ""):
            rows.append(Row("V14", rel, f"settings template sets {key} at {dotted}"))
    return _sorted(rows)


def _automode_lines(text):
    return text.removeprefix("\ufeff").split("\n")


def parse_automode(text):
    entries = []
    problems = []
    section = None
    titled = False
    for number, line in enumerate(_automode_lines(text), start=1):
        if re.match(r"#{1,6}(?:[ \t]|$)", line):
            heading = line.strip()
            if heading in ("## allow", "## environment"):
                section = heading[3:]
            elif section is None and not titled and line.startswith("# "):
                titled = True
            else:
                problems.append((number, f"heading {heading} is not ## allow or ## environment"))
                section = "foreign"
            continue
        if section not in ("allow", "environment") or not line.strip():
            continue
        if line.startswith("- "):
            entries.append(AutomodeEntry(number, section, line[2:]))
        else:
            problems.append((number, f"not an entry line under ## {section}"))
    return entries, problems


def check_v24(packs):
    rows = []
    for pack in packs:
        name = _declares_automode(pack)
        if name is None or not name.endswith(".md"):
            continue
        rel = f"{pack.rel}/{name}"
        if rel not in pack.files:
            continue
        if rel not in pack.texts:
            rows.append(Row("V24", rel, f"automode fragment {name} is not readable"))
            continue
        text = pack.texts[rel]
        entries, problems = parse_automode(text)
        for number, message in problems:
            rows.append(Row("V24", rel, f"line {number}: {message}"))
        for entry in entries:
            if not entry.text.startswith(AUTOMODE_TAG):
                rows.append(Row("V24", rel, (
                    f"line {entry.line}: entry does not open {AUTOMODE_TAG}")))
        for number, line in enumerate(_automode_lines(text), start=1):
            for match in AUTOMODE_PLACEHOLDER.finditer(line):
                if match.group(1) not in AUTOMODE_PLACEHOLDERS:
                    rows.append(Row("V24", rel, (
                        f"line {number}: unknown placeholder {{{{{match.group(1)}}}}}")))
            if "{{" in AUTOMODE_PLACEHOLDER.sub("", line):
                rows.append(Row("V24", rel, f"line {number}: unclosed placeholder {{{{"))
            for pattern in AUTOMODE_PATHS:
                for match in pattern.finditer(line):
                    rows.append(Row("V24", rel, (
                        f"line {number}: literal machine path {match.group(0)}")))
    return _sorted(rows)


def _hook_commands(document):
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        return
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            hook_list = entry.get("hooks")
            if not isinstance(hook_list, list):
                continue
            for hook in hook_list:
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    yield hook["command"]


def check_v17(packs):
    declared = {pack.name: set(_provides(pack).get("references") or []) for pack in packs}
    rows = []
    for pack in packs:
        settings = _declares_settings(pack)
        if settings is None:
            continue
        rel = f"{pack.rel}/{settings}"
        text = pack.texts.get(rel)
        if text is None:
            continue
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(document, dict):
            continue
        seen = set()
        for command in _hook_commands(document):
            for name, file in HOOK_REFERENCE.findall(command):
                if (name, file) in seen:
                    continue
                seen.add((name, file))
                if name not in declared:
                    rows.append(Row("V17", rel, (
                        f"hook command names .claude/references/{name}/{file}, "
                        f"which is not a pack of this base")))
                elif file not in declared[name]:
                    rows.append(Row("V17", rel, (
                        f"hook command names .claude/references/{name}/{file}, "
                        f"which {name} does not declare")))
    return _sorted(rows)


def check_v18(packs):
    rows = []
    for pack in packs:
        for label, entries, cap in (("agent", pack.agent_entries, AGENT_DESCRIPTION_MAX),
                                    ("skill", pack.skill_entries, SKILL_DESCRIPTION_MAX)):
            for entry in entries:
                if entry.data is None:
                    continue
                description = entry.data.get("description")
                if isinstance(description, str) and len(description) > cap:
                    rows.append(Row("V18", entry.rel, (
                        f"{label} description is {len(description)} characters, "
                        f"over the cap of {cap}")))
    return _sorted(rows)


def check_v19(packs):
    rows = []
    for pack in packs:
        for entry in pack.agent_entries:
            if entry.data is None:
                continue
            if entry.data.get("omitClaudeMd") is not True:
                rows.append(Row("V19", entry.rel, "omitClaudeMd is not true"))
    return _sorted(rows)


def check_v20(root, packs, filler=None, fallback=None, texts=None):
    filler = filler or {}
    rows = []
    texts = {} if texts is None else texts
    for pack in packs:
        for binding in pack.data.get("bindings") or []:
            if not isinstance(binding, dict) or binding.get("required") is not True:
                continue
            key = binding.get("key")
            if key != "process-docs":
                continue
            bindings_rel = f".claude/bindings/{filler.get(key, pack.name)}.md"
            if bindings_rel not in texts:
                texts[bindings_rel] = _guarded_bindings_text(root, key, pack.name, filler,
                                                             fallback)
            text = texts[bindings_rel]
            if text is UNREADABLE:
                continue
            body = _binding_section(text, key) if text is not None else None
            if body is None:
                continue
            reading = _design_docs_reading(body)
            if reading is not None:
                rows.append(Row("V20", bindings_rel, (
                    f"process-docs: {reading}; every project needs a home for its design docs")))
    return _sorted(rows)


def check_v21(root, packs, filler=None, fallback=None, texts=None):
    filler = filler or {}
    if filler.get("verification") != "unity":
        return []
    rows = []
    texts = {} if texts is None else texts
    for pack in packs:
        for binding in pack.data.get("bindings") or []:
            if not isinstance(binding, dict) or binding.get("required") is not True:
                continue
            key = binding.get("key")
            if key != "verification":
                continue
            bindings_rel = f".claude/bindings/{filler.get(key, pack.name)}.md"
            if bindings_rel not in texts:
                texts[bindings_rel] = _guarded_bindings_text(root, key, pack.name, filler,
                                                             fallback)
            text = texts[bindings_rel]
            if text is UNREADABLE:
                continue
            body = _binding_section(text, key) if text is not None else None
            if body is None:
                continue
            reading = _path_form_reading(body)
            if reading is not None:
                rows.append(Row("V21", bindings_rel, (
                    f"verification: {reading}; unity's selector, a writer's M1 read and the "
                    f"holder probe put the root they are given in <root>")))
    return _sorted(rows)


def check_v23(root, ledger, filler=None, fallback=None, texts=None):
    filler_map = {key: value for key, value in (filler or {}).items() if isinstance(value, str)}
    texts = {} if texts is None else texts
    rows = []
    unreadable = set()
    for rel in sorted(ledger):
        if not (rel.startswith(".claude/skills/") and rel.endswith(".md")):
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            rows.append(Row("V23", rel, (
                f"cannot be read: {exc.strerror}; its composed bindings are not compared")))
            continue
        except UnicodeDecodeError:
            rows.append(Row("V23", rel, (
                "cannot be read: not UTF-8 text; its composed bindings are not compared")))
            continue
        kind = _composed_kind(rel)
        if kind == "skill":
            try:
                keys = _skill_binding_keys(parse_frontmatter(text))
            except FrontmatterError as exc:
                rows.append(Row("V23", rel, (
                    f"frontmatter cannot be read: {exc.args[0]}; its composed bindings are "
                    f"not compared")))
                continue
        elif kind == "reference":
            keys = _reference_binding_keys(text)
        else:
            keys = []
        blocks, broken = _read_binding_blocks(text)
        fix = ("upgrade" if ledger_hash(text.encode("utf-8")) == ledger[rel]
               else f"upgrade --take-theirs {rel}")
        if broken:
            rows.append(Row("V23", rel, (
                f"composed bindings have broken markers: {', '.join(broken)}; "
                f"run harness.py {fix}")))
            continue
        diffs = []
        for key in keys:
            if key not in filler_map:
                expected = _render_absent_block(key, "unfilled")
            else:
                brel = f".claude/bindings/{filler_map[key]}.md"
                if brel not in texts:
                    texts[brel] = _guarded_bindings_text(root, key, filler_map[key], filler_map,
                                                         fallback)
                bindings = texts[brel]
                if bindings is UNREADABLE:
                    if brel not in unreadable:
                        unreadable.add(brel)
                        rows.append(Row("V23", brel, (
                            "cannot be read: unreadable or not UTF-8 text; composed bindings "
                            "reading it are not compared")))
                    continue
                if bindings is None:
                    expected = _render_absent_block(key, "no-file", filler_map[key])
                else:
                    body = _binding_body(bindings, key)
                    if body is None:
                        expected = _render_absent_block(key, "no-section", filler_map[key])
                    else:
                        expected = _render_binding_block(key, brel, body)
            if key not in blocks:
                diffs.append(f"{key} not composed")
            elif f"\n{expected}\n" not in f"\n{text}\n":
                diffs.append(f"{key} changed")
        diffs += [f"{key} not read" for key in blocks if key not in keys]
        if diffs:
            rows.append(Row("V23", rel, (
                f"composed bindings differ from the live bindings: {', '.join(diffs)}; "
                f"run harness.py {fix}")))
    return _sorted(rows)


def check_v15(parent_filler, filler, rel):
    rows = []
    for key in sorted(set(parent_filler) & set(filler)):
        if parent_filler[key] != "core" and parent_filler[key] != filler[key]:
            rows.append(Row("V15", rel, f"binding key {key} is filled by {filler[key]} here "
                                        f"and by {parent_filler[key]} in the parent"))
    return _sorted(rows)


def ancestor_projects(start):
    return [directory for directory in Path(start).resolve().parents
            if (directory / MANIFEST_REL).is_file()]


def exclusion_patterns(target, ancestors):
    name = Path(target).name
    patterns = set()
    left_out = []
    for ancestor in ancestors:
        if ancestor.name == name:
            left_out.append((ancestor, f"it shares this project's directory name {name}"))
        elif any(char in "*?[]{}()!+@\\" for char in ancestor.name):
            left_out.append((ancestor, f"its name {ancestor.name} holds a glob character"))
        elif not ancestor.name:
            left_out.append((ancestor, "it has no directory name"))
        else:
            patterns.update(f"**/{ancestor.name}/{tail}" for tail in EXCLUDED_TAILS)
    return sorted(patterns), left_out


def exclusion_matches(pattern, path, wide=False):
    if any(char in "[]{}()!+@\\" for char in pattern):
        return False
    if DRIVE_PREFIX.match(pattern):
        pattern = pattern[0].upper() + pattern[1:]
    if DRIVE_PREFIX.match(path):
        path = path[0].upper() + path[1:]
    if wide:
        pattern, path = pattern.casefold(), path.casefold()
    if pattern.startswith("/"):
        parts = pattern[1:].split("/")
    elif DRIVE_PREFIX.match(pattern) or pattern.startswith("**/"):
        parts = pattern.split("/")
    else:
        return False
    segments = path.split("/")[1:] if path.startswith("/") else path.split("/")

    def one(part, segment):
        if not wide and segment.startswith("."):
            return part == segment and "*" not in part and "?" not in part
        expression = "".join(".*" if char == "*" else "." if char == "?" else re.escape(char)
                             for char in re.sub(r"\*+", "*", part))
        return re.fullmatch(expression, segment, re.DOTALL) is not None

    def spans(parts, segments):
        if not parts:
            return not segments
        if parts[0] == "**":
            if spans(parts[1:], segments):
                return True
            return (bool(segments) and (wide or not segments[0].startswith("."))
                    and spans(parts, segments[1:]))
        return bool(segments) and one(parts[0], segments[0]) and spans(parts[1:], segments[1:])

    return spans(parts, segments)


def check_v16(root):
    root = Path(root).resolve()
    if not (root / ".claude/rules/CONSTITUTION.md").is_file():
        return []
    ancestors = ancestor_projects(root)
    if not ancestors:
        return []
    rows = []
    carried = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        path = root / rel
        if not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rows.append(Row("V16", rel, f"not usable for claudeMdExcludes: invalid JSON: {exc}"))
            continue
        if not isinstance(document, dict):
            rows.append(Row("V16", rel, "not usable for claudeMdExcludes: not a JSON object"))
            continue
        patterns = document.get("claudeMdExcludes", [])
        if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
            rows.append(Row("V16", rel, "not usable for claudeMdExcludes: "
                                        "claudeMdExcludes is not a list of strings"))
            continue
        for pattern in patterns:
            if (rel, pattern) not in carried:
                carried.append((rel, pattern))
    _patterns, left_out = exclusion_patterns(root, ancestors)
    left = [ancestor for ancestor, _reason in left_out]
    for ancestor in ancestors:
        for tail in EXCLUDED_TAILS:
            path = ancestor / tail
            if not path.is_file() or any(exclusion_matches(pattern, path.as_posix())
                                         for _rel, pattern in carried):
                continue
            name = Path(os.path.relpath(path, root)).as_posix()
            if ancestor in left:
                ending = ("no folder-name pattern can exclude it, "
                          "add an absolute pattern to .claude/settings.local.json")
            else:
                ending = f"the scaffold's pattern is **/{ancestor.name}/{tail}"
            rows.append(Row("V16", ".claude/settings.json",
                            f"ancestor {name} is not matched by claudeMdExcludes; {ending}"))
    for rel, pattern in carried:
        for tail in EXCLUDED_TAILS:
            if exclusion_matches(pattern, (root / tail).as_posix(), wide=True):
                rows.append(Row("V16", rel, f"claudeMdExcludes pattern {pattern} also matches "
                                            f"this project's own {tail}"))
    return _sorted(rows)


def _roles(pack):
    roles = pack.data.get("roles")
    return roles if isinstance(roles, dict) else {}


def check_v6(packs):
    rows = []
    for pack in packs:
        roles = _roles(pack)
        agents = _provides(pack).get("agents")
        declared = ([name for name in agents if isinstance(name, str)]
                    if isinstance(agents, list) else [])
        for name, (rel, data) in pack.agents.items():
            if name not in roles:
                rows.append(Row("V6", rel, "no allowlist row"))
            else:
                allowed = roles[name] if isinstance(roles[name], list) else []
                tools = [tool.strip() for tool in _string(data.get("tools")).split(",")
                         if tool.strip()]
                outside = [tool for tool in tools if tool not in allowed]
                if outside:
                    rows.append(Row("V6", rel, (
                        f"tools outside the allowlist row: {', '.join(outside)}")))
            model = data.get("model")
            if model == "inherit":
                if name != "architect":
                    rows.append(Row("V6", rel, "model: inherit is permitted only for architect"))
            elif model not in ("opus", "sonnet"):
                rows.append(Row("V6", rel, f"model: {model} must be opus or sonnet"))
        pack_rel = f"{pack.rel}/PACK.md"
        for name in declared:
            if name not in pack.agents and name not in roles:
                rows.append(Row("V6", pack_rel, f"no allowlist row for agent {name}"))
        for name in roles:
            if name not in declared:
                rows.append(Row("V6", pack_rel, (
                    f"stray allowlist row for {name}, which pack {pack.name} does not provide")))
    return _sorted(rows)


def check_v7(packs):
    rows = []
    for pack in packs:
        for _name, (rel, data) in pack.skills.items():
            kind = data.get("kind")
            if kind == "orchestration":
                stops = data.get("stops")
                if not isinstance(stops, list) or not stops:
                    rows.append(Row("V7", rel, "orchestration skill has no non-empty stops:"))
            elif kind == "execution" and data.get("agents"):
                rows.append(Row("V7", rel, "execution skill declares agents:"))
    return _sorted(rows)


def check_v8(packs):
    rows = []
    for pack in packs:
        for rel in sorted(pack.texts):
            seen = []
            for match in PACK_REFERENCE.finditer(pack.texts[rel]):
                text = match.group(0)
                other = "core" if text.startswith("core/") else text.split("/")[1]
                if other != pack.name and text not in seen:
                    seen.append(text)
                    rows.append(Row("V8", rel, (
                        f"path reference crosses into pack {other}: {text}")))
    return _sorted(rows)


def _deprecation(label, name, data):
    date = data.get("removal-date")
    if isinstance(date, str) and date:
        return f"deprecated {label} {name}, removal-date {date}"
    return f"deprecated {label} {name}, no removal-date"


def check_v9(packs):
    rows = []
    for pack in packs:
        if pack.data.get("status") == "deprecated":
            rows.append(Row("V9", f"{pack.rel}/PACK.md",
                            _deprecation("pack", pack.name, pack.data)))
        for name, (rel, data) in pack.agents.items():
            if data.get("status") == "deprecated":
                rows.append(Row("V9", rel, _deprecation("agent", name, data)))
        for name, (rel, data) in pack.skills.items():
            if data.get("status") == "deprecated":
                rows.append(Row("V9", rel, _deprecation("skill", name, data)))
    return _sorted(rows)


def check_v12(packs):
    rows = []
    for pack in packs:
        for entry in pack.agent_entries:
            if entry.data is None:
                continue
            rel = entry.rel
            lines = entry.text.splitlines()
            headings = [index for index, line in enumerate(lines)
                        if line.rstrip() == "## Output"]
            if not headings:
                rows.append(Row("V12", rel, "no ## Output heading"))
                continue
            if len(headings) > 1:
                rows.append(Row("V12", rel,
                                f"{len(headings)} ## Output headings, expected 1"))
                continue
            following = [line for line in lines[headings[0] + 1:] if line.strip()]
            if not following:
                rows.append(Row("V12", rel, "## Output has no following non-blank line"))
                continue
            missing = [word for word in STATUS_WORDS if word not in following[0]]
            if missing:
                rows.append(Row("V12", rel, (
                    f"first line after ## Output is missing the status words: "
                    f"{', '.join(missing)}")))
    return _sorted(rows)


def check_v22(packs):
    rows = []
    for pack in packs:
        for entry in pack.agent_entries:
            if entry.data is None:
                continue
            rel = entry.rel
            lines = entry.text.split("\n")
            body = lines[_frontmatter_closing(lines) + 1:]
            heading = next((index for index, line in enumerate(body) if line.startswith("## ")),
                           None)
            if heading is None or body[heading].rstrip() != "## Binding":
                rows.append(Row("V22", rel, "first ## heading is not ## Binding"))
                continue
            paragraph = []
            for line in body[heading + 1:]:
                if line.strip():
                    paragraph.append(line)
                elif paragraph:
                    break
            if not AGENT_BINDING_SENTENCE.search(" ".join(" ".join(paragraph).split())):
                rows.append(Row("V22", rel, (
                    "## Binding's first paragraph lacks the sentence 'if the binding is absent, "
                    "report that in the first line and stop' (or 'proceed generically')")))
    return _sorted(rows)


def check_v1_v2(packs, presets):
    known = {pack.name: pack for pack in packs}
    usable = [(rel, data) for rel, data, error in presets
              if error is None and not _preset_problems(data)]
    v1_rows = []
    v2_rows = []
    for rel, data in usable:
        named = data["packs"]
        for name in named:
            if name not in known:
                v1_rows.append(Row("V1", rel, (
                    f"preset names pack {name}, which is not in the base")))
        conflicts = []
        for name in named:
            pack = known.get(name)
            if pack is None:
                continue
            for required in pack.data.get("requires") or []:
                if required not in named:
                    v2_rows.append(Row("V2", rel, (
                        f"preset is missing pack {required}, required by {name}")))
            for other in pack.data.get("conflicts") or []:
                pair = tuple(sorted((name, other)))
                if other in named and pair not in conflicts:
                    conflicts.append(pair)
        for first, second in conflicts:
            v2_rows.append(Row("V2", rel, (
                f"preset lists conflicting packs {first} and {second}")))
    return _sorted(v1_rows) + _sorted(v2_rows)


def check_v1_v2_manifest(packs, manifest, rel):
    known = {pack.name: pack for pack in packs}
    named = manifest.get("packs") if isinstance(manifest, dict) else None
    if not isinstance(named, dict):
        return []
    v1_rows = []
    v2_rows = []
    conflicts = []
    for name, version in named.items():
        pack = known.get(name)
        if pack is None:
            v1_rows.append(Row("V1", rel, (
                f"manifest names pack {name}, which is not in the base")))
            continue
        found = pack.data.get("version")
        if version != found:
            v1_rows.append(Row("V1", rel, (
                f"manifest records {name} at {version}, base has {found}")))
        for required in pack.data.get("requires") or []:
            if required not in named:
                v2_rows.append(Row("V2", rel, (
                    f"manifest is missing pack {required}, required by {name}")))
        for other in pack.data.get("conflicts") or []:
            pair = tuple(sorted((name, other)))
            if other in named and pair not in conflicts:
                conflicts.append(pair)
    for first, second in conflicts:
        v2_rows.append(Row("V2", rel, (
            f"manifest lists conflicting packs {first} and {second}")))
    return _sorted(v1_rows) + _sorted(v2_rows)


def _managed_packs(interior):
    listed = [line[len("**Packs:** "):] for line in interior
              if line.startswith("**Packs:** ")]
    if len(listed) != 1:
        return None
    names = listed[0].split(", ")
    if not names or not all(re.fullmatch(PACK_IDENTIFIER, name) for name in names):
        return None
    return names


def check_v10(root, named):
    rel = "CLAUDE.md"
    path = root / rel
    if not path.is_file():
        return [Row("V10", rel, "no CLAUDE.md at the project root")]
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == MANAGED_START]
    ends = [index for index, line in enumerate(lines) if line.strip() == MANAGED_END]
    if not starts:
        return [Row("V10", rel, "managed block start marker missing")]
    if len(starts) > 1:
        return [Row("V10", rel, f"{len(starts)} start markers, expected 1")]
    if not ends:
        return [Row("V10", rel, "managed block end marker missing")]
    if len(ends) > 1:
        return [Row("V10", rel, f"{len(ends)} end markers, expected 1")]
    if ends[0] < starts[0]:
        return [Row("V10", rel, "managed block markers are out of order")]
    interior = lines[starts[0] + 1:ends[0]]
    rows = []
    listed = _managed_packs(interior)
    if listed is None:
        rows.append(Row("V10", rel, "managed block pack list is not parseable"))
    if len([line for line in interior if line.startswith("**Bindings:** ")]) != 1:
        rows.append(Row("V10", rel, "managed block has no bindings pointer"))
    if listed is not None and sorted(listed) != sorted(named):
        rows.append(Row("V10", rel, (
            f"managed block lists packs {', '.join(sorted(listed)) if listed else 'none'}, "
            f"manifest lists {', '.join(sorted(named)) if named else 'none'}")))
    return _sorted(rows)


def check_v11(root, base_root=None, packs=None):
    base_root = root if base_root is None else base_root
    rows = []
    annex_source_rel = "core/references/constitution-annex.md"
    annex_source = base_root / annex_source_rel
    if annex_source.is_file():
        annex_rel = ".claude/references/core/constitution-annex.md"
        annex_copy = root / annex_rel
        if not annex_copy.is_file():
            rows.append(Row("V11", annex_rel, (
                "missing, but core/references/constitution-annex.md exists in the base")))
        else:
            source_text = next((pack.texts[annex_source_rel] for pack in packs or []
                                if annex_source_rel in pack.texts), None)
            if source_text is None:
                source_text = annex_source.read_text(encoding="utf-8")
            source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
            copy_hash = hashlib.sha256(
                annex_copy.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            if copy_hash != source_hash:
                rows.append(Row("V11", annex_rel, (
                    f"sha256 {copy_hash[:12]} differs from core/references/constitution-annex.md "
                    f"{source_hash[:12]}")))
    if not (base_root / "CONSTITUTION.md").is_file():
        return _sorted(rows)
    rel = ".claude/rules/CONSTITUTION.md"
    copy = root / rel
    if not copy.is_file():
        rows.append(Row("V11", rel, "missing, but CONSTITUTION.md exists at the root"))
        return _sorted(rows)
    source_text = (base_root / "CONSTITUTION.md").read_text(encoding="utf-8")
    copy_text = copy.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    copy_hash = hashlib.sha256(copy_text.encode("utf-8")).hexdigest()
    if copy_hash != source_hash:
        rows.append(Row("V11", rel, (
            f"sha256 {copy_hash[:12]} differs from CONSTITUTION.md {source_hash[:12]}")))
    if copy_text.startswith("---\n"):
        rows.append(Row("V11", rel, "begins with a --- frontmatter block"))
    for number, line in enumerate(copy_text.splitlines(), start=1):
        if line.startswith("paths:"):
            rows.append(Row("V11", rel, f"line {number} begins with paths:"))
    return _sorted(rows)


V25_ROOTS = ("core", "packs", "scripts")

V25_SKIPPED = (".md", ".json", ".txt")

V25_SEPARATOR = "# " + "=" * 77

V25_FIELDS = ("# Purpose:", "# Layer:", "# Owns:", "# Depends:")

V25_ENCODING = re.compile(r"#.*?coding[:=][ \t]*[-\w.]+")

V25_ENCODING_LINE = re.compile(
    r"#[ \t]*(?:-\*-[ \t]*)?(?:vim:[ \t]*set[ \t]+)?(?:file)?(?:en)?coding[:=][ \t]*[-\w.]+"
    r"(?:[ \t]*-\*-|[ \t]*:)?[ \t]*")

V25_SHEBANG = re.compile(r"#!(?:\S*/env(?:[ \t]+-\S+)*[ \t]+[^\s-]\S*|\S+)(?:[ \t]+-\S+)*[ \t]*")

V25_DIRECTIVE = re.compile(r"# type: ignore(?:\[[a-z][a-z0-9-]*(?:, *[a-z][a-z0-9-]*)*\])?")


def _v25_exempt(comments):
    exempt = set()
    top = 1
    if comments.get(1, "").startswith("#!"):
        if V25_SHEBANG.fullmatch(comments[1]):
            exempt.add(1)
        top = 2
    if top in comments and V25_ENCODING.match(comments[top]):
        if V25_ENCODING_LINE.fullmatch(comments[top]):
            exempt.add(top)
        top += 1
    block = [comments.get(line) for line in range(top, top + 6)]
    if (None not in block and block[0] == V25_SEPARATOR and block[5] == V25_SEPARATOR
            and all(text.startswith(field) for text, field in zip(block[1:5], V25_FIELDS))):
        exempt.update(range(top, top + 6))
    return exempt


def _v25_python(data):
    tree = ast.parse(data)
    comments = [token for token in tokenize.tokenize(io.BytesIO(data).readline)
                if token.type == tokenize.COMMENT]
    exempt = _v25_exempt({token.start[0]: token.string for token in comments
                          if token.start[1] == 0})
    pairs = [(token.start[0], "body comment") for token in comments
             if token.start[0] not in exempt and not V25_DIRECTIVE.fullmatch(token.string)]
    pairs.extend((node.lineno, "docstring or bare string statement") for node in ast.walk(tree)
                 if isinstance(node, ast.Expr)
                 and (isinstance(node.value, ast.Constant)
                      and isinstance(node.value.value, (str, bytes))
                      or isinstance(node.value, ast.JoinedStr)))
    return pairs


V25_READERS = {".py": _v25_python}


def check_v25(root):
    rows = []
    for name in V25_ROOTS:
        if not (root / name).is_dir():
            continue
        for path in sorted((root / name).rglob("*")):
            if not path.is_file():
                continue
            rel = _rel(root, path)
            if not _shipped(rel):
                continue
            suffix = path.suffix
            if suffix in V25_SKIPPED:
                continue
            reader = V25_READERS.get(suffix)
            if reader is None:
                rows.append(Row("V25", rel, f"no comment reader for {suffix or '(no suffix)'}"))
                continue
            try:
                pairs = reader(path.read_bytes())
            except (OSError, SyntaxError, ValueError, tokenize.TokenError):
                rows.append(Row("V25", rel, "cannot be read as Python"))
                continue
            rows.extend(Row("V25", rel, f"line {line}: {message}") for line, message in pairs)
    return _sorted(rows)


def _banner(manifest):
    fields = manifest if isinstance(manifest, dict) else {}
    base = fields.get("base")
    packs = fields.get("packs")
    return (f"validate: project mode; manifest {MANIFEST_REL}; "
            f"base {base if isinstance(base, str) and base else 'none'}; "
            f"packs {', '.join(sorted(packs)) if isinstance(packs, dict) and packs else 'none'}")


def _base_banner(packs):
    return f"validate: base mode; packs {', '.join(pack.name for pack in packs)}"


def _validate_project(root, manifest, discovered=None):
    banner = _banner(manifest)
    fields = manifest if isinstance(manifest, dict) else {}
    written = fields.get("base")
    if not isinstance(written, str) or not written:
        return [Row("BASE", MANIFEST_REL, "manifest has no base")], [], [banner]
    base = _manifest_base(root, fields)
    if not base.is_dir():
        return [Row("BASE", MANIFEST_REL, f"base {written} is not a directory")], [], [banner]
    packs = (discovered if discovered is not None and base == Path(root).resolve()
             else discover_packs(base))
    if not packs:
        return [Row("BASE", MANIFEST_REL, f"base {written} holds no pack")], [], [banner]
    try:
        schemas = load_schemas(base)
    except FrontmatterError as exc:
        rel, message = exc.args
        return [Row("SCHEMA", rel, message)], [], [banner]
    named = fields.get("packs")
    named = named if isinstance(named, dict) else {}
    filler = fields.get("bindings")
    filler = filler if isinstance(filler, dict) else {}
    pointer = fields.get("parent")
    parent_root = None
    effective, effective_filler = named, filler
    parent_filler = {}
    if isinstance(pointer, str) and pointer:
        parent_root = (root / pointer).resolve()
        _parent_rel, document, error = load_manifest(parent_root)
        parent_named = document.get("packs") if isinstance(document, dict) else None
        if error is not None or not isinstance(parent_named, dict):
            return [Row("BASE", MANIFEST_REL,
                        f"parent {pointer} is not a harness project")], [], [banner]
        parent_filler = document.get("bindings")
        parent_filler = parent_filler if isinstance(parent_filler, dict) else {}
        effective = {**parent_named, **named}
        effective_filler = {**parent_filler, **filler}
    composed = [pack for pack in packs if pack.name in effective]
    failures = []
    failures += check_manifest(manifest, schemas, MANIFEST_REL)
    failures += check_schemas(composed, schemas, [])
    failures += check_v3(composed)
    failures += check_v4(composed)
    binding_texts = {}
    failures += check_v5(root, composed, filler=effective_filler, fallback=parent_root,
                         texts=binding_texts)
    failures += check_v20(root, composed, filler=effective_filler, fallback=parent_root,
                          texts=binding_texts)
    failures += check_v13(composed)
    failures += check_v14(composed)
    failures += check_v24(composed)
    failures += check_v17(composed)
    failures += check_v18(composed)
    failures += check_v19(composed)
    failures += check_v6(composed)
    failures += check_v7(composed)
    failures += check_v8(composed)
    warnings = check_v9(composed)
    warnings += check_v21(root, composed, filler=effective_filler, fallback=parent_root,
                          texts=binding_texts)
    files = fields.get("files")
    warnings += check_v23(root, files if isinstance(files, dict) else {},
                          filler=effective_filler, fallback=parent_root, texts=binding_texts)
    failures += check_v12(composed)
    failures += check_v22(composed)
    failures += check_v1_v2_manifest(packs, dict(manifest, packs=effective), MANIFEST_REL)
    failures += check_v10(root, named)
    failures += check_v15(parent_filler, filler, MANIFEST_REL)
    failures += check_v16(root)
    if parent_root is None or (root / ".claude/rules/CONSTITUTION.md").is_file():
        failures += check_v11(root, base_root=base, packs=packs)
    return failures, warnings, [banner]


def validate(root):
    failures, warnings, _banner_lines = validate_report(root)
    return failures, warnings


def validate_report(root):
    root = Path(root)
    manifest = None
    has_manifest = (root / MANIFEST_REL).is_file()
    if has_manifest:
        rel, manifest, error = load_manifest(root)
        if error is not None:
            return [Row("SCHEMA", rel, error)], [], []
    packs = discover_packs(root)
    if has_manifest and not packs:
        return _validate_project(root, manifest)
    if not packs:
        return [Row("BASE", ".", "no pack found (no core/PACK.md, no packs/*/PACK.md)")], [], []
    try:
        schemas = load_schemas(root)
    except FrontmatterError as exc:
        rel, message = exc.args
        return [Row("SCHEMA", rel, message)], [], []
    presets = load_presets(root)
    failures = []
    failures += check_schemas(packs, schemas, presets)
    failures += check_v3(packs)
    failures += check_v4(packs)
    binding_texts = {}
    failures += check_v5(root, packs, texts=binding_texts)
    failures += check_v20(root, packs, texts=binding_texts)
    failures += check_v13(packs)
    failures += check_v14(packs)
    failures += check_v24(packs)
    failures += check_v17(packs)
    failures += check_v18(packs)
    failures += check_v19(packs)
    failures += check_v6(packs)
    failures += check_v7(packs)
    failures += check_v8(packs)
    warnings = check_v9(packs)
    warnings += check_v21(root, packs, texts=binding_texts)
    failures += check_v12(packs)
    failures += check_v22(packs)
    failures += check_v1_v2(packs, presets)
    failures += check_v11(root, packs=packs)
    failures += check_v25(root)
    if not has_manifest:
        return failures, warnings, []
    project_failures, project_warnings, project_banners = _validate_project(
        root, manifest, discovered=packs)
    return (failures + project_failures,
            warnings + project_warnings,
            [_base_banner(packs)] + project_banners)


def list_packs(root):
    root = Path(root)
    packs = discover_packs(root)
    presets = load_presets(root)
    entries = []
    for rel, data, error in presets:
        if error is not None:
            continue
        names = data.get("packs")
        entries.append((_preset_name(rel, data),
                        data.get("description", ""),
                        names if isinstance(names, list) else []))
    payload = {"packs": [], "presets": []}
    for pack in packs:
        payload["packs"].append({
            "name": pack.name,
            "kind": pack.kind,
            "version": pack.data.get("version", ""),
            "status": pack.data.get("status", ""),
            "description": pack.data.get("description", ""),
            "triggers": pack.data.get("triggers") or [],
            "requires": pack.data.get("requires") or [],
            "conflicts": pack.data.get("conflicts") or [],
            "bindings": [binding.get("key") for binding in pack.data.get("bindings") or []
                         if isinstance(binding, dict)],
            "presets": [name for name, _description, named in entries if pack.name in named],
        })
    for name, description, named in entries:
        payload["presets"].append({"name": name, "description": description, "packs": named})
    return payload


def _value(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def render_list_text(payload):
    blocks = []
    for pack in payload["packs"]:
        lines = ["  ".join([pack["name"], pack["kind"], pack["version"], pack["status"]])]
        lines += [f"  {key}: {_value(pack[key])}" for key in LIST_KEYS]
        blocks.append("\n".join(lines))
    if payload["presets"]:
        lines = ["presets:"]
        for preset in payload["presets"]:
            lines.append(f"  {preset['name']}  {preset['description']}")
            lines.append(f"    packs: {_value(preset['packs'])}")
        blocks.append("\n".join(lines))
    else:
        blocks.append("presets: none")
    return "\n\n".join(blocks)


def render_list_json(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _base_of(packs):
    return packs[0].directory.parents[len(packs[0].rel.split("/")) - 1]


def _preset_packs(packs, name):
    if not packs:
        return None
    for rel, data, error in load_presets(_base_of(packs)):
        if error is not None or _preset_problems(data):
            continue
        if _preset_name(rel, data) == name:
            return list(data["packs"])
    return None


def resolve_composition(packs, requested, preset):
    if not requested and not preset:
        return [], "name at least one pack or a preset"
    listed = []
    if preset:
        listed = _preset_packs(packs, preset)
        if listed is None:
            return [], f"preset {preset} is not in the base"
    names = []
    for name in listed + list(requested) + ["core"]:
        if name not in names:
            names.append(name)
    if "design-track" not in names and any(pack.name == "design-track" for pack in packs):
        names.append("design-track")
    known = {pack.name: pack for pack in packs}
    unknown = sorted(name for name in names if name not in known)
    if unknown:
        return [], f"unknown pack {unknown[0]}"
    composed = [pack for pack in packs if pack.name in names]
    for pack in sorted(composed, key=lambda item: item.name):
        for required in pack.data.get("requires") or []:
            if required not in names:
                return [], (f"pack {pack.name} requires {required}, "
                            f"which the composition does not name")
    conflicts = []
    for pack in composed:
        for other in pack.data.get("conflicts") or []:
            pair = tuple(sorted((pack.name, other)))
            if other in names and pair not in conflicts:
                conflicts.append(pair)
    if conflicts:
        first, second = sorted(conflicts)[0]
        return [], f"packs {first} and {second} conflict"
    return composed, None


def _declared_bindings(pack):
    declared = {}
    for binding in pack.data.get("bindings") or []:
        if not isinstance(binding, dict):
            continue
        key = binding.get("key")
        if isinstance(key, str) and key not in declared:
            declared[key] = _string(binding.get("file"))
    return declared


def resolve_fillers(composed):
    fillers = {}
    for pack in composed:
        for key in _declared_bindings(pack):
            if key in fillers:
                continue
            candidates = sorted(other.name for other in composed
                                if other.name != "core" and key in _declared_bindings(other))
            if len(candidates) > 1:
                return {}, (f"packs {candidates[0]} and {candidates[1]} "
                            f"both fill binding key {key}")
            fillers[key] = candidates[0] if candidates else "core"
    return fillers, None


def render_bindings_file(pack, keys):
    declared = _declared_bindings(pack)
    sections = []
    for key in keys:
        text = pack.texts.get(f"{pack.rel}/{declared.get(key, '')}")
        if text is not None:
            sections.append(text.rstrip("\n"))
    return f"# {pack.name} bindings\n\n" + "\n\n".join(sections) + "\n"


def flatten_plan(composed):
    sources = {}
    leftovers = []
    claimed = {}
    owner = {}
    agents = []
    skills = []
    for pack in composed:
        settings = _declares_settings(pack)
        automode = _declares_automode(pack)
        for rel in pack.files:
            inner = rel[len(pack.rel) + 1:]
            parts = inner.split("/")
            if (inner == "PACK.md" or parts[0] == "bindings"
                    or (automode is not None and inner == automode)):
                continue
            if settings is not None and inner == settings:
                destination = ".claude/settings.json"
            elif _is_agent_rel(rel, pack.rel):
                destination = f".claude/agents/{parts[1]}"
                held = claimed.get(destination)
                if held is not None and held != pack.name:
                    pair = sorted((held, pack.name))
                    agents.append((parts[1], pair[0], pair[1]))
            elif parts[0] == "skills" and len(parts) > 1:
                destination = f".claude/skills/{'/'.join(parts[1:])}"
                held = owner.setdefault(parts[1], pack.name)
                if held != pack.name:
                    pair = sorted((held, pack.name))
                    skills.append((parts[1], pair[0], pair[1]))
            elif parts[0] == "references" and len(parts) > 1:
                destination = f".claude/references/{pack.name}/{'/'.join(parts[1:])}"
            else:
                leftovers.append(rel)
                continue
            claimed.setdefault(destination, pack.name)
            sources[destination] = rel
    if agents:
        name, first, second = sorted(agents)[0]
        return {}, [], f"packs {first} and {second} both provide agent {name}"
    if skills:
        name, first, second = sorted(skills)[0]
        return {}, [], f"packs {first} and {second} both provide skill {name}"
    declaring = sum(1 for pack in composed if _declares_settings(pack) is not None)
    if declaring > 1:
        sources.pop(".claude/settings.json", None)
    if composed and (_base_of(composed) / "CONSTITUTION.md").is_file():
        sources[".claude/rules/CONSTITUTION.md"] = "CONSTITUTION.md"
    return sources, sorted(leftovers), None


def _settings_source(provenance, dotted, value, label):
    provenance.setdefault(dotted, label)
    if isinstance(value, dict):
        for key, item in value.items():
            _settings_source(provenance, f"{dotted}.{key}" if dotted else key, item, label)


def _merge_value(current, incoming, label, dotted, provenance):
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = dict(current)
        for key, item in incoming.items():
            path = f"{dotted}.{key}" if dotted else key
            if key not in merged:
                merged[key] = item
                _settings_source(provenance, path, item, label)
                continue
            value, conflict = _merge_value(merged[key], item, label, path, provenance)
            if conflict is not None:
                return None, conflict
            merged[key] = value
        return merged, None
    if isinstance(current, list) and isinstance(incoming, list):
        merged = list(current)
        for item in incoming:
            if item not in merged:
                merged.append(item)
        return merged, None
    if current == incoming:
        return current, None
    return None, f"{provenance.get(dotted)} and {label} set {dotted} differently"


def merge_settings(items):
    document = {}
    provenance = {}
    for label, incoming in items:
        merged, conflict = _merge_value(document, incoming, label, "", provenance)
        if conflict is not None:
            return None, conflict
        document = merged
    return document, None


def settings_text(composed):
    declaring = [(pack, _declares_settings(pack)) for pack in composed
                 if _declares_settings(pack) is not None]
    if len(declaring) < 2:
        return None, None
    items = []
    for pack, settings in declaring:
        text = pack.texts.get(f"{pack.rel}/{settings}")
        if text is None:
            return None, f"{pack.name}'s settings template is not readable"
        try:
            document = json.loads(text)
        except json.JSONDecodeError:
            return None, f"{pack.name}'s settings template is not valid JSON"
        if not isinstance(document, dict):
            return None, f"{pack.name}'s settings template is not a JSON object"
        items.append((pack.name, document))
    document, conflict = merge_settings(items)
    if conflict is not None:
        return None, f"packs {conflict}"
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n", None


def _script_path(base, script):
    return posixpath.normpath(posixpath.join(base, f"scripts/{script}.py"))


def read_rules(base):
    return [f"Bash(py {_script_path(base, script)} {subcommand}:*)"
            for script, subcommands in READ_SUBCOMMANDS for subcommand in subcommands]


def write_rules(base):
    return [f"Bash(py {_script_path(base, script)} {subcommand}:*)"
            for script, subcommands in WRITE_SUBCOMMANDS for subcommand in subcommands]


def generated_values(target, recorded, fillers):
    directories, unreadable = [], None
    rel = f".claude/bindings/{fillers.get('trees', 'core')}.md"
    try:
        lines = _trees_section(target, fillers)
    except (OSError, UnicodeDecodeError):
        unreadable = {"file": rel, "slots": None}
    else:
        if not _trees_absent(lines):
            raw = _trees_hub(lines)
            hub = _drive_path(raw) if raw is not None else None
            location = _trees_location(lines)
            for path in ([hub] if hub is not None else []) + location:
                if path.casefold() not in [held.casefold() for held in directories]:
                    directories.append(path)
            slots = (["Hub"] if hub is None else []) + (["Location"] if not location else [])
            if slots:
                unreadable = {"file": rel, "slots": slots}
    return {"paths": {script: _script_path(recorded, script)
                      for script, _subcommands in READ_SUBCOMMANDS},
            "rules": read_rules(recorded) + write_rules(recorded),
            "directories": directories,
            "unreadable": unreadable}


def manifest_text(base_rel, preset, packs, files, fillers, parent=None):
    document = {
        "harness": HARNESS_VERSION,
        "base": base_rel,
        "preset": preset,
        "packs": {name: version for name, version in sorted(packs.items())},
        "parent": parent,
        "files": {rel: digest for rel, digest in sorted(files.items())},
        "bindings": {key: fill for key, fill in sorted(fillers.items())},
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def render_managed_block(names):
    return [
        "<!-- Managed by harness.py — scaffold, add, and upgrade rewrite everything "
        "between these markers. -->",
        "",
        f"**Packs:** {', '.join(sorted(names)) if names else 'none'}",
        "",
        "**Bindings:** `.claude/bindings/<pack>.md` — one file per pack, "
        "one `##` section per key.",
        "",
    ]


def render_skeleton(title, names):
    lines = [f"# {title}", "", MANAGED_START]
    lines += render_managed_block(names)
    lines += [MANAGED_END, "", "## Project notes", "",
              "TODO (what a session needs to know about this project that the bindings do not say)"]
    return "\n".join(lines) + "\n"


def rewrite_managed_block(text, interior):
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.strip() == MANAGED_START]
    ends = [index for index, line in enumerate(lines) if line.strip() == MANAGED_END]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return None
    return "\n".join(lines[:starts[0] + 1] + list(interior) + lines[ends[0]:])


def _required_keys(composed):
    keys = set()
    for pack in composed:
        for binding in pack.data.get("bindings") or []:
            if not isinstance(binding, dict) or binding.get("required") is not True:
                continue
            if isinstance(binding.get("key"), str):
                keys.add(binding["key"])
    return keys


def render_summary(target, versions, preset, notes, to_fill, count, verb="scaffold",
                   skipped=None):
    filling = ", ".join(f".claude/bindings/{pack}.md ({', '.join(keys)})"
                        for pack, keys in to_fill)
    lines = [f"{verb}: {target}",
             "  packs: " + ", ".join(f"{name} {version}"
                                     for name, version in sorted(versions.items())),
             f"  preset: {preset if preset else 'none'}"]
    lines += [f"  {note}" for note in notes]
    lines += [f"  bindings to fill: {filling if filling else 'none'}",
              f"  next: the binding interview, then harness.py validate --root {target}",
              f"{verb}: wrote {count} files into {target}"
              + ("" if skipped is None else f", skipped {skipped}")]
    return "\n".join(lines)


def _target_is_empty(target):
    if not target.exists():
        return True
    if not target.is_dir():
        return False
    entries = [path.name for path in target.iterdir()]
    return not entries or entries == [".git"]


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _write_whole(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def _reparse(path):
    try:
        attributes = os.lstat(path).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _crossing(root, rel):
    parts = PurePosixPath(rel).parts
    for depth in range(1, len(parts)):
        component = "/".join(parts[:depth])
        path = root / component
        if os.path.islink(path):
            return component, "symlink"
        if _reparse(path):
            return component, "junction"
        if not os.path.lexists(path):
            break
        if not path.is_dir():
            return component, "not a directory"
    return None


def adopt_plan(target, sources, texts, interior):
    if os.path.lexists(target / MANIFEST_REL):
        return [], None, f"target {target} is already a project; grow it with add"
    skipped = []
    for dest in sorted((set(sources) | set(texts)) - {"CLAUDE.md"}):
        crossing = _crossing(target, dest)
        if crossing is not None:
            component, kind = crossing
            return [], None, (f"{dest} crosses {component}, which is not a directory"
                              if kind == "not a directory"
                              else f"{dest} crosses the {kind} {component}")
        if os.path.lexists(target / dest):
            skipped.append(dest)
    path = target / "CLAUDE.md"
    if not os.path.lexists(path):
        return skipped, None, None
    if path.is_symlink() or not path.is_file():
        return [], None, "CLAUDE.md is not a regular file"
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    starts = sum(1 for line in lines if line.strip() == MANAGED_START)
    ends = sum(1 for line in lines if line.strip() == MANAGED_END)
    if starts == 0 and ends == 0:
        heading = next((index for index, line in enumerate(lines)
                        if re.match(r"^#{1,6}(\s|$)", line)), None)
        if heading is None:
            merged = [MANAGED_START, *interior, MANAGED_END, ""] + lines
            outcome = "inserted at the top (no heading)"
        else:
            merged = (lines[:heading + 1] + ["", MANAGED_START, *interior, MANAGED_END]
                      + lines[heading + 1:])
            outcome = "inserted after the first heading"
        return skipped, ("\n".join(merged), outcome), None
    rewritten = rewrite_managed_block(text, interior)
    if rewritten is None:
        return [], None, "CLAUDE.md has a broken managed-block marker pair"
    return skipped, (rewritten, "rewritten between the existing markers"), None


def write_project(target, base, plan):
    sources, texts, given = plan["sources"], plan["texts"], plan.get("data", {})
    ledger = {}
    for destination in sorted(set(sources) | set(texts) | set(given)):
        try:
            data = (given[destination] if destination in given
                    else texts[destination].encode("utf-8") if destination in texts
                    else (base / sources[destination]).read_bytes())
            _write(target / destination, data)
        except OSError as exc:
            return len(ledger), f"{exc.strerror} writing {destination}"
        ledger[destination] = ledger_hash(data)
    path = target / MANIFEST_REL
    try:
        rendered = plan["manifest"](ledger).encode("utf-8")
        if path.is_file() and ledger_hash(path.read_bytes()) == ledger_hash(rendered):
            return len(ledger), None
        _write(path, rendered)
    except OSError as exc:
        return len(ledger), f"{exc.strerror} writing {MANIFEST_REL}"
    return len(ledger) + 1, None


def _refuse(reason, verb="scaffold"):
    print(f"{verb}: refused — {reason}", file=sys.stderr)
    return 1


def _fail(failure, target, verb="scaffold"):
    print(f"{verb}: failed — {failure}; the partial target {target} was left in place",
          file=sys.stderr)
    return 1


def _rewrite_block(target):
    _rel, manifest, error = load_manifest(target)
    named = manifest.get("packs") if isinstance(manifest, dict) else None
    path = target / "CLAUDE.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else None
    rewritten = None
    if error is None and isinstance(named, dict) and text is not None:
        rewritten = rewrite_managed_block(text, render_managed_block(sorted(named)))
    if rewritten is None:
        return _refuse(f"--rewrite-managed-block needs an existing project at {target}")
    try:
        _write(path, rewritten.encode("utf-8"))
    except OSError as exc:
        return _fail(f"{exc.strerror} writing CLAUDE.md", target)
    print("\n".join([f"scaffold: {target}",
                     f"  managed block: {', '.join(sorted(named))}",
                     "  no other file was written",
                     f"scaffold: wrote 1 files into {target}"]))
    return 0


def _in_parent_scope(target, parent):
    return parent in target.parents and not (target / ".git").exists()


@dataclass
class Composition:
    refusal: str | None = None
    composed: list | None = None
    parent_rel: str | None = None
    sources: dict | None = None
    texts: dict | None = None
    fillers: dict | None = None
    versions: dict | None = None
    base_rel: str | None = None
    notes: list | None = None
    to_fill: list | None = None
    names: list | None = None
    required: set | None = None
    ancestors: list | None = None
    exclusions: list | None = None
    left_out: list | None = None
    generated: dict | None = None


def _parent_note(parent_rel, delta):
    return f"parent: {parent_rel} — " + (
        "delta child; the parent's constitution copy and settings file are not copied"
        if delta else "union child; its own discovery root")


def _parent_bindings(parent, document=None):
    if document is None:
        _parent_rel, document, _error = load_manifest(parent)
    if isinstance(document, dict) and isinstance(document.get("bindings"), dict):
        return document["bindings"], parent
    return {}, parent


def compose_plan(target, base, discovered, requested, preset, parent=None, delta=None,
                 written=None, parent_root=None, ledger=None):
    composed, refusal = resolve_composition(discovered, requested, preset)
    if refusal is not None:
        return Composition(refusal=refusal)
    parent_rel = None
    given, delta = delta, bool(delta)
    effective = None
    beneath, fallback = {}, None
    if parent is not None:
        _parent_rel, document, error = load_manifest(parent)
        parent_named = document.get("packs") if isinstance(document, dict) else None
        if error is not None or not isinstance(parent_named, dict):
            return Composition(refusal=f"--parent needs an existing project at {parent}")
        beneath, fallback = _parent_bindings(parent, document)
        composed, refusal = resolve_composition(
            discovered, [pack.name for pack in composed] + sorted(parent_named), None)
        if refusal is not None:
            return Composition(refusal=refusal)
        delta = _in_parent_scope(target, parent) if given is None else delta
        if delta:
            effective = composed
            composed = [pack for pack in composed if pack.name not in parent_named]
            if not composed:
                return Composition(
                    refusal=f"every named pack is already composed by the parent at {parent}")
        parent_rel = _recorded_path(parent, target)
        if parent_rel is None:
            return Composition(refusal=f"parent {parent} cannot be recorded from {target}: "
                                       "no relative path and no drive-absolute form")
    elif parent_root is not None:
        beneath, fallback = _parent_bindings(parent_root)
    if effective is not None:
        _union, _union_leftovers, refusal = flatten_plan(effective)
        if refusal is not None:
            return Composition(refusal=refusal)
    sources, leftovers, refusal = flatten_plan(composed)
    if refusal is not None:
        return Composition(refusal=refusal)
    if effective is not None:
        _union_fillers, refusal = resolve_fillers(effective)
        if refusal is not None:
            return Composition(refusal=refusal)
    fillers, refusal = resolve_fillers(composed)
    if refusal is not None:
        return Composition(refusal=refusal)
    merged, refusal = settings_text(composed)
    if refusal is not None:
        return Composition(refusal=refusal)
    ancestors, exclusions, left_out = [], [], []
    if not delta and ".claude/rules/CONSTITUTION.md" in sources:
        ancestors = ancestor_projects(target)
        if ancestors:
            exclusions, left_out = exclusion_patterns(target, ancestors)
    recorded = written if written is not None else _recorded_path(base, target)
    if recorded is None:
        return Composition(refusal=f"base {base} cannot be recorded from {target}: "
                                   "no relative path and no drive-absolute form")
    generated = None
    if not delta and (merged is not None or ".claude/settings.json" in sources or exclusions):
        if merged is not None:
            document = json.loads(merged)
        elif ".claude/settings.json" in sources:
            pack = next(pack for pack in composed if _declares_settings(pack) is not None)
            text = pack.texts.get(f"{pack.rel}/{_declares_settings(pack)}")
            if text is None:
                return Composition(refusal=f"{pack.name}'s settings template is not readable")
            try:
                document = json.loads(text)
            except json.JSONDecodeError:
                return Composition(refusal=f"{pack.name}'s settings template is not valid JSON")
            if not isinstance(document, dict):
                return Composition(refusal=f"{pack.name}'s settings template is not a JSON object")
        else:
            document = {}
        generated = generated_values(target, recorded, fillers)
        items = [(".claude/settings.json", document)]
        if exclusions:
            items.append(("ancestor exclusions", {"claudeMdExcludes": exclusions}))
        fragment = {"allow": generated["rules"]}
        if generated["directories"]:
            fragment["additionalDirectories"] = generated["directories"]
        items.append(("generated values", {"permissions": fragment}))
        folded, conflict = merge_settings(items)
        if conflict is not None:
            return Composition(refusal=conflict)
        merged = json.dumps(folded, indent=2, ensure_ascii=False) + "\n"
        sources.pop(".claude/settings.json", None)

    notes = []
    if leftovers:
        notes.append(f"not copied: {', '.join(leftovers)}")
    if delta:
        sources.pop(".claude/rules/CONSTITUTION.md", None)
        sources.pop(".claude/settings.json", None)
        merged = None
    else:
        if merged is None and ".claude/settings.json" not in sources:
            notes.append("no settings template: no composed pack declares one")
        if ".claude/rules/CONSTITUTION.md" not in sources:
            notes.append("no constitution: the base holds no CONSTITUTION.md")
    if parent_rel is not None:
        notes.append(_parent_note(parent_rel, delta))
    required = _required_keys(effective if effective is not None else composed)
    texts = {}
    if merged is not None:
        texts[".claude/settings.json"] = merged
    to_fill = []
    for pack in composed:
        keys = [key for key in _declared_bindings(pack) if fillers.get(key) == pack.name]
        if not keys:
            continue
        texts[f".claude/bindings/{pack.name}.md"] = render_bindings_file(pack, keys)
        filling = [key for key in keys if key in required]
        if filling:
            to_fill.append((pack.name, filling))
    blocks, refusal = _compose_bindings(target, composed, sources, texts, fillers, beneath,
                                        fallback, None if written is None else (ledger or {}))
    if refusal is not None:
        return Composition(refusal=refusal)
    for destination, text in blocks.items():
        sources.pop(destination)
        texts[destination] = text
    names = [pack.name for pack in composed]
    texts["CLAUDE.md"] = render_skeleton(target.name, names)
    versions = {pack.name: _string(pack.data.get("version")) for pack in composed}
    return Composition(composed=composed, parent_rel=parent_rel,
                       sources=sources, texts=texts, fillers=fillers,
                       versions=versions, base_rel=recorded, notes=notes, to_fill=to_fill,
                       names=names, required=required, ancestors=ancestors,
                       exclusions=exclusions, left_out=left_out, generated=generated)


def exclusion_notes(target, ancestors, exclusions, left_out, has_settings_text):
    left = [ancestor for ancestor, _reason in left_out]
    notes = []
    if exclusions and has_settings_text:
        projects = ", ".join(Path(os.path.relpath(ancestor, target)).as_posix()
                             for ancestor in ancestors if ancestor not in left)
        notes.append(f"ancestor exclusions: {', '.join(exclusions)} "
                     f"(ancestor projects: {projects})")
    elif exclusions:
        notes.append("ancestor exclusions not written: .claude/settings.json already present; "
                     f"add {', '.join(exclusions)} to its claudeMdExcludes")
    notes += [f"ancestor exclusion not written for "
              f"{Path(os.path.relpath(ancestor, target)).as_posix()}: {reason}; "
              "add an absolute pattern to .claude/settings.local.json"
              for ancestor, reason in left_out]
    return notes


def generated_notes(generated, has_settings_text):
    if generated is None:
        return []
    dirs = ", ".join(generated["directories"])
    if has_settings_text:
        notes = [("generated values: "
                  + (f"additionalDirectories {dirs}; " if dirs else "")
                  + "allow rules for " + ", ".join(
                      f"py {generated['paths'][script]} "
                      f"({', '.join(subcommands + dict(WRITE_SUBCOMMANDS).get(script, ()))})"
                      for script, subcommands in READ_SUBCOMMANDS))]
    else:
        notes = ["generated values not written: .claude/settings.json already present; "
                 f"add {', '.join(generated['rules'])} to its permissions"
                 + (f", and additionalDirectories {dirs}" if dirs else "")]
    unreadable = generated["unreadable"]
    if unreadable is not None and unreadable["slots"] is not None:
        notes.append(f"generated values: trees {', '.join(unreadable['slots'])} unreadable in "
                     f"{unreadable['file']}; "
                     + ("generated the rest" if has_settings_text
                        else "left out of the values to add"))
    elif unreadable is not None:
        notes.append(f"generated values: {unreadable['file']} unreadable; "
                     + ("generated the rules alone" if has_settings_text
                        else "the values to add are the rules alone"))
    return notes


def scaffold(target, base, packs, preset=None, rewrite=False, parent=None, adopt=False):
    if rewrite:
        return _rewrite_block(target)
    verb = "adopt" if adopt else "scaffold"
    if base in target.parents:
        return _refuse(f"target {target} is inside the base at {base}", verb)
    requested = [name.strip() for name in packs.split(",") if name.strip()]
    discovered = discover_packs(base)
    plan = compose_plan(target, base, discovered, requested, preset, parent=parent)
    if plan.refusal is not None:
        return _refuse(plan.refusal, verb)
    if not adopt and not _target_is_empty(target):
        return _refuse(f"target {target} is not empty", verb)
    sources, texts = plan.sources, plan.texts
    notes, to_fill = plan.notes, plan.to_fill
    skipped = None
    if adopt:
        skips, claude_md, refusal = adopt_plan(target, sources, texts,
                                               render_managed_block(plan.names))
        if refusal is not None:
            return _refuse(refusal, verb)
    for path in sorted(set(sources) | set(texts)):
        ok, reason = contained(target, path)
        if not ok:
            return _refuse(f"{path} is not a contained path: {reason}", verb)
    if adopt:
        for destination in skips:
            sources.pop(destination, None)
            texts.pop(destination, None)
        to_fill = [(pack, keys) for pack, keys in to_fill
                   if f".claude/bindings/{pack}.md" not in skips]
        notes += [f"skipped (already present): {destination}" for destination in skips]
        skipped = len(skips)
        if claude_md is not None:
            text, outcome = claude_md
            texts.pop("CLAUDE.md")
            notes.append(f"CLAUDE.md: managed block {outcome}")
            try:
                _write(target / "CLAUDE.md", text.encode("utf-8"))
            except OSError as exc:
                return _fail(f"{exc.strerror} writing CLAUDE.md", target, verb)
    notes += exclusion_notes(target, plan.ancestors, plan.exclusions, plan.left_out,
                             ".claude/settings.json" in texts)
    notes += generated_notes(plan.generated, ".claude/settings.json" in texts)
    count, failure = write_project(target, base, {
        "sources": sources,
        "texts": texts,
        "manifest": lambda files: manifest_text(plan.base_rel, preset, plan.versions, files,
                                                plan.fillers, parent=plan.parent_rel),
    })
    if failure is not None:
        return _fail(failure, target, verb)
    print(render_summary(target, plan.versions, preset, notes, to_fill, count, verb, skipped))
    return 0


def resolve_addition(packs, named, name, inherited=None):
    if name in named:
        return None, [], f"pack {name} is already composed"
    known = {pack.name: pack for pack in packs}
    if name not in known:
        return None, [], f"unknown pack {name}"
    pack = known[name]
    declared = pack.data.get("conflicts") or []
    effective = {**(inherited or {}), **named}
    existing = [other for other in packs if other.name in effective]
    for other in existing:
        if other.name in declared or name in (other.data.get("conflicts") or []):
            return None, [], f"pack {name} conflicts with {other.name}"
    for required in pack.data.get("requires") or []:
        if required not in effective:
            return None, [], (f"pack {name} requires {required}, "
                              f"which the project does not compose")
    return pack, existing, None


def _provider(source, packs):
    for pack in packs:
        if source.startswith(f"{pack.rel}/"):
            return pack.name
    return None


def _collision(name, held, destination):
    parts = destination.split("/")
    if parts[1] == "skills":
        return f"{name} and {held} both provide skill {parts[2]}"
    return f"{name} and {held} both provide agent {parts[2]}"


def _adoptable(path, source, planned=None):
    try:
        digest = ledger_hash(path.read_bytes())
        expected = planned if planned is not None else source.read_bytes()
        return digest if digest == ledger_hash(expected) else None
    except OSError:
        return None


def _delta_child(root, pointer, ledger):
    rel = ".claude/settings.json"
    return bool(pointer) and not ((root / rel).exists() or rel in ledger)


def _merged_settings(root, name, template):
    rel = ".claude/settings.json"
    try:
        project = json.loads((root / rel).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{rel} is not usable: invalid JSON: {exc}"
    except OSError as exc:
        return None, f"{rel} is not usable: unreadable: {exc}"
    if not isinstance(project, dict):
        return None, f"{rel} is not usable: not a JSON object"
    try:
        fragment = json.loads(template)
    except json.JSONDecodeError:
        return None, f"{name}'s settings template is not valid JSON"
    if not isinstance(fragment, dict):
        return None, f"{name}'s settings template is not a JSON object"
    document, conflict = merge_settings([(rel, project), (name, fragment)])
    if conflict is not None:
        return None, conflict
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n", None


def grow_bindings_file(existing, pack, keys):
    if existing.strip() == "":
        return render_bindings_file(pack, keys), keys
    declared = _declared_bindings(pack)
    sections = []
    appended = []
    for key in keys:
        if _binding_section(existing, key) is not None:
            continue
        text = pack.texts.get(f"{pack.rel}/{declared.get(key, '')}")
        if text is None:
            continue
        sections.append(text.rstrip("\n"))
        appended.append(key)
    if not appended:
        return existing, []
    return existing.rstrip("\n") + "\n\n" + "\n\n".join(sections) + "\n", appended


def add(name, root):
    if not (root / MANIFEST_REL).is_file():
        return _refuse(f"add needs an existing project at {root}", verb="add")
    _rel, manifest, error = load_manifest(root)
    if error is None and not isinstance(manifest, dict):
        error = "the document is not an object"
    if error is not None:
        return _refuse(f"the manifest at {root} is not usable: {error}", verb="add")
    written = manifest.get("base")
    if not isinstance(written, str) or not written:
        return _refuse("manifest has no base", verb="add")
    base = _manifest_base(root, manifest)
    if not base.is_dir():
        return _refuse(f"base {written} is not a directory", verb="add")
    packs = discover_packs(base)
    if not packs:
        return _refuse(f"base {written} holds no pack", verb="add")
    named = manifest.get("packs")
    named = named if isinstance(named, dict) else {}
    ledger = manifest.get("files")
    ledger = ledger if isinstance(ledger, dict) else {}
    pointer = _string(manifest.get("parent"))
    delta_child = _delta_child(root, pointer, ledger)
    inherited = {}
    if delta_child:
        _parent_rel, document, error = load_manifest((root / pointer).resolve())
        parent_named = document.get("packs") if isinstance(document, dict) else None
        if error is None and isinstance(parent_named, dict):
            inherited = parent_named
    pack, existing, refusal = resolve_addition(packs, named, name, inherited)
    if refusal is not None:
        return _refuse(refusal, verb="add")
    held, _held, refusal = flatten_plan([other for other in existing if other.name != name])
    if refusal is not None:
        return _refuse(refusal, verb="add")
    delta, leftovers, refusal = flatten_plan([pack])
    if refusal is not None:
        return _refuse(refusal, verb="add")
    held.pop(".claude/rules/CONSTITUTION.md", None)
    delta.pop(".claude/rules/CONSTITUTION.md", None)
    dropped_settings = delta_child and ".claude/settings.json" in delta
    if delta_child:
        held.pop(".claude/settings.json", None)
        delta.pop(".claude/settings.json", None)
    provided = any(_declares_settings(other) is not None for other in existing)
    merged = None
    if ".claude/settings.json" in delta and provided:
        delta.pop(".claude/settings.json", None)
        settings = _declares_settings(pack)
        template = pack.texts.get(f"{pack.rel}/{settings}")
        if template is None:
            return _refuse(f"{name}'s settings template is not readable", verb="add")
        rel = ".claude/settings.json"
        try:
            clean = rel in ledger and ledger_hash((root / rel).read_bytes()) == ledger[rel]
        except OSError:
            clean = False
        if clean:
            plan = compose_plan(root, base, packs, sorted(set(named) | {name}), None,
                                parent=None, delta=False, written=written)
            if plan.refusal is not None:
                return _refuse(plan.refusal, verb="add")
            merged = plan.texts[rel]
        else:
            merged, refusal = _merged_settings(root, name, template)
            if refusal is not None:
                return _refuse(refusal, verb="add")
    filler = manifest.get("bindings")
    filler = dict(filler) if isinstance(filler, dict) else {}
    keys = []
    repointed = []
    for key in _declared_bindings(pack):
        holder = filler.get(key)
        if holder is not None and holder != "core":
            return _refuse(f"binding key {key} is filled by {holder}; re-pointing one pack's "
                           f"key to another is not this verb's call", verb="add")
        if holder == "core":
            repointed.append(f"re-pointed: {key} from core to {name}; the ## {key} section "
                             f"of .claude/bindings/core.md is now inert")
        filler[key] = name
        keys.append(key)
    bindings_rel = f".claude/bindings/{name}.md"
    path = root / bindings_rel
    try:
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError as exc:
        return _refuse(f"{bindings_rel} cannot be read: {exc.strerror}", verb="add")
    except UnicodeDecodeError:
        return _refuse(f"{bindings_rel} cannot be read: not UTF-8 text", verb="add")
    text, appended = grow_bindings_file(current, pack, keys)
    beneath, fallback = {}, None
    if pointer:
        beneath, fallback = _parent_bindings((root / pointer).resolve())
    own = {rel: digest for rel, digest in ledger.items() if rel != bindings_rel}
    blocks, refusal = _compose_bindings(root, [pack], delta, {bindings_rel: text}, filler,
                                        beneath, fallback, own)
    if refusal is not None:
        return _refuse(refusal, verb="add")
    adopted = {}
    for destination in sorted(delta):
        if destination in held:
            return _refuse(_collision(name, _provider(held[destination], existing), destination),
                           verb="add")
        overwrite = (f"{name} would overwrite {destination}, "
                     f"which no pack in this project provides")
        if destination in ledger:
            return _refuse(overwrite, verb="add")
        if not (root / destination).exists():
            continue
        planned = blocks[destination].encode("utf-8") if destination in blocks else None
        digest = _adoptable(root / destination, base / delta[destination], planned)
        if digest is None:
            return _refuse(overwrite, verb="add")
        adopted[destination] = digest
        delta.pop(destination)
    version = _string(pack.data.get("version"))
    notes = [f"added: {name} {version}"]
    notes += [f"adopted: {destination}" for destination in sorted(adopted)]
    notes += repointed
    notes += [f"already sectioned: {key} in {bindings_rel}, left as it is" for key in keys
              if key not in appended and _binding_section(current, key) is not None]
    if leftovers:
        notes.append(f"not copied: {', '.join(leftovers)}")
    if dropped_settings:
        notes.append(f"parent: {pointer} — delta child; {name}'s settings file is not copied, "
                     f"the parent's copy governs by walk-up")
    if merged is not None:
        notes.append(f"merged: {name}'s settings fragment into .claude/settings.json")
    texts = {bindings_rel: text} if appended else {}
    for destination in sorted(blocks):
        if destination in delta:
            delta.pop(destination)
            texts[destination] = blocks[destination]
    if merged is not None:
        texts[".claude/settings.json"] = merged
    grown = dict(named)
    grown[name] = version
    claude = root / "CLAUDE.md"
    skeleton = claude.read_text(encoding="utf-8") if claude.is_file() else None
    rewritten = (rewrite_managed_block(skeleton, render_managed_block(sorted(grown)))
                 if skeleton is not None else None)
    if rewritten is None:
        return _refuse(f"CLAUDE.md at {root} has no usable managed block", verb="add")
    texts["CLAUDE.md"] = rewritten

    required = _required_keys(existing + [pack])
    filling = [key for key in keys if key in required]
    preset, parent = manifest.get("preset"), manifest.get("parent")
    for path in sorted(set(delta) | set(texts)):
        ok, reason = contained(root, path)
        if not ok:
            return _refuse(f"{path} is not a contained path: {reason}", verb="add")
    count, failure = write_project(root, base, {
        "sources": delta,
        "texts": texts,
        "manifest": lambda files: manifest_text(written, preset, grown,
                                                {**ledger, **adopted, **files},
                                                filler, parent=parent),
    })
    if failure is not None:
        return _fail(failure, root, verb="add")
    print(render_summary(root, grown, preset, notes, [(name, filling)] if filling else [],
                         count, verb="add"))
    return 0


class ClassificationError(Exception):
    pass


def glob_match(pattern, rel):
    parts = pattern.split("/")
    segments = rel.split("/")

    def one(part, segment):
        expression = "".join(".*" if char == "*" else "." if char == "?" else re.escape(char)
                             for char in re.sub(r"\*+", "*", part))
        return re.fullmatch(expression, segment, re.DOTALL) is not None

    def spans(parts, segments):
        if not parts:
            return not segments
        if parts[0] == "**":
            return spans(parts[1:], segments) or (bool(segments) and spans(parts, segments[1:]))
        return bool(segments) and one(parts[0], segments[0]) and spans(parts[1:], segments[1:])

    return spans(parts, segments)


def _rendered(value):
    return value if isinstance(value, str) else json.dumps(value)


def load_classification(schemas):
    manifest = schemas["manifest"]
    declaration = manifest.get("x-classification") if isinstance(manifest, dict) else None
    entries = declaration.get("classes") if isinstance(declaration, dict) else None
    if not isinstance(entries, list) or not entries:
        return None, "no x-classification in schemas/manifest.schema.json"
    classes = []
    for entry in entries:
        name = entry.get("class") if isinstance(entry, dict) else None
        if name not in ("LOCKED", "PRESERVE", "managed", "ledgered"):
            return None, f"unknown class {_rendered(name)}"
        region = entry.get("region")
        if name == "managed" and region != "managed block":
            return None, f"unknown region {_rendered(region)} for class managed"
        patterns = entry.get("patterns")
        if not isinstance(patterns, list):
            return None, f"pattern {_rendered(patterns)} uses unsupported glob syntax"
        for pattern in patterns:
            if not isinstance(pattern, str) or any(char in pattern for char in "[]{}"):
                return None, f"pattern {_rendered(pattern)} uses unsupported glob syntax"
        classes.append((name, list(patterns)))
    return classes, None


def classify(rel, classes):
    for name, patterns in classes:
        if any(glob_match(pattern, rel) for pattern in patterns):
            return name
    raise ClassificationError(f"{rel} matches no class")


@dataclass
class Project:
    root: Path
    manifest: dict
    written: str
    base: Path
    packs: list
    schemas: dict
    classes: list
    classified: dict
    ledger: dict
    named: dict
    parent_root: Path | None
    effective: dict
    effective_filler: dict
    composed: list
    delta: bool


def load_project(root):
    if not (root / MANIFEST_REL).is_file():
        return None, [Row("MANIFEST", MANIFEST_REL, "no manifest at the project root")]
    _rel, manifest, error = load_manifest(root)
    if error is not None:
        return None, [Row("SCHEMA", MANIFEST_REL, error)]
    if not isinstance(manifest, dict):
        return None, [Row("SCHEMA", MANIFEST_REL, "the document is not an object")]
    written = manifest.get("base")
    if not isinstance(written, str) or not written:
        return None, [Row("BASE", MANIFEST_REL, "manifest has no base")]
    base = _manifest_base(root, manifest)
    if not base.is_dir():
        return None, [Row("BASE", MANIFEST_REL, f"base {written} is not a directory")]
    packs = discover_packs(base)
    if not packs:
        return None, [Row("BASE", MANIFEST_REL, f"base {written} holds no pack")]
    try:
        schemas = load_schemas(base)
    except FrontmatterError as exc:
        rel, message = exc.args
        return None, [Row("SCHEMA", rel, message)]
    rows = check_manifest(manifest, schemas, MANIFEST_REL)
    if rows:
        return None, rows
    named = manifest["packs"]
    known = {pack.name for pack in packs}
    missing = sorted(name for name in named if name not in known)
    if missing:
        return None, [Row("BASE", MANIFEST_REL,
                          f"manifest names pack {missing[0]}, which is not in the base")]
    filler = manifest["bindings"]
    pointer = _string(manifest.get("parent"))
    parent_root = None
    effective, effective_filler = named, filler
    if pointer:
        parent_root = (root / pointer).resolve()
        _parent_rel, document, error = load_manifest(parent_root)
        parent_named = document.get("packs") if isinstance(document, dict) else None
        if error is not None or not isinstance(parent_named, dict):
            return None, [Row("BASE", MANIFEST_REL, f"parent {pointer} is not a harness project")]
        parent_filler = document.get("bindings")
        parent_filler = parent_filler if isinstance(parent_filler, dict) else {}
        effective = {**parent_named, **named}
        effective_filler = {**parent_filler, **filler}
    classes, reason = load_classification(schemas)
    if reason is not None:
        return None, [Row("BASE", "schemas/manifest.schema.json",
                          f"x-classification is not usable: {reason}")]
    ledger = manifest["files"]
    try:
        classified = {path: classify(path, classes) for path in sorted(ledger)}
    except ClassificationError as exc:
        return None, [Row("BASE", "schemas/manifest.schema.json",
                          f"x-classification is not usable: {exc.args[0]}")]
    return Project(
        root=root,
        manifest=manifest,
        written=written,
        base=base,
        packs=packs,
        schemas=schemas,
        classes=classes,
        classified=classified,
        ledger=ledger,
        named=named,
        parent_root=parent_root,
        effective=effective,
        effective_filler=effective_filler,
        composed=[pack for pack in packs if pack.name in effective],
        delta=_delta_child(root, pointer, ledger),
    ), None


def ledger_drift(root, ledger, classified):
    rows = []
    for rel, recorded in ledger.items():
        if classified[rel] != "ledgered":
            continue
        path = root / rel
        if not path.is_file():
            rows.append(Row("DRIFT", rel, "locally deleted: in the ledger, absent on disk"))
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            rows.append(Row("DRIFT", rel, f"unreadable: {exc.strerror}"))
            continue
        if ledger_hash(data) != recorded:
            rows.append(Row("DRIFT", rel, "locally modified: its hash differs from the ledger's"))
    return _sorted(rows)


def local_items(root, ledger):
    rows = set()
    agents = root / ".claude/agents"
    if agents.is_dir():
        for path in agents.rglob("*"):
            rel = _rel(root, path)
            if path.is_file() and rel not in ledger:
                rows.add(Row("LOCAL", rel, "unledgered agent file"))
    skills = root / ".claude/skills"
    if skills.is_dir():
        for path in skills.rglob("*"):
            rel = _rel(root, path)
            if not path.is_file() or rel in ledger:
                continue
            parts = rel.split("/")
            if len(parts) == 3:
                rows.add(Row("LOCAL", rel, "unledgered file"))
            elif any(key.startswith(f".claude/skills/{parts[2]}/") for key in ledger):
                rows.add(Row("LOCAL", rel, "unledgered file in a ledgered skill"))
            else:
                rows.add(Row("LOCAL", f".claude/skills/{parts[2]}", "unledgered skill directory"))
    return _sorted(rows)


def behind(named, packs):
    versions = {pack.name: pack.data.get("version") for pack in packs}
    rows = []
    for name, recorded in named.items():
        if name in versions and recorded != versions[name]:
            rows.append(Row("BEHIND", MANIFEST_REL,
                            f"manifest records {name} at {recorded}, base has {versions[name]}"))
    return _sorted(rows)


def user_shadows(ledger):
    home = Path.home()
    skills = set()
    agents = set()
    for key in ledger:
        parts = key.split("/")
        if len(parts) >= 4 and parts[:2] == [".claude", "skills"]:
            skills.add(parts[2])
        elif len(parts) == 3 and parts[:2] == [".claude", "agents"] and parts[2].endswith(".md"):
            agents.add(PurePosixPath(key).stem)
    rows = []
    for name in skills:
        if os.path.lexists(home / ".claude/skills" / name):
            rows.append(Row("SHADOW", f".claude/skills/{name}",
                            f"shadowed by the user-level ~/.claude/skills/{name}"))
        for first in {path.parents[2].name
                      for path in (home / ".claude/skills").glob(f"*/*/{name}/SKILL.md")}:
            rows.append(Row("SHADOW", f".claude/skills/{name}",
                            f"a user-level synced skill of the same name sits at "
                            f"~/.claude/skills/{first}/*/{name}; which copy loads is unverified"))
    for name in agents:
        if os.path.lexists(home / ".claude/agents" / f"{name}.md"):
            rows.append(Row("SHADOW", f".claude/agents/{name}.md",
                            f"shadowed by the user-level ~/.claude/agents/{name}.md"))
    return _sorted(rows)


def over_cap_lines(root, code, rel, cap):
    path = root / rel
    if not path.is_file():
        return 0, []
    lines = path.read_text(encoding="utf-8").split("\n")
    over = [(number, len(line))
            for number, line in enumerate(lines, start=1) if len(line) > cap]
    if len(over) > 5:
        number, length = max(over, key=lambda item: item[1])
        return len(over), [Row(code, rel,
                               f"{len(over)} lines over the {cap}-character cap "
                               f"(longest: line {number}, {length} characters)")]
    return len(over), [Row(code, rel,
                           f"line {number}: {length} characters, over the {cap}-character cap")
                       for number, length in over]


def status_lines(root, project):
    value, reason = _slot_value(root, project, "board", "core", "STATUS line cap")
    figure = SLOT_CHARACTERS.match(value) if reason is None else None
    if reason == "the value reads TODO":
        cap = LINE_CAP
    elif figure is not None:
        cap = int(figure.group(1))
    else:
        return []
    return over_cap_lines(root, "STATUS", "memory/STATUS.md", cap)[1]


def changelog_lines(root):
    return over_cap_lines(root, "CHANGELOG", "CHANGELOG.md", LINE_CAP)


def closed_deferrals(root):
    path = root / "memory/STATUS.md"
    if not path.is_file():
        return 0, []
    count = 0
    inside = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            inside = line.rstrip() == "## Deferred"
        elif inside and CLOSED_DEFERRAL.match(line):
            count += 1
    if not count:
        return 0, []
    return count, [Row("DEFERRED", "memory/STATUS.md",
                       f"{count} closed deferrals still in STATUS")]


def doctor_rulings(root):
    path = root / "memory/doctor-rulings.md"
    if not path.is_file():
        return {}
    rulings = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        match = DOCTOR_RULING.match(line.rstrip())
        if match and match.group(1) in RULABLE_CODES:
            code, rel, count, _date = match.groups()
            rulings[(code, rel)] = max(int(count), rulings.get((code, rel), -1))
    return rulings


def _slot_value(root, project, key, owner, label, missing=None, subject="the value"):
    try:
        text = _bindings_text(root, key, owner, project.effective_filler, project.parent_root)
    except (OSError, UnicodeDecodeError):
        return None, "cannot read the bindings file"
    if text is None and missing is not None:
        return None, missing
    body = _binding_section(text, key) if text is not None else None
    if body is None:
        return None, f"no {key} section"
    prefix = f"- {label}:"
    line = next((line for line in body if line.startswith(prefix)), None)
    if line is None:
        return None, f"no {label} line"
    value = line[len(prefix):].strip()
    for word, shown in zip(UNBOUND_VALUES, ("TODO", "none")):
        if value.casefold().startswith(word):
            return None, f"{subject} reads {shown}"
    return value, None


def budget_slot(root, project, key, label, kind):
    value, reason = _slot_value(root, project, key, "core", label)
    if reason is not None:
        return Slot(None, None, reason)
    figure = SLOT_KB.search(value)
    if figure is None:
        return Slot(None, None, "no KB figure")
    budget = int(figure.group(1)) * 1024
    if kind == "status":
        return Slot(budget, None, None)
    span = SLOT_SPAN.search(value)
    if span is None:
        return Slot(None, None, "no path pattern")
    pattern = span.group(1).strip()
    for word, shown in zip(UNBOUND_VALUES, ("TODO", "none")):
        if pattern.casefold() == word:
            return Slot(None, None, f"the path pattern reads {shown}")
    if not pattern:
        return Slot(None, None, "the path pattern is empty")
    if (PurePath(pattern).is_absolute() or PurePath(pattern).drive
            or pattern.startswith(("/", "\\"))):
        return Slot(None, None, "the path pattern is not relative to the root")
    if ".." in re.split(r"[/\\]", pattern):
        return Slot(None, None, "the path pattern leaves the root")
    return Slot(budget, pattern, None)


def body_bytes(path):
    kept = 0
    fence = None
    inside = False
    done = False
    for raw in Path(path).read_bytes().splitlines(keepends=True):
        line = raw.decode("utf-8", errors="replace")
        marker = CODE_FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1) == fence:
                fence = None
        elif fence is None and ATX_HEADING.match(line):
            if inside and line.startswith("## "):
                inside = False
                done = True
            elif not inside and not done and line.rstrip() == "## Build plan":
                inside = True
        if not inside:
            kept += len(raw)
    return kept


def budget_items(root, project, memory_root, feature, kinds):
    items = []
    for key, label, kind in BUDGET_SLOTS:
        if kind not in kinds:
            continue
        slot = budget_slot(root, project, key, label, kind)
        if slot.reason is not None:
            items.append(BudgetItem("NOT CHECKED", label, ".claude/bindings", slot.reason,
                                    None, None, None, "unfilled"))
            continue
        if kind == "status":
            path = memory_root / "memory/STATUS.md"
            if not path.is_file():
                items.append(BudgetItem("NOT CHECKED", label, "memory/STATUS.md",
                                        "no memory/STATUS.md", None, slot.budget, None,
                                        "unreadable"))
                continue
            pattern = None
            files = [("memory/STATUS.md", path)]
        else:
            pattern = slot.pattern.replace("<feature>", feature)
            try:
                files = sorted(((_rel(root, path), path) for path in root.glob(pattern)
                                if path.is_file()), key=lambda entry: entry[0])
            except (ValueError, NotImplementedError, OSError) as error:
                items.append(BudgetItem("NOT CHECKED", label, pattern,
                                        f"the path pattern is not a valid glob: {error}", None,
                                        slot.budget, pattern, "unreadable"))
                continue
            if not files:
                items.append(BudgetItem("NOT CHECKED", label, pattern,
                                        f"no file matches {pattern}", None, slot.budget, pattern,
                                        "no match"))
                continue
        for rel, path in files:
            try:
                size = body_bytes(path) if kind == "body" else path.stat().st_size
            except OSError as error:
                items.append(BudgetItem("NOT CHECKED", label, rel, f"cannot read: {error}",
                                        None, slot.budget, pattern, "unreadable"))
                continue
            items.append(BudgetItem("FAIL" if size > slot.budget else "PASS", label, rel,
                                    f"{size} of {slot.budget} bytes", size, slot.budget,
                                    pattern, None))
    return items


def item_feature(path, pattern):
    parts = re.split(r"[/\\]", pattern)
    index = next((index for index, part in enumerate(parts) if part == "<feature>"), None)
    if index is None or any(part in ("", ".") or "**" in part for part in parts[:index]):
        return None
    components = path.split("/")
    return components[index] if index < len(components) else None


def feature_open(root, body_pattern, feature):
    try:
        data = read_frontmatter(root / body_pattern.replace("<feature>", feature))
    except (OSError, ValueError, FrontmatterError):
        return True
    status = data.get("status")
    return status is None or status == "draft"


def budget_rows(root, project):
    items = budget_items(root, project, root, "*", ("status", "body", "plan", "brief"))
    rows = []
    memo = {}
    body_slot = next(slot for slot in BUDGET_SLOTS if slot[2] == "body")
    for key, label, kind in BUDGET_SLOTS:
        over = [item for item in items if item.label == label and item.state == "FAIL"]
        if over and kind in ("body", "plan"):
            pattern = budget_slot(root, project, key, label, kind).pattern
            body = budget_slot(root, project, *body_slot).pattern
            kept = []
            for item in over:
                feature = item_feature(item.path, pattern)
                if feature is not None and body is not None and feature not in memo:
                    memo[feature] = feature_open(root, body, feature)
                if feature is None or body is None or memo[feature]:
                    kept.append(item)
            over = kept
        if not over:
            continue
        if kind == "status":
            item = over[0]
            rows.append(Row("BUDGET", item.path,
                            f"{item.size} bytes, over the {item.budget // 1024} KB budget "
                            f"({item.budget} bytes)"))
            continue
        largest = max(over, key=lambda item: item.size)
        rows.append(Row("BUDGET", largest.pattern,
                        f"{len(over)} {BUDGET_NOUNS[kind]} over the "
                        f"{largest.budget // 1024} KB budget; "
                        f"largest {largest.path}, {largest.size} bytes"))
    unfilled = [item.label for item in items if item.cause == "unfilled"]
    if unfilled:
        rows.append(Row("BUDGET", ".claude/bindings",
                        f"{len(unfilled)} budget slots unfilled: {', '.join(unfilled)}"))
    return rows


def slot_rows(root, project):
    fillers = {pack.name: pack for pack in project.composed}
    missing = {}
    for pack in project.composed:
        for binding in pack.data.get("bindings") or []:
            if not isinstance(binding, dict) or binding.get("required") is not True:
                continue
            key = binding.get("key")
            if not isinstance(key, str):
                continue
            filling = fillers.get(project.effective_filler.get(key, pack.name))
            declared = _declared_bindings(filling).get(key) if filling is not None else None
            template = filling.texts.get(f"{filling.rel}/{declared}") if declared else None
            if template is None:
                continue
            try:
                text = _bindings_text(root, key, pack.name, project.effective_filler,
                                      project.parent_root)
            except (OSError, UnicodeDecodeError):
                continue
            body = _binding_section(text, key) if text is not None else None
            if body is None:
                continue
            labels = _missing_slots(body, template)
            if labels:
                missing.setdefault(f".claude/bindings/{filling.name}.md", []).append(
                    (key, labels))
    rows = []
    for rel, fields in missing.items():
        rows.append(Row("SLOTS", rel, "; ".join(f"{key}: {', '.join(labels)}"
                                                for key, labels in fields)
                        + ": template slots this filled section has no line for"))
    return rows


def _vc_system(root, project):
    value, reason = _slot_value(root, project, "vc", "core", "System", missing="no bindings file",
                                subject="the System value")
    if value == "":
        return None, "the System value is empty"
    return value, reason


def _vc_main_branch(root, project):
    value, reason = _slot_value(root, project, "vc", "core", "Main branch",
                                missing="no bindings file", subject="the Main branch value")
    if reason is not None:
        return None, reason
    span = SLOT_SPAN.search(value)
    if span is None or not span.group(1).strip():
        return None, "no branch name in backticks"
    return span.group(1).strip(), None


def _vc_automode_named(root, project):
    value, reason = _slot_value(root, project, "vc", "core", "Auto-mode entries")
    if reason is not None:
        if reason in ("no vc section", "no Auto-mode entries line", "the value reads TODO"):
            return True, None
        return None, reason
    if value == "":
        return None, "the value is empty"
    if value.casefold().startswith("excluded"):
        return False, None
    if value.casefold().startswith("included"):
        return True, None
    return None, f"the value {value} is neither included nor excluded"


def _scratch_ignored(root):
    try:
        done = subprocess.run(["git", "check-ignore", "-q", "--", SCRATCH_PROBE], cwd=root,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              errors="replace", timeout=SCRATCH_GIT_WAIT)
    except FileNotFoundError:
        return None, "git is not on PATH"
    except OSError:
        return None, "git could not be started"
    except subprocess.TimeoutExpired:
        return None, f"no answer within {SCRATCH_GIT_WAIT} seconds"
    if done.returncode in (0, 1):
        return done.returncode == 0, None
    line = next((line.strip() for line in done.stderr.splitlines() if line.strip()), None)
    if line is None:
        return None, f"git check-ignore exited {done.returncode}"
    return None, line.encode("ascii", "replace").decode("ascii")


def scratch_rows(root, project):
    rows = []
    value, reason = _vc_system(root, project)
    if value is None:
        rows.append(Row("SCRATCH", SCRATCH_DIR,
                        f"NOT CHECKED - the vc binding names no system ({reason})"))
    elif not re.match(r"git\b", value, re.IGNORECASE):
        rows.append(Row("SCRATCH", SCRATCH_DIR, "NOT CHECKED - the check covers git only; "
                                                "the vc binding names another system"))
    else:
        ignored, reason = _scratch_ignored(root)
        if ignored is None:
            rows.append(Row("SCRATCH", SCRATCH_DIR,
                            f"NOT CHECKED - git could not answer ({reason})"))
        elif not ignored:
            rows.append(Row("SCRATCH", SCRATCH_DIR,
                            f"not ignored by git - add {SCRATCH_DIR}/ to the ignore file"))
    if (root / SCRATCH_OLD).is_dir():
        rows.append(Row("SCRATCH", SCRATCH_OLD, "an old scratch folder is present; nothing "
                                                "files or reads there - the human removes it"))
    slot = budget_slot(root, project, "process-docs", "Brief budget", "brief")
    if (slot.reason is None
            and slot.pattern.replace("\\", "/").split("/")[:2] == SCRATCH_OLD.split("/")):
        rows.append(Row("SCRATCH", ".claude/bindings",
                        f"Brief budget pattern {slot.pattern} is under the old scratch folder, "
                        f"where no brief is filed - point it at {SCRATCH_DIR}/"))
    return rows


def _doctor_banner(manifest):
    fields = manifest if isinstance(manifest, dict) else {}
    base = fields.get("base")
    packs = fields.get("packs")
    return (f"doctor: project; manifest {MANIFEST_REL}; "
            f"base {base if isinstance(base, str) and base else 'none'}; "
            f"packs {', '.join(sorted(packs)) if isinstance(packs, dict) and packs else 'none'}")


def doctor_report(root, memo=None):
    _rel, document, _error = load_manifest(root)
    banner = _doctor_banner(document)
    project, rows = load_project(root)
    if project is None:
        return rows, [], banner
    binding_texts = {}
    failures = check_v5(root, project.composed, filler=project.effective_filler,
                        fallback=project.parent_root, texts=binding_texts)
    failures += check_v20(root, project.composed, filler=project.effective_filler,
                          fallback=project.parent_root, texts=binding_texts)
    if project.parent_root is None or (root / ".claude/rules/CONSTITUTION.md").is_file():
        failures += check_v11(root, base_root=project.base)
    warnings = []
    warnings += ledger_drift(root, project.ledger, project.classified)
    warnings += local_items(root, project.ledger)
    warnings += behind(project.named, project.packs)
    warnings += check_v9(project.composed)
    warnings += check_v21(root, project.composed, filler=project.effective_filler,
                          fallback=project.parent_root, texts=binding_texts)
    warnings += check_v23(root, project.ledger, filler=project.effective_filler,
                          fallback=project.parent_root, texts=binding_texts)
    warnings += user_shadows(project.ledger)
    warnings += automode_rows(project, memo)
    warnings += status_lines(root, project)
    rulings = doctor_rulings(root)
    for code, rel, (count, rows) in (("CHANGELOG", "CHANGELOG.md", changelog_lines(root)),
                                     ("DEFERRED", "memory/STATUS.md", closed_deferrals(root))):
        if rulings.get((code, rel), -1) < count:
            warnings += rows
    warnings += budget_rows(root, project)
    warnings += slot_rows(root, project)
    warnings += scratch_rows(root, project)
    return failures, warnings, banner


def doctor(root):
    failures, warnings, banner = doctor_report(root)
    return print_report([banner], failures, warnings, "doctor")


def workspace_projects(root):
    projects = [root] if (root / MANIFEST_REL).is_file() else []
    projects += sorted((child for child in root.iterdir()
                        if child.is_dir() and (child / MANIFEST_REL).is_file()),
                       key=lambda child: child.name)
    return projects


def doctor_all(root):
    projects = workspace_projects(root)
    if not projects:
        return _refuse(f"no project at {root} or in its immediate children", verb="doctor --all")
    holders = {}
    failed = False
    memo = {}
    for project in projects:
        rel = "." if project == root else project.name
        print(f"project: {rel}")
        failures, warnings, banner = doctor_report(project, memo)
        if print_report([banner], failures, warnings, "doctor"):
            failed = True
        for row in warnings:
            if row.code == "LOCAL":
                holders.setdefault(row.path[len(".claude/"):], []).append(rel)
    print("local items across projects:")
    for item in sorted(holders):
        line = f"  {item}  {', '.join(holders[item])}"
        if len(holders[item]) >= 2:
            line += f"  (in {len(holders[item])} projects)"
        print(line)
    if not holders:
        print("  none")
    print("doctor --all: FAIL" if failed else "doctor --all: PASS")
    return 1 if failed else 0


def _automode_body(project, key):
    try:
        text = _bindings_text(project.root, key, "core", project.effective_filler,
                              project.parent_root)
    except (OSError, UnicodeDecodeError):
        return None
    return _binding_section(text, key) if text is not None else None


def _automode_values(root, project):
    values = {"root": str(root)}
    unbound = {}
    trees = _automode_body(project, "trees")
    if trees is not None and _answers_none(trees):
        values["trees.hub"] = str(project.root)
        values["trees.location"] = None
    else:
        hub, reason = _slot_value(project.root, project, "trees", "core", "Hub",
                                  missing="no bindings file", subject="the Hub value")
        match = HUB_CHECKOUT.search(hub) if reason is None else None
        if match is not None:
            values["trees.hub"] = match.group(1)
        else:
            unbound["trees.hub"] = (*AUTOMODE_SLOTS["trees.hub"],
                                    reason or "the Hub value names no main checkout")
        _location, reason = _slot_value(project.root, project, "trees", "core", "Location",
                                        missing="no bindings file", subject="the Location value")
        roots = _trees_location(trees) if reason is None else []
        if roots:
            values["trees.location"] = roots[0].replace("/", "\\")
        else:
            unbound["trees.location"] = (
                *AUTOMODE_SLOTS["trees.location"],
                reason or "the Location value names no drive-absolute path in backticks")
    vc = _automode_body(project, "vc")
    system = _vc_system(project.root, project)
    if (vc is not None and _answers_none(vc)) or system[1] == "the System value reads none":
        values["vc.system"] = None
        values["vc.default-branch"] = None
    else:
        for name, (value, reason) in (("vc.system", system),
                                      ("vc.default-branch",
                                       _vc_main_branch(project.root, project))):
            if reason is None:
                values[name] = value
            else:
                unbound[name] = (*AUTOMODE_SLOTS[name], reason)
    return values, unbound


def _automode_compose(root, named, fragments):
    filled = [(rel, project, *_automode_values(root, project)) for rel, project in named]
    composed = {key: [] for key in AUTOMODE_KEYS}
    found = set()
    for key in AUTOMODE_KEYS:
        for pack, entries in fragments:
            for entry in entries:
                if entry.section != key:
                    continue
                names = AUTOMODE_PLACEHOLDER.findall(entry.text)
                if all(name == "root" for name in names):
                    fills = [{"root": str(root)}]
                else:
                    fills = []
                    for index, (rel, project, values, unbound) in enumerate(filled):
                        if pack.name not in {held.name for held in project.composed}:
                            continue
                        if any(name in values and values[name] is None for name in names):
                            continue
                        missing = [name for name in names if name in unbound]
                        for name in missing:
                            found.add((index, AUTOMODE_PLACEHOLDERS.index(name), rel,
                                       *unbound[name]))
                        if not missing:
                            fills.append(values)
                for values in fills:
                    line = AUTOMODE_PLACEHOLDER.sub(lambda match: values[match.group(1)],
                                                    entry.text)
                    if line not in composed[key]:
                        composed[key].append(line)
    return composed, [record[2:] for record in sorted(found)]


def _automode_settings_path():
    return Path.home().joinpath(*AUTOMODE_SETTINGS)


def _automode_constant(literal):
    raise ValueError(f"the constant {literal} is not JSON")


def _automode_settings(path):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return {}, None
    except OSError as exc:
        return None, f"unreadable: {exc}"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"not UTF-8: {exc}"
    try:
        document = json.loads(text.removeprefix("﻿"), parse_constant=_automode_constant)
    except (ValueError, RecursionError) as exc:
        return None, f"invalid JSON: {exc}"
    try:
        json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except UnicodeEncodeError as exc:
        return None, f"not UTF-8: {exc}"
    except ValueError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(document, dict):
        return None, "the document is not an object"
    if "autoMode" not in document:
        return document, None
    mode = document["autoMode"]
    if not isinstance(mode, dict):
        return None, "autoMode is not an object"
    for key in AUTOMODE_KEYS:
        if key in mode and not (isinstance(mode[key], list)
                                and all(isinstance(item, str) for item in mode[key])):
            return None, f"autoMode.{key} is not a list of strings"
    return document, None


def _automode_transform(document, composed):
    result = dict(document)
    mode = dict(document.get("autoMode", {}))
    for key in AUTOMODE_KEYS:
        rest = [entry for entry in mode.get(key, [])
                if not entry.startswith(AUTOMODE_TAG) and entry != AUTOMODE_DEFAULTS]
        mode[key] = [AUTOMODE_DEFAULTS, *composed[key], *rest]
    result["autoMode"] = mode
    return result


def _automode_drift(document, composed):
    drift = []
    for key in AUTOMODE_KEYS:
        entries = document.get("autoMode", {}).get(key, [])
        causes = []
        if [entry for entry in entries if entry.startswith(AUTOMODE_TAG)] != composed[key]:
            causes.append("tagged entries differ")
        if AUTOMODE_DEFAULTS not in entries:
            causes.append(f'"{AUTOMODE_DEFAULTS}" missing')
        if causes:
            drift.append((key, causes))
    return drift


def _automode_diff(path, key, current, proposed):
    return list(difflib.unified_diff(current, proposed, f"{path} autoMode.{key}",
                                     f"composed autoMode.{key}",
                                     n=len(current) + len(proposed), lineterm=""))


def _automode_read(root):
    paths = workspace_projects(root)
    if not paths:
        return AutomodeRead([], None, None, AutomodeRefusal(
            f"no project at {root} or in its immediate children", (), False))
    scanned = []
    for path in paths:
        rel = "." if path == root else path.name
        project, rows = load_project(path)
        if project is None:
            row = rows[0]
            return AutomodeRead(scanned, None, None, AutomodeRefusal(
                f"project {rel} does not load — {row.code} {row.path}: {row.message}", (),
                False))
        included, reason = _vc_automode_named(path, project)
        if included is None:
            return AutomodeRead(scanned, None, None, AutomodeRefusal(
                f"project {rel}: vc Auto-mode entries — {reason}", (), False))
        scanned.append((rel, project, included))
    named = [(rel, project) for rel, project, included in scanned if included]
    bases = []
    for _rel, project in named:
        if project.base not in bases:
            bases.append(project.base)
    if len(bases) > 1:
        details = tuple(f"  {rel}: base {project.base}" for rel, project in named)
        return AutomodeRead(scanned, None, None, AutomodeRefusal(
            f"the named projects are on {len(bases)} bases", details, False))
    base = bases[0] if bases else None
    union = {}
    for _rel, project in named:
        for pack in project.composed:
            if _declares_automode(pack) is not None and pack.name not in union:
                union[pack.name] = pack
    packs = sorted(union.values(), key=lambda pack: (pack.name != "core", pack.name))
    rows = [row for row in check_v13(packs) if row.message.startswith("automode file")]
    rows += check_v24(packs)
    unread = [pack for pack in packs
              if f"{pack.rel}/{_declares_automode(pack)}" not in pack.texts]
    if rows or unread:
        details = []
        for row in rows:
            details.append(format_row(row))
        cited = {row.path for row in rows}
        for pack in unread:
            rel = f"{pack.rel}/{_declares_automode(pack)}"
            if rel in pack.files and rel not in cited:
                details.append(f"{rel}: not a readable .md autoMode fragment")
        return AutomodeRead(scanned, base, None, AutomodeRefusal(
            "an autoMode fragment is missing or malformed", tuple(details), True))
    fragments = [(pack, parse_automode(pack.texts[f"{pack.rel}/{_declares_automode(pack)}"])[0])
                 for pack in packs]
    composed, records = _automode_compose(root, named, fragments)
    if records:
        details = tuple(f"{rel}: {binding} {slot} — {reason}"
                        for rel, binding, slot, reason in records)
        return AutomodeRead(scanned, base, None, AutomodeRefusal(
            f"{len(records)} placeholder slots unbound", details, True))
    return AutomodeRead(scanned, base, composed, None)


def _automode_workspace_root(project):
    hub = _trees_hub_path(project.root, project.manifest.get("bindings"))
    if hub is not None and (hub / MANIFEST_REL).is_file():
        main = hub.resolve()
    else:
        main = project.root.resolve()
    return main.parent if (main.parent / MANIFEST_REL).is_file() else main


def automode_rows(project, memo=None):
    memo = {} if memo is None else memo
    root = project.root
    try:
        root = _automode_workspace_root(project)
        held = memo.get(root)
        if held is None:
            record = _automode_read(root)
            settings = None
            if record.refusal is None:
                path = _automode_settings_path()
                document, reason = _automode_settings(path)
                settings = (path, document, reason)
            held = (record, settings)
            memo[root] = held
        record, settings = held
        if record.refusal is not None:
            reason = record.refusal.reason
        else:
            path, document, reason = settings
            if reason is not None:
                reason = f"the settings file {path}: {reason}"
            else:
                drift = _automode_drift(document, record.composed)
                if not drift:
                    return []
                arrays = ", ".join(f"autoMode.{key} ({'; '.join(causes)})"
                                   for key, causes in drift)
                return [Row("AUTOMODE", AUTOMODE_ROW_PATH,
                            f"{arrays} drift from the block composed for {root}; run harness.py "
                            f'automode --root "{root}" --apply in your own terminal')]
    except (OSError, UnicodeDecodeError) as exc:
        reason = str(exc)
    return [Row("AUTOMODE", AUTOMODE_ROW_PATH,
                f'drift not checked for {root}: {reason}; harness.py automode --root "{root}" '
                "shows why")]


def automode(root, apply=False):
    if apply:
        marker = next((name for name in AUTOMODE_MARKERS if os.environ.get(name)), None)
        if marker is not None:
            return _refuse(f"--apply in a Claude Code shell: {marker} is set; the apply is the "
                           "human's to run in their own terminal", verb="automode")
    record = _automode_read(root)
    if record.refusal is None or record.refusal.after_banner:
        print(f"automode: workspace {root}; {len(record.scanned)} projects; "
              f"base {'none' if record.base is None else record.base}")
        for rel, _project, included in record.scanned:
            print(f"project: {rel}  {'named' if included else 'excluded'}")
    if record.refusal is not None:
        for line in record.refusal.details:
            print(line, file=sys.stderr)
        return _refuse(record.refusal.reason, verb="automode")
    composed = record.composed
    path = _automode_settings_path()
    document, reason = _automode_settings(path)
    if reason is not None:
        return _refuse(f"the settings file {path}: {reason}", verb="automode")
    proposed = _automode_transform(document, composed)
    for key in AUTOMODE_KEYS:
        print(f"## {key}")
        for line in composed[key]:
            print(f"- {line}")
    current = document.get("autoMode", {})
    diffs = [_automode_diff(path, key, current.get(key, []), proposed["autoMode"][key])
             for key in AUTOMODE_KEYS]
    for diff in diffs:
        for line in diff:
            print(line)
    if not any(diffs):
        print(f"automode: no difference against {path}")
        if apply:
            print("automode: nothing written — the settings file already holds the composed "
                  "entries")
            print("automode: reminder — run claude auto-mode critique")
        return 0
    added = sum(line.startswith("+") for diff in diffs for line in diff[2:])
    removed = sum(line.startswith("-") for diff in diffs for line in diff[2:])
    if not apply:
        print(f"automode: {added} entries added, {removed} removed; nothing written — run with "
              "--apply to write")
        return 0
    try:
        data = (json.dumps(proposed, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    except UnicodeEncodeError as exc:
        return _refuse(f"the settings file {path}: not UTF-8: {exc}", verb="automode")
    print(f"automode: {added} entries added, {removed} removed")
    try:
        _write_whole(path, data)
    except OSError as exc:
        return _refuse(f"cannot write {path}: {exc}; the settings file is unchanged",
                       verb="automode")
    print(f"automode: wrote {path}")
    print("automode: reminder — run claude auto-mode critique")
    return 0


def budget(root, hub, feature):
    project, rows = load_project(root)
    if project is None:
        return _refuse(rows[0].message, verb="budget")
    if feature is not None and (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", feature)
                                or ".." in feature):
        return _refuse(f"invalid feature name {feature!r}", verb="budget")
    memory_root = hub or root
    kinds = ("status", "body", "plan") if feature is not None else ("status",)
    items = budget_items(root, project, memory_root, feature, kinds)
    if feature is not None:
        for item in items:
            if item.label == "Architecture-doc body budget" and item.cause == "no match":
                return _refuse(f"no architecture doc matches {item.path} for feature {feature}",
                               verb="budget")
    print(f"budget: project {root}; memory {memory_root}; feature {feature or 'none'}")
    for item in items:
        print(f"{item.state}  {item.label}  {item.path}  {item.detail}")
    failed = any(item.state == "FAIL" for item in items)
    print("budget: FAIL" if failed else "budget: PASS")
    return 1 if failed else 0


def bounds_slot(root, project, label):
    value, reason = _slot_value(root, project, "classes", "light-lane", label)
    if reason is not None:
        return None, reason
    head = value.split(" — ", 1)[0].strip()
    if label == "Trivial bound":
        match = re.fullmatch(r"(\d+) lines?, (\d+) files?", head)
        if match is None:
            return None, "the bound is not <n> lines, <m> file"
        return (int(match.group(1)), int(match.group(2))), None
    if label == "Prose paths":
        globs = [glob.strip() for glob in SLOT_SPAN.findall(head)]
        if not globs:
            return None, "the bound holds no glob"
        if "" in globs:
            return None, "the bound holds an empty glob"
        span = SLOT_SPAN.pattern
        if re.fullmatch(rf"{span}(?:\s*,\s*{span})*", head) is None:
            return None, "the bound holds text beside its globs"
        return globs, None
    match = re.fullmatch(r"(\d+) items?", head)
    if match is None:
        return None, "the bound is not <n> items"
    return int(match.group(1)), None


def _unquote_numstat_path(rel):
    if len(rel) < 2 or not (rel.startswith('"') and rel.endswith('"')):
        return rel
    escape = rb'\\([0-3][0-7]{2}|[abtnvfr"\\])'
    inner = rel[1:-1].encode("utf-8")
    if re.fullmatch(rb'(?:[^"\\]|' + escape + rb")*", inner) is None:
        return None
    named = {b"a": b"\a", b"b": b"\b", b"t": b"\t", b"n": b"\n", b"v": b"\v", b"f": b"\f",
             b"r": b"\r", b'"': b'"', b"\\": b"\\"}
    raw = re.sub(escape, lambda match: named.get(match.group(1))
                 or bytes([int(match.group(1), 8)]), inner)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_numstat(path):
    if path is None:
        return None, "no numstat file"
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, f"cannot read the numstat file {path}"
    entries = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if "\t" not in line:
            added, deleted, rel = "-", "-", line
        else:
            fields = line.split("\t")
            if len(fields) != 3 or not all(re.fullmatch(r"\d+|-", field)
                                           for field in fields[:2]):
                return None, f"numstat line {number} does not parse"
            added, deleted, rel = fields
        if not rel or " => " in rel:
            return None, f"numstat line {number} does not parse"
        rel = _unquote_numstat_path(rel)
        if not rel:
            return None, f"numstat line {number} does not parse"
        entries.append((None if added == "-" else int(added),
                        None if deleted == "-" else int(deleted), rel))
    if not entries:
        return None, "the numstat file lists no file"
    return entries, None


def bounds_lines(root, project, declared, numstat, items):
    count = len(set(items))
    lines = []
    if declared == "slim":
        lines.append(("PASS", "class", "slim has no bound"))
    else:
        label = "Trivial bound" if declared == "trivial" else "Prose paths"
        bound, reason = bounds_slot(root, project, label)
        if reason is None:
            entries, reason = read_numstat(numstat)
        if reason is not None:
            lines.append(("FAIL", label, reason))
        else:
            paths = list(dict.fromkeys(rel for _added, _deleted, rel in entries))
            if declared == "trivial":
                unknown = list(dict.fromkeys(rel for added, deleted, rel in entries
                                             if added is None or deleted is None))
                if unknown:
                    lines.append(("FAIL", label, "no line count for " + ", ".join(unknown)))
                else:
                    changed = sum(added + deleted for added, deleted, _rel in entries)
                    most_lines, most_files = bound
                    state = ("PASS" if changed <= most_lines and len(paths) <= most_files
                             else "FAIL")
                    lines.append((state, label, f"{changed} of {most_lines} lines, "
                                                f"{len(paths)} of {most_files} files"))
            else:
                outside = [rel for rel in paths
                           if not any(glob_match(glob, rel) for glob in bound)]
                if outside:
                    lines.append(("FAIL", label, "on no glob: " + ", ".join(outside)))
                else:
                    lines.append(("PASS", label, f"{len(paths)} files, every one on a glob"))
    if count >= 2:
        cap, reason = bounds_slot(root, project, "Batch cap")
        if reason is not None:
            lines.append(("FAIL", "Batch cap", reason))
        else:
            lines.append(("PASS" if count <= cap else "FAIL", "Batch cap",
                          f"{count} of {cap} items"))
    failed = any(state == "FAIL" for state, _label, _detail in lines)
    return lines, "slim" if failed else declared, count


def bounds(root, declared, numstat, items):
    project, rows = load_project(root)
    if project is None:
        return _refuse(rows[0].message, verb="bounds")
    if declared not in BOUNDS_CLASSES:
        return _refuse(f"class {declared!r} is not slim, prose or trivial", verb="bounds")
    lines, _effective, count = bounds_lines(root, project, declared, numstat, items)
    print(f"bounds: project {root}; class {declared}; items {count}")
    for state, bound_label, detail in lines:
        print(f"{state}  {bound_label}  {detail}")
    failed = any(state == "FAIL" for state, _label, _detail in lines)
    print(f"bounds: FAIL — class slim, escalated from {declared}" if failed
          else f"bounds: PASS — class {declared}")
    return 1 if failed else 0


def close_slot(root, project):
    value, reason = _slot_value(root, project, "classes", "light-lane", "Delegated classes")
    if reason is not None:
        return None, reason
    names = [name.strip() for name in value.split(" — ", 1)[0].split(",")]
    if any(name not in CLOSE_CLASSES for name in names) or len(set(names)) != len(names):
        return None, "the value names no closing class"
    return names, None


def _close_paths(root, project, paths):
    found = []
    value, reason = _slot_value(root, project, "process-docs", "core", "Design docs")
    prefix = None
    if reason is None:
        span = SLOT_SPAN.search(value)
        prefix = span.group(1).split("<", 1)[0].strip() if span is not None else ""
        if not prefix:
            reason = "the value names no path"
    if reason is not None:
        found.append(f"Design docs slot: {reason}")
    for rel in paths:
        ok, why = contained(root, rel)
        if not ok:
            found.append(f"{rel} is not a contained path: {why}")
            continue
        folded = rel.casefold()
        kind = next((kind for kind, patterns in CLOSE_TRIGGERS
                     if any(glob_match("**/" + pattern, folded) for pattern in patterns)), None)
        if kind is not None:
            found.append(f"{kind} {rel}")
            continue
        if prefix and folded.startswith(prefix.casefold()):
            found.append(f"locked doc {rel}")
            continue
        if not folded.endswith(".md"):
            continue
        if not (root / rel).exists():
            found.append(f"locked doc {rel}")
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            found.append(f"cannot read {rel}")
            continue
        if not text.startswith("---"):
            continue
        try:
            data = parse_frontmatter(text)
        except FrontmatterError:
            found.append(f"front matter of {rel} does not parse")
            continue
        if data.get("status") == "locked" or (data.get("type") == "requirements"
                                              and data.get("status") == "accepted"):
            found.append(f"locked doc {rel}")
    if found:
        return "HUMAN", "; ".join(found)
    return "PASS", f"{len(paths)} files: no binding, settings, fragment or locked doc"


def _entry_pattern(key):
    escaped = re.escape(key)
    return re.compile(rf"- \*\*(?:{escaped}(?:\*\*|\s)|`{escaped}`(?:\*\*|\s|:))")


def _entry_end(lines, index, end):
    index += 1
    while index < end and lines[index][:1] in (" ", "\t") and lines[index].strip():
        index += 1
    return index


def _close_block(branch, status):
    if branch is None:
        return "HUMAN", "no branch"
    if status is None:
        return "HUMAN", "no STATUS file"
    try:
        text = Path(status).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "HUMAN", "cannot read the STATUS file"
    lines = text.split("\n")
    start = end = 0
    if "## Current" in lines:
        start = lines.index("## Current") + 1
        end = next((index for index in range(start, len(lines))
                    if lines[index].startswith("## ")), len(lines))
    pattern = _entry_pattern(branch)
    found = [index for index in range(start, end) if pattern.match(lines[index])]
    if not found:
        return "HUMAN", f"no block for {branch} under ## Current"
    if len(found) > 1:
        return "HUMAN", f"{len(found)} blocks for {branch}"
    block = "\n".join(lines[found[0]:_entry_end(lines, found[0], end)])
    words = [f"{word} on the block" for word in ("human-ask", "human-check") if word in block]
    if words:
        return "HUMAN", "; ".join(words)
    return "PASS", "no human-ask, no human-check"


def _close_items(items, brief):
    closed = list(dict.fromkeys(items))
    if brief is None:
        if len(closed) >= 2:
            return "HUMAN", "a batch with no launch brief"
        return "PASS", f"{len(closed)} items as declared"
    try:
        lines = Path(brief).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return "HUMAN", "cannot read the brief"
    lane = None
    if "## Lane" in lines:
        start = lines.index("## Lane") + 1
        end = next((index for index in range(start, len(lines))
                    if lines[index].startswith("## ")), len(lines))
        lane = next((line.strip() for line in lines[start:end] if line.strip()), None)
    if lane is None:
        return "HUMAN", "the brief has no Lane"
    if ", batch " not in lane:
        if len(closed) >= 2:
            return "HUMAN", f"the Lane names no batch for {len(closed)} items"
        return "PASS", f"{len(closed)} items as declared"
    declared = [name.strip() for name in lane.split(", batch ", 1)[1].split(",")]
    if not all(re.fullmatch(r"[^\s,]+", name) for name in declared):
        return "HUMAN", "the Lane's batch does not parse"
    declared = list(dict.fromkeys(declared))
    if set(declared) != set(closed):
        return "HUMAN", (f"items {', '.join(closed) or 'none'} not as declared "
                         f"{', '.join(declared)}")
    return "PASS", f"{len(closed)} items as declared"


def _close_reading(check, value, wanted):
    if value is None:
        return "HUMAN", f"no {check} reading"
    if value == wanted:
        return "PASS", value
    if check == "review" and value == "open":
        return "HUMAN", "open findings"
    return "HUMAN", f"reads {value}"


def _close_upgrade(root):
    found = []
    run, refusal = upgrade_plan(root, True, None)
    if refusal is not None:
        found.append(f"refused — {refusal}")
    else:
        outcome = next((outcome for outcome in run.outcomes
                        if outcome.label not in ("unchanged", "preserved", "orphaned")), None)
        if outcome is not None:
            found.append(f"the dry run reads {outcome.label} {outcome.path}")
        if any(line.startswith("  manifest: ") for line in run.lines):
            found.append("the dry run writes the manifest")
        found += [line.strip() for line in run.lines if line.startswith("  slots missing:")]
    failures, _warnings, _banners = validate_report(root)
    if failures:
        found.append(f"validate: {format_row(failures[0])}")
    failures, _warnings, _banner = doctor_report(root)
    if failures:
        found.append(f"doctor: {format_row(failures[0])}")
    if found:
        return "HUMAN", "; ".join(found)
    return "PASS", "dry run plans no write; validate and doctor pass"


def _close_escaped(text):
    return CLOSE_CONTROL.sub(lambda match: repr(match.group())[1:-1], text)


def close_class(root, declared, numstat, items, branch, status, brief, review, preflight, slot):
    project, rows = load_project(root)
    if project is None:
        return _refuse(rows[0].message, verb="close-class")
    classes, reason = close_slot(root, project)
    if slot:
        print(f"close-class: slot {', '.join(classes)}" if reason is None
              else f"close-class: slot delegates nothing — {reason}")
        return 0
    if declared not in BOUNDS_CLASSES:
        return _refuse(f"class {declared!r} is not slim, prose or trivial", verb="close-class")
    checks = [("slot", "PASS", ", ".join(classes)) if reason is None
              else ("slot", "HUMAN", reason)]
    entries, reason = read_numstat(numstat)
    paths = [] if entries is None else list(dict.fromkeys(rel for _a, _d, rel in entries))
    if reason is None and any(CLOSE_CONTROL.search(rel) for rel in paths):
        reason = "control character in a path"
    checks.append(("paths", "HUMAN", reason) if reason is not None
                  else ("paths", *_close_paths(root, project, paths)))
    checks.append(("block", *_close_block(branch, status)))
    if items or brief is not None:
        checks.append(("items", *_close_items(items, brief)))
    checks.append(("review", *_close_reading("review", review, "clean")))
    checks.append(("preflight", *_close_reading("preflight", preflight, "PASS")))
    upgraded = MANIFEST_REL in paths and all(rel in (MANIFEST_REL, "CLAUDE.md")
                                             or rel in project.ledger for rel in paths)
    if upgraded:
        checks.append(("upgrade", *_close_upgrade(root)))
    lines, effective, count = bounds_lines(root, project, declared, numstat, items)
    human = [f"{check}: {detail}" for check, state, detail in checks if state == "HUMAN"]
    candidate = "delegated" if upgraded or effective in ("prose", "trivial") else "audited"
    if human:
        verdict = "human — " + "; ".join(human)
    elif candidate not in classes:
        verdict = f"human — slot omits {candidate}"
    elif upgraded:
        verdict = "delegated — a clean harness upgrade; dry run plans no write; slot names delegated"
    elif candidate == "delegated":
        verdict = f"delegated — effective {effective}; slot names delegated"
    else:
        verdict = "audited — effective slim; review clean; items as declared; slot names audited"
    print(f"close-class: project {root}; branch {branch or 'none'}; class {declared}; "
          f"items {count}")
    for check, state, detail in checks:
        print(f"{state}  {check}  {_close_escaped(detail)}")
    for state, bound_label, detail in lines:
        print(f"{state}  {bound_label}  {_close_escaped(detail)}")
    print(f"close-class: {_close_escaped(verdict)}")
    return 0


def contained(root, rel):
    if "\\" in rel:
        return False, "holds a backslash"
    if rel.startswith("/"):
        return False, "is absolute"
    segments = rel.split("/")
    if ".." in segments:
        return False, "holds a '..' segment"
    if "" in segments:
        return False, "holds an empty segment"
    crossing = _crossing(root, rel)
    if crossing is None:
        return True, None
    component, kind = crossing
    return False, (f"{component} is not a directory" if kind == "not a directory"
                   else f"{component} is a {kind}")


@dataclass
class Outcome:
    path: str
    label: str
    detail: str | None
    data: bytes | None
    digest: str | None


def _bindings_pack(path, composed):
    return next((pack for pack in composed if path == f".claude/bindings/{pack.name}.md"), None)


def _decoded(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def upgrade_outcomes(project, composition, take_theirs, paths):
    sources, texts, ledger = composition.sources, composition.texts, project.ledger
    if take_theirs is not None:
        if take_theirs not in ledger:
            return None, f"--take-theirs {take_theirs} is not in the ledger"
        if project.classified[take_theirs] != "ledgered":
            return None, (f"--take-theirs {take_theirs} is classified "
                          f"{project.classified[take_theirs]}, not ledgered")
        if take_theirs not in sources and take_theirs not in texts:
            return None, f"--take-theirs {take_theirs} is not shipped by any composed pack"
    outcomes = []
    for path in paths:
        try:
            name = classify(path, project.classes)
        except ClassificationError as exc:
            return None, f"x-classification is not usable: {exc.args[0]}"
        ledgered = path in ledger
        if not _shipped(path):
            outcomes.append(Outcome(path, "dropped from the ledger", None, None, None))
            continue
        if path not in sources and path not in texts:
            outcomes.append(Outcome(path, "orphaned",
                                    "no composed pack ships it; the human removes it or "
                                    "composes the pack that now ships it", None, None))
            continue
        disk = None
        on_disk = project.root / path
        if on_disk.is_file():
            try:
                disk = on_disk.read_bytes()
            except OSError as exc:
                return None, f"{path} is not readable: {exc.strerror}"
        if path in texts:
            planned = texts[path].encode("utf-8")
        else:
            try:
                planned = (project.base / sources[path]).read_bytes()
            except OSError as exc:
                return None, f"{sources[path]} is not readable: {exc.strerror}"
        planned_hash = ledger_hash(planned)
        disk_hash = None if disk is None else ledger_hash(disk)
        equal = disk_hash is not None and disk_hash == planned_hash
        taken = path == take_theirs and not equal and (disk is None
                                                       or disk_hash != ledger[path])
        if name == "LOCKED":
            outcomes.append(Outcome(path, "unchanged", None, None,
                                    disk_hash if ledgered else None) if equal
                            else Outcome(path, "replaced (LOCKED)", None, planned,
                                         planned_hash))
        elif name == "PRESERVE":
            outcomes.append(_preserve_outcome(path, disk, planned, ledgered, composition))
        elif name == "managed":
            outcomes.append(_managed_outcome(path, disk, composition))
        elif not ledgered:
            if disk is None:
                outcomes.append(Outcome(path, "added", None, planned, planned_hash))
            elif equal:
                outcomes.append(Outcome(path, "adopted", None, None, disk_hash))
            else:
                outcomes.append(Outcome(path, "not adopted: a local file at a pack path",
                                        None, None, None))
        elif taken:
            outcomes.append(Outcome(path, "replaced (--take-theirs)", None, planned,
                                    planned_hash))
        elif disk is None:
            outcomes.append(Outcome(path, "missing: locally deleted", None, None, None))
        elif disk_hash == ledger[path]:
            outcomes.append(Outcome(path, "unchanged", None, None, disk_hash) if equal
                            else Outcome(path, "replaced", None, planned, planned_hash))
        else:
            outcomes.append(Outcome(path, "current", None, None, disk_hash) if equal
                            else Outcome(path, "skipped: locally modified", None, None, None))
    return outcomes, None


def _preserve_outcome(path, disk, planned, ledgered, composition):
    if disk is None:
        return (Outcome(path, "missing", None, None, None) if ledgered
                else Outcome(path, "added", None, planned, ledger_hash(planned)))
    pack = _bindings_pack(path, composition.composed)
    existing = _decoded(disk)
    if pack is None or existing is None:
        return Outcome(path, "preserved", None, None, None)
    keys = [key for key in _declared_bindings(pack)
            if composition.fillers.get(key) == pack.name]
    grown, appended = grow_bindings_file(existing, pack, keys)
    if not appended:
        return Outcome(path, "preserved", None, None, None)
    data = grown.encode("utf-8")
    return Outcome(path, "appended", ", ".join(appended), data, ledger_hash(data))


def _managed_outcome(path, disk, composition):
    if disk is None:
        return Outcome(path, "missing", None, None, None)
    existing = _decoded(disk)
    rewritten = (rewrite_managed_block(existing, render_managed_block(composition.names))
                 if existing is not None else None)
    if rewritten is None:
        return Outcome(path, "not written: unusable markers", None, None, None)
    if rewritten == existing:
        return Outcome(path, "unchanged", None, None, None)
    data = rewritten.encode("utf-8")
    return Outcome(path, "merged", None, data, ledger_hash(data))


def _report_packs(project, composition):
    fields = []
    for name in sorted(composition.versions):
        version = composition.versions[name]
        recorded = project.named.get(name)
        fields.append(f"{name} {recorded} -> {version}"
                      if recorded is not None and recorded != version else f"{name} {version}")
    return "  packs: " + ", ".join(fields)


def _report_filling(composition, outcomes):
    filling = []
    for outcome in outcomes:
        pack = _bindings_pack(outcome.path, composition.composed)
        if outcome.data is None or pack is None:
            continue
        keys = ([key for key in outcome.detail.split(", ") if key in composition.required]
                if outcome.label == "appended"
                else next((keys for name, keys in composition.to_fill if name == pack.name), []))
        if keys:
            filling.append(f"{outcome.path} ({', '.join(keys)})")
    return "  bindings to fill: " + (", ".join(filling) if filling else "none")


def _slot_labels(template):
    labels = []
    for line in template.splitlines():
        if not line.startswith("- ") or ":" not in line:
            continue
        label = line[2:].split(":", 1)[0]
        if "—" not in label and "`" not in label and len(label) <= 40:
            labels.append(label)
    return labels


def _answers_none(body):
    answers = [line for line in body if line.startswith("- ")]
    return (len(answers) == 1
            and re.match(r"none(\s|—|$)", answers[0][2:], re.IGNORECASE) is not None)


def _missing_slots(body, template):
    if _answers_none(body):
        return []
    return [label for label in _slot_labels(template)
            if not any(line.startswith(f"- {label}:") for line in body)]


def _report_slots(project, composition, outcomes):
    lines = []
    for outcome in outcomes:
        pack = _bindings_pack(outcome.path, composition.composed)
        on_disk = project.root / outcome.path
        if pack is None or not on_disk.is_file():
            continue
        existing = _decoded(on_disk.read_bytes())
        if existing is None:
            continue
        declared = _declared_bindings(pack)
        fields = []
        for key in declared:
            body = _binding_section(existing, key)
            template = pack.texts.get(f"{pack.rel}/{declared[key]}")
            if composition.fillers.get(key) != pack.name or body is None or template is None:
                continue
            missing = _missing_slots(body, template)
            if missing:
                fields.append(f"{key}: {', '.join(missing)}")
        if fields:
            lines.append(f"  slots missing: {outcome.path} ({'; '.join(fields)})")
    return lines


def _report_design_docs(project, composition):
    filler = composition.fillers.get("process-docs")
    if filler is None:
        return []
    rel = f".claude/bindings/{filler}.md"
    on_disk = project.root / rel
    if not on_disk.is_file():
        return []
    existing = _decoded(on_disk.read_bytes())
    if existing is None:
        return []
    body = _binding_section(existing, "process-docs")
    if body is None:
        return []
    reading = _design_docs_reading(body)
    if reading not in ("Design docs reads none", "no Design docs line"):
        return []
    return [f"  design docs: {rel} (process-docs: {reading}; V20 refuses it)"]


def _report_path_form(project, composition):
    filler = composition.fillers.get("verification")
    if filler != "unity":
        return []
    rel = f".claude/bindings/{filler}.md"
    on_disk = project.root / rel
    if not on_disk.is_file():
        return []
    existing = _decoded(on_disk.read_bytes())
    if existing is None:
        return []
    body = _binding_section(existing, "verification")
    if body is None:
        return []
    reading = _path_form_reading(body)
    if reading is None:
        return []
    return [f"  path form: {rel} (verification: {reading}; V21 warns)"]


COMMAND_WORD = "python" + "3"
_COMMAND_WORD_AFTER = re.compile(r"(?:[`\"']|Bash\(|exec[ \t]+|[|&;][ \t]*)"
                                 + re.escape(COMMAND_WORD) + r"(?=\s|$)")
_COMMAND_WORD_ARGV = re.compile(r"\[[ \t]*([\"'])" + re.escape(COMMAND_WORD) + r"\1")
_COMMAND_WORD_FIRST = re.compile(re.escape(COMMAND_WORD) + r"(?=\s|$)")


def command_word_lines(text):
    lines = text.split("\n")
    fenced = set()
    fence = None
    for index, line in enumerate(lines):
        marker = CODE_FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1) == fence:
                fence = None
        elif fence is not None:
            fenced.add(index)
    return [index + 1 for index, line in enumerate(lines)
            if _COMMAND_WORD_AFTER.search(line) or _COMMAND_WORD_ARGV.search(line)
            or (index in fenced and _COMMAND_WORD_FIRST.match(line.strip()))]


def _report_command_words(project):
    root = project.root
    lines = []
    for path in [*sorted((root / ".claude/bindings").glob("*.md")), root / "CLAUDE.md"]:
        if not path.is_file():
            continue
        text = _decoded(path.read_bytes())
        numbers = command_word_lines(text) if text is not None else []
        if numbers:
            rel = path.relative_to(root).as_posix()
            lines.append(f"  {COMMAND_WORD} left: {rel} "
                         f"(lines {', '.join(str(number) for number in numbers)}); "
                         "upgrade edits none of it")
    return lines


def upgrade_manifest_text(project, composition, outcomes):
    merged = {**{rel: digest for rel, digest in project.ledger.items() if _shipped(rel)},
              **{outcome.path: outcome.digest for outcome in outcomes
                 if outcome.digest is not None}}
    preset, parent = project.manifest.get("preset"), project.manifest.get("parent")
    return manifest_text(project.written, preset, composition.versions, merged,
                         composition.fillers, parent=parent)


def upgrade_report(project, composition, outcomes, dry_run, take_theirs=None):
    root = project.root
    path = root / MANIFEST_REL
    rendered = upgrade_manifest_text(project, composition, outcomes).encode("utf-8")
    manifest_changes = not (path.is_file()
                            and ledger_hash(path.read_bytes()) == ledger_hash(rendered))
    lines = [f"upgrade: {root}", _report_packs(project, composition)]
    lines += [f"  {outcome.label}: {outcome.path} ({outcome.detail})"
              if outcome.label in ("appended", "orphaned")
              else f"  {outcome.label}: {outcome.path}"
              for outcome in outcomes if outcome.label != "unchanged"]
    lines.append(f"  unchanged: {sum(1 for o in outcomes if o.label == 'unchanged')} files")
    if manifest_changes:
        lines.append(f"  manifest: {MANIFEST_REL}")
    lines += [f"  {note}" for note in composition.notes]
    if next((outcome.label for outcome in outcomes if outcome.path == take_theirs),
            None) in ("unchanged", "replaced"):
        lines.append(f"  --take-theirs {take_theirs}: not locally modified; handled as usual")
    lines += _report_slots(project, composition, outcomes)
    lines += _report_path_form(project, composition)
    lines += _report_design_docs(project, composition)
    lines += _report_command_words(project)
    lines.append(_report_filling(composition, outcomes))
    lines.append(f"  next: harness.py validate --root {root}, "
                 f"then harness.py doctor --root {root}")
    count = (sum(1 for outcome in outcomes if outcome.data is not None)
             + (1 if manifest_changes else 0))
    lines.append(f"upgrade: dry run — would write {count} files into {root}; nothing written"
                 if dry_run else f"upgrade: wrote {count} files into {root}")
    return lines


@dataclass
class UpgradeRun:
    project: Project
    composition: Composition
    outcomes: list
    lines: list


def _loader_reason(root, row):
    if row.code == "SCHEMA" and row.path == MANIFEST_REL:
        return f"the manifest at {root} is not usable: {row.message}"
    if row.path in (MANIFEST_REL, "schemas/manifest.schema.json"):
        return row.message
    return f"{row.path}: {row.message}"


def upgrade_plan(root, dry_run, take_theirs):
    project, rows = load_project(root)
    if project is None:
        return None, "; ".join(_loader_reason(root, row) for row in rows)
    composition = compose_plan(root, project.base, project.packs, sorted(project.named), None,
                               parent=project.parent_root if project.delta else None,
                               delta=project.delta, written=project.written,
                               parent_root=project.parent_root, ledger=project.ledger)
    if composition.refusal is not None:
        return None, composition.refusal
    if project.parent_root is not None and not project.delta:
        composition.notes.append(
            _parent_note(_recorded_path(project.parent_root, root)
                         or Path(project.parent_root).as_posix(), False))
    composition.notes += exclusion_notes(root, composition.ancestors, composition.exclusions,
                                         composition.left_out,
                                         ".claude/settings.json" in composition.texts)
    composition.notes += generated_notes(composition.generated,
                                         ".claude/settings.json" in composition.texts)
    paths = sorted(set(composition.sources) | set(composition.texts) | set(project.ledger))
    for path in paths:
        ok, reason = contained(root, path)
        if not ok:
            return None, f"{path} is not a contained path: {reason}"
    outcomes, refusal = upgrade_outcomes(project, composition, take_theirs, paths)
    if refusal is not None:
        return None, refusal
    return UpgradeRun(project=project, composition=composition, outcomes=outcomes,
                      lines=upgrade_report(project, composition, outcomes, dry_run,
                                           take_theirs)), None


def upgrade_apply(run):
    project, composition = run.project, run.composition
    _count, failure = write_project(project.root, project.base, {
        "sources": {},
        "texts": {},
        "data": {outcome.path: outcome.data for outcome in run.outcomes
                 if outcome.data is not None},
        "manifest": lambda _files: upgrade_manifest_text(project, composition, run.outcomes),
    })
    return failure


def upgrade(root, dry_run, take_theirs):
    run, refusal = upgrade_plan(root, dry_run, take_theirs)
    if refusal is not None:
        return _refuse(refusal, verb="upgrade")
    print("\n".join(run.lines))
    if dry_run:
        return 0
    failure = upgrade_apply(run)
    return _fail(failure, root, verb="upgrade") if failure is not None else 0


def upgrade_all(root):
    projects = workspace_projects(root)
    if not projects:
        return _refuse(f"no project at {root} or in its immediate children", verb="upgrade --all")
    refused = False
    print(f"upgrade --all: {len(projects)} projects under {root}")
    for project in projects:
        print(f"project: {'.' if project == root else project.name}")
        run, refusal = upgrade_plan(project, True, None)
        if refusal is not None:
            print(f"upgrade: refused — {refusal}")
            refused = True
            continue
        print("\n".join(run.lines))
    print("upgrade --all: dry run; nothing written")
    return 1 if refused else 0


def promote_mapping(path):
    outside = (f"{path} is not a promotable path; promote a file under .claude/agents/, "
               f".claude/skills/ or .claude/references/<pack>/")
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != ".claude":
        return None, outside
    if parts[1] == "agents":
        if len(parts) != 3 or not parts[2].endswith(".md"):
            return None, outside
        stem = PurePosixPath(parts[2]).stem
        return PromoteMapping(f"agents/{parts[2]}", "agents", stem, "agent", stem), None
    if parts[1] == "skills" and len(parts) >= 4:
        tail = "skills/" + "/".join(parts[2:])
        if len(parts) == 4 and parts[3] == "SKILL.md":
            return PromoteMapping(tail, "skills", parts[2], "skill", parts[2]), None
        return PromoteMapping(tail, None, None, "skill", parts[2]), None
    if parts[1] == "references" and len(parts) == 4:
        return PromoteMapping(f"references/{parts[3]}", "references", parts[3], None, None), None
    if parts[1] == "references" and len(parts) > 4:
        return None, f"{path} is a nested reference; a pack's references are flat file names"
    return None, outside


def _provides_line(lines, member):
    closing = _frontmatter_closing(lines)
    if closing is None:
        return None
    start = next((index for index in range(1, closing) if lines[index] == "provides:"), None)
    if start is None:
        return None
    for index in range(start + 1, closing):
        if not lines[index].startswith("  "):
            return None
        if re.fullmatch(rf"  {member}: \[.*\]", lines[index]):
            return index
    return None


def provides_edit(text, member, item):
    lines = text.split("\n")
    index = _provides_line(lines, member)
    if index is None:
        return None, False
    interior = lines[index][len(f"  {member}: ["):-1]
    names = interior.split(", ") if interior else []
    if item in names:
        return text, False
    names = sorted(names + [item])
    lines[index] = f"  {member}: [{', '.join(names)}]"
    rewritten = "\n".join(lines)
    try:
        provides = parse_frontmatter(rewritten).get("provides")
    except FrontmatterError:
        return None, False
    listed = provides.get(member) if isinstance(provides, dict) else None
    return (rewritten, True) if listed == names else (None, False)


def promote_stub(name, kind, member, item):
    members = {"agents": [], "skills": [], "references": []}
    members[member] = [item]
    return "\n".join([
        "---",
        f"name: {name}",
        f"kind: {kind}",
        "version: 0.0.0",
        "status: draft",
        "removal-date: null",
        f"description: {PROMOTE_STUB_DESCRIPTION}",
        "triggers: []",
        "requires: [core]",
        "conflicts: []",
        "provides:",
        f"  agents: [{', '.join(members['agents'])}]",
        f"  skills: [{', '.join(members['skills'])}]",
        f"  references: [{', '.join(members['references'])}]",
        "  preflight-checks: []",
        "roles: {}",
        "bindings: []",
        "---",
        "",
        f"# {name}",
        "",
        "TODO: what this pack is for, what a project gets by composing it, and which packs it "
        "requires. The version and the status stay 0.0.0 and draft until the human's review.",
        "",
    ])


def _promote_collision(packs, target, mapping):
    if mapping.label is None:
        return None
    holder = next((pack.name for pack in packs if pack is not target
                   and mapping.name in (pack.agents if mapping.label == "agent" else pack.skills)),
                  None)
    if holder is None:
        return None
    return f"{holder} already provides {mapping.label} {mapping.name}"


def promote(path, root, to, new_pack, kind):
    project, rows = load_project(root)
    if project is None:
        return _refuse("; ".join(_loader_reason(root, row) for row in rows), verb="promote")
    ok, reason = contained(root, path)
    if not ok:
        return _refuse(f"{path} is not a contained path: {reason}", verb="promote")
    mapping, refusal = promote_mapping(path)
    if refusal is not None:
        return _refuse(refusal, verb="promote")
    if not (root / path).is_file():
        return _refuse(f"{path} is not a file in this project", verb="promote")
    if path in project.ledger:
        return _refuse(f"{path} is already ledgered; promote takes a local file", verb="promote")
    if new_pack is not None:
        if re.fullmatch(PACK_IDENTIFIER, new_pack) is None:
            return _refuse(f"--new-pack name {new_pack} is not an identifier: {PACK_IDENTIFIER}",
                           verb="promote")
        if kind is None:
            return _refuse(f"--new-pack {new_pack} needs --kind", verb="promote")
        if kind not in PACK_KINDS:
            return _refuse(f"--kind {kind} is not a pack kind: {', '.join(PACK_KINDS)}",
                           verb="promote")
        if mapping.member is None:
            return _refuse(f"--new-pack needs a file that provides; "
                           f"promote {mapping.name}/SKILL.md first", verb="promote")
        if any(pack.name == new_pack for pack in project.packs):
            return _refuse(f"pack {new_pack} is already in the base", verb="promote")
        target, pack_rel = None, f"packs/{new_pack}"
    else:
        target = next((pack for pack in project.packs if pack.name == to), None)
        if target is None:
            return _refuse(f"unknown pack {to}", verb="promote")
        pack_rel = target.rel
    refusal = _promote_collision(project.packs, target, mapping)
    if refusal is not None:
        return _refuse(refusal, verb="promote")
    base = project.base
    destination = f"{pack_rel}/{mapping.tail}"
    if (base / destination).exists():
        return _refuse(f"{destination} already exists in the base", verb="promote")
    pack_md = f"{pack_rel}/PACK.md"
    try:
        data = (root / path).read_bytes()
    except OSError as exc:
        return _refuse(f"{path} is not readable: {exc.strerror}", verb="promote")
    if new_pack is not None:
        pack_text = promote_stub(new_pack, kind, mapping.member, mapping.item)
    elif mapping.member is None:
        pack_text = None
    else:
        current = target.texts.get(pack_md)
        pack_text, changed = (provides_edit(current, mapping.member, mapping.item)
                              if current is not None else (None, False))
        if pack_text is None:
            return _refuse(f"{pack_md} has no editable one-line provides.{mapping.member} list",
                           verb="promote")
        pack_text = pack_text if changed else None

    writes = [(destination, data)]
    if pack_text is not None:
        writes.append((pack_md, pack_text.encode("utf-8")))
    for rel, payload in writes:
        try:
            _write(base / rel, payload)
        except OSError as exc:
            return _fail(f"{exc.strerror} writing {rel}", base, verb="promote")
    lines = [f"promote: {path} -> {destination}",
             f"  pack: {new_pack} (new: status draft, version 0.0.0, kind {kind})"
             if new_pack is not None else f"  pack: {target.name} (existing)"]
    if pack_text is not None:
        lines.append(f"  provides.{mapping.member}: + {mapping.item}")
    lines += [f"  next: harness.py validate --root {base}",
              f"promote: wrote {len(writes)} files into {base}"]
    print("\n".join(lines))
    return 0


def outline(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return _refuse(f"cannot read {path}: {exc.strerror}", verb="outline")
    fence = None
    for number, line in enumerate(text.split("\n"), start=1):
        marker = CODE_FENCE.match(line)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1) == fence:
                fence = None
        elif fence is None and ATX_HEADING.match(line):
            print(f"{number:>5}  {line.rstrip()}")
    return 0


def project_slug(root):
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(root).resolve()))


def usage_transcripts(directory, root):
    if not directory.is_dir():
        return []
    slug = project_slug(root)
    return sorted(path for child in directory.iterdir()
                  if child.is_dir() and child.name.startswith(slug)
                  for path in child.glob("*.jsonl"))


def _usage_records(path):
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def _on_or_after(timestamp, since):
    if since is None:
        return True
    try:
        moment = datetime.datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        return False
    if moment.tzinfo is not None:
        moment = moment.astimezone(datetime.timezone.utc)
    return moment.date() >= since


def _seconds(start, end):
    try:
        return (datetime.datetime.fromisoformat(end)
                - datetime.datetime.fromisoformat(start)).total_seconds()
    except (TypeError, ValueError):
        return None


def _platform(cwd):
    return "wsl" if (cwd or "").startswith("/") else "win"


def _lane(branch):
    for prefix in ("feat-", "design-", "light-"):
        if branch.startswith(prefix):
            return prefix[:-1]
    return "hub" if branch in ("master", "main", "HEAD") else "lab/other"


def _bash_action(command):
    whole = command.strip()
    bare = re.sub(r"^(cd [^&;]+(&&|;)\s*)+", "", whole)
    first = bare.split()[0] if bare.split() else ""
    if "harness.py validate" in whole or "harness.py doctor" in whole or "unittest" in whole:
        return "Bash: validate/doctor/tests"
    if re.search(r"\bharness\.py\b", whole):
        return "Bash: harness.py other"
    if first == "git" or " git " in bare[:40]:
        return "Bash: git"
    if ("claude --bg" in whole or "claude agents" in whole or "claude stop" in whole
            or first == "claude"):
        return "Bash: claude sessions"
    if first in ("cat", "sed", "head", "tail", "type", "Get-Content", "awk"):
        return "Bash: read file (cat/sed/head/tail/awk)"
    if first in ("grep", "rg", "find", "ls", "wc", "tree", "dir", "stat", "du", "for"):
        return "Bash: search/list"
    if first in ("python3", "python", "py"):
        return "Bash: python (edits/scripts)"
    return "Bash: other"


def _tool_action(block):
    name = block.get("name")
    if name == "Bash":
        return _bash_action(str((block.get("input") or {}).get("command", "")))
    if name == "Agent":
        return "Agent dispatch"
    return name


def usage_calls(records, since=None):
    calls = {}
    for record in records:
        message = record.get("message") if record.get("type") == "assistant" else None
        if not isinstance(message, dict):
            continue
        model = message.get("model")
        if not model or model == "<synthetic>":
            continue
        timestamp = record.get("timestamp") or ""
        if not _on_or_after(timestamp, since):
            continue
        key = message.get("id") or record.get("requestId") or record.get("uuid")
        call = calls.setdefault(key, {"usage": {}, "actions": []})
        call["usage"] = message.get("usage") or call["usage"]
        call.update(model=model, branch=record.get("gitBranch") or "?",
                    skill=record.get("attributionSkill") or "(none)", timestamp=timestamp,
                    cwd=record.get("cwd") or "")
        content = message.get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                call["actions"].append(_tool_action(block))
    return calls


def _agent_type(path):
    try:
        meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "?"
    return meta.get("agentType", "?") if isinstance(meta, dict) else "?"


def usage_session(path, since=None):
    records = _usage_records(path)
    cwd = first = version = cost = None
    pending = {}
    turns = []
    bash = []
    for record in records:
        if record.get("cwd") and cwd is None:
            cwd = record["cwd"]
        if record.get("version"):
            version = record["version"]
        timestamp = record.get("timestamp")
        if timestamp:
            first = first or timestamp
        kind = record.get("type")
        if kind == "cost-state":
            cost = record
        message = record.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        blocks = ([block for block in content if isinstance(block, dict)]
                  if isinstance(content, list) else [])
        if kind == "assistant":
            for block in blocks:
                if block.get("type") == "tool_use" and block.get("name") == "Bash":
                    pending[block.get("id")] = timestamp
        if kind == "user":
            for block in blocks:
                if block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    seconds = _seconds(pending.pop(block.get("tool_use_id")), timestamp)
                    if seconds is not None and seconds >= 0:
                        bash.append((_platform(cwd), seconds))
        if kind == "system" and record.get("subtype") == "turn_duration":
            turns.append((_platform(cwd), (record.get("durationMs") or 0) / 1000))
    subagents = []
    for sub in sorted((path.parent / path.stem / "subagents").glob("*.jsonl")):
        sub_records = _usage_records(sub)
        stamps = [record["timestamp"] for record in sub_records if record.get("timestamp")]
        subagents.append((_agent_type(sub), usage_calls(sub_records, since),
                          stamps[0] if stamps else None, stamps[-1] if stamps else None))
    return UsageSession(path.stem, usage_calls(records, since), cost, cwd, first, version,
                        turns, bash, subagents)


def _usage_weight(usage):
    return sum((usage.get(key) or 0) * weight for key, weight in USAGE_WEIGHTS.items())


def _context_size(usage):
    return ((usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0))


def _call_tokens(usage):
    return _context_size(usage) + (usage.get("output_tokens") or 0)


def _median(values):
    return statistics.median(values) if values else 0


def _at(values, fraction):
    return values[int(len(values) * fraction)] if values else 0


def _usage_keys(call):
    return (("branch", call["branch"]), ("lane", _lane(call["branch"])),
            ("day", call["timestamp"][:10]))


def usage_recount(sessions):
    tokens = defaultdict(Counter)
    units = defaultdict(float)
    model_units = Counter()
    cost_model = Counter()
    context = []
    calls_per_session = []
    skill_units = Counter()
    agent_tokens = defaultdict(Counter)
    agent_models = defaultdict(Counter)
    agent_runs = Counter()
    agent_units = defaultdict(float)
    platform_context = defaultdict(list)
    for session in sessions:
        for model, usage in ((session.cost or {}).get("modelUsage") or {}).items():
            cost_model[model] += usage.get("costUSD", 0) or 0
        if session.calls:
            calls_per_session.append(len(session.calls))
        for call in session.calls.values():
            usage, model = call["usage"], call["model"]
            for key in USAGE_WEIGHTS:
                tokens[("main", model)][key] += usage.get(key) or 0
            weight = _usage_weight(usage)
            model_units[model] += weight
            for kind, key in _usage_keys(call):
                units[(kind, key, model, "main")] += weight
            skill_units[call["skill"]] += weight
            size = _context_size(usage)
            context.append(size)
            platform_context[_platform(call["cwd"])].append(size)
        for agent, calls, _first, _last in session.subagents:
            agent_runs[agent] += 1
            for call in calls.values():
                usage, model = call["usage"], call["model"]
                for key in USAGE_WEIGHTS:
                    tokens[("sub", model)][key] += usage.get(key) or 0
                    agent_tokens[agent][key] += usage.get(key) or 0
                agent_tokens[agent]["calls"] += 1
                agent_models[agent][model] += 1
                weight = _usage_weight(usage)
                model_units[model] += weight
                agent_units[(agent, model)] += weight
                for kind, key in _usage_keys(call):
                    units[(kind, key, model, "sub")] += weight
    price = {model: (cost_model.get(model, 0) / weight if weight else 0)
             for model, weight in model_units.items()}
    lines = ["CORRECTED ACCOUNTING (one call per message.id). Cost-state USD by model:"]
    for model, usd in cost_model.most_common():
        lines.append(f"  {model:30s} ${usd:8.1f}")
    lines.append(f"  TOTAL ${sum(cost_model.values()):.1f}\n")
    lines.append("TOKENS BY SIDE/MODEL (M): in / cache-create / cache-read / out ; apportioned USD")
    side_usd = Counter()
    for (side, model), counts in sorted(tokens.items()):
        usd = _usage_weight(counts) * price.get(model, 0)
        side_usd[side] += usd
        lines.append(f"  {side:4s} {model:28s} {counts['input_tokens']/1e6:7.1f} "
                     f"{counts['cache_creation_input_tokens']/1e6:8.1f} "
                     f"{counts['cache_read_input_tokens']/1e6:9.1f} "
                     f"{counts['output_tokens']/1e6:7.2f}  ${usd:7.0f}")
    lines.append(f"  => main ${side_usd['main']:.0f}   sub ${side_usd['sub']:.0f}\n")
    context.sort()
    calls_per_session.sort()
    lines.append(f"MAIN CONTEXT PER CALL: calls={len(context)} median={_median(context):.0f} "
                 f"p75={_at(context, .75)} p90={_at(context, .9)} "
                 f"max={context[-1] if context else 0}")
    for platform, sizes in platform_context.items():
        lines.append(f"  {platform}: median={_median(sizes):.0f} n={len(sizes)}")
    lines.append(f"MAIN CALLS PER SESSION: median={_median(calls_per_session):.0f} "
                 f"p90={_at(calls_per_session, .9)} "
                 f"max={calls_per_session[-1] if calls_per_session else 0}\n")
    skill_total = sum(skill_units.values()) or 1
    lines.append("MAIN-THREAD SHARE BY ATTRIBUTED SKILL:")
    for skill, weight in skill_units.most_common(12):
        lines.append(f"  {skill:26s} {weight/skill_total*100:5.1f}%")
    lines.append("\nSUBAGENTS BY TYPE: runs, calls, cache-read M, cache-create M, out M, "
                 "est USD, models")
    rows = []
    for agent, counts in agent_tokens.items():
        usd = sum(weight * price.get(model, 0)
                  for (name, model), weight in agent_units.items() if name == agent)
        rows.append((usd, agent, counts))
    for usd, agent, counts in sorted(rows, key=lambda row: (row[0], row[1]), reverse=True):
        lines.append(f"  {agent:20s} runs={agent_runs[agent]:4d} calls={counts['calls']:6d} "
                     f"cr={counts['cache_read_input_tokens']/1e6:7.1f} "
                     f"cc={counts['cache_creation_input_tokens']/1e6:6.1f} "
                     f"out={counts['output_tokens']/1e6:5.2f} ${usd:6.0f} "
                     f"${usd/max(1, agent_runs[agent]):5.2f}/run "
                     f"{dict(agent_models[agent].most_common(3))}")
    spend = defaultdict(lambda: [0.0, 0.0])
    for (kind, key, model, side), weight in units.items():
        spend[(kind, key)][0 if side == "main" else 1] += weight * price.get(model, 0)
    for kind in ("lane", "day", "branch"):
        lines.append(f"\nUSD BY {kind.upper()} (main, sub, total)")
        rows = sorted(((main + sub, key[1], main, sub) for key, (main, sub) in spend.items()
                       if key[0] == kind),
                      key=lambda row: (row[1] if kind == "day" else -row[0]))
        for total, key, main, sub in rows:
            if total >= 1:
                lines.append(f"  {key:44s} ${main:7.0f} ${sub:7.0f} ${total:7.0f}")
    return lines


def _usage_add(counts, usage):
    counts["ctx"] += _context_size(usage)
    counts["cr"] += usage.get("cache_read_input_tokens") or 0
    counts["cw"] += usage.get("cache_creation_input_tokens") or 0
    counts["out"] += usage.get("output_tokens") or 0
    counts["calls"] += 1


def usage_tokens_by(sessions):
    by = defaultdict(Counter)
    sessions_by_branch = defaultdict(set)
    runs_by_agent = Counter()
    for session in sessions:
        for call in session.calls.values():
            era = _platform(call["cwd"])
            branch = call["branch"]
            for key in (("side", "main"), ("lane", _lane(branch)), ("branch", branch),
                        ("skill", call["skill"]), ("era", era + ":main"),
                        ("model", "main:" + call["model"])):
                _usage_add(by[key], call["usage"])
            sessions_by_branch[branch].add(session.sid)
        for agent, calls, _first, _last in session.subagents:
            runs_by_agent[agent] += 1
            for call in calls.values():
                era = _platform(call["cwd"])
                branch = call["branch"]
                for key in (("side", "sub"), ("lane", _lane(branch)), ("branch", branch),
                            ("agent", agent), ("era", era + ":sub"),
                            ("model", "sub:" + call["model"]), ("branch_sub", branch)):
                    _usage_add(by[key], call["usage"])
    lines = []

    def table(kind, title, width=44, extra=None, limit=None):
        lines.append(f"\n== {title}")
        rows = [(key[1], counts) for key, counts in by.items() if key[0] == kind]
        rows.sort(key=lambda row: -(row[1]["ctx"] + row[1]["out"]))
        total = sum(counts["ctx"] + counts["out"] for _name, counts in rows) or 1
        for name, counts in rows[:limit]:
            tokens = counts["ctx"] + counts["out"]
            tail = extra(name, counts) if extra else ""
            lines.append(f"  {name:{width}s} total={tokens/1e6:9.1f}M ({tokens/total*100:5.1f}%) "
                         f"ctx/call={counts['ctx']/max(1, counts['calls'])/1e3:6.1f}k "
                         f"calls={counts['calls']:6d} cache-write={counts['cw']/1e6:7.1f}M "
                         f"out={counts['out']/1e6:6.2f}M {tail}")

    sides = [by[("side", side)] for side in ("main", "sub")]
    grand = sum(counts["ctx"] + counts["out"] for counts in sides)
    lines.append(f"GRAND TOTAL tokens processed (input+cache-read+cache-write+output): "
                 f"{grand/1e9:.2f}B")
    lines.append(f"  (cache-read share: {100 * sum(c['cr'] for c in sides) / (grand or 1):.1f}%; "
                 f"output share: {100 * sum(c['out'] for c in sides) / (grand or 1):.2f}%)")
    table("side", "MAIN THREAD vs SUBAGENTS", width=8)
    table("model", "BY SIDE:MODEL", width=30)
    table("era", "BY PLATFORM ERA", width=10)
    table("lane", "BY LANE", width=10)
    table("agent", "SUBAGENTS BY TYPE", width=20,
          extra=lambda name, counts: (
              f"runs={runs_by_agent[name]} per-run="
              f"{(counts['ctx'] + counts['out'])/max(1, runs_by_agent[name])/1e6:5.2f}M"))
    table("skill", "MAIN THREAD BY ATTRIBUTED SKILL", width=26, limit=16)

    def branch_extra(name, counts):
        sub = by[("branch_sub", name)]
        share = (sub["ctx"] + sub["out"]) / max(1, counts["ctx"] + counts["out"]) * 100
        return f"sessions={len(sessions_by_branch.get(name, ()))} sub-share={share:4.0f}%"

    table("branch", "BY BRANCH (main+sub)", extra=branch_extra)
    return lines


def usage_main_calls(sessions):
    categories = defaultdict(Counter)
    for session in sessions:
        for call in session.calls.values():
            actions = call["actions"]
            if not actions:
                key = "(text only: answer, report to human, end of turn)"
            elif len(set(actions)) == 1:
                key = actions[0]
            else:
                key = "multi: " + "+".join(sorted(set(actions)))[:60]
            categories[key]["calls"] += 1
            categories[key]["tok"] += _call_tokens(call["usage"])
    total = sum(counts["tok"] for counts in categories.values())
    count = sum(counts["calls"] for counts in categories.values())
    lines = [f"MAIN-THREAD API CALLS BY ACTION (deduped): calls={count} tokens={total/1e9:.2f}B"]
    for key, counts in sorted(categories.items(), key=lambda item: -item[1]["tok"])[:30]:
        lines.append(f"  {key:62s} calls={counts['calls']:6d} "
                     f"({counts['calls']/(count or 1)*100:4.1f}%) "
                     f"tokens={counts['tok']/1e6:8.1f}M ({counts['tok']/(total or 1)*100:4.1f}%)")
    return lines


def usage_platform_split(sessions):
    durations = defaultdict(lambda: defaultdict(list))
    turns = defaultdict(list)
    tool_share = defaultdict(list)
    bash = defaultdict(list)
    starts = []
    for session in sessions:
        platform = _platform(session.cwd)
        for where, seconds in session.turns:
            turns[where].append(seconds)
        for where, seconds in session.bash:
            bash[where].append(seconds)
        if session.cost:
            api = session.cost.get("totalAPIDuration") or 0
            tool = session.cost.get("totalToolDuration") or 0
            if api + tool:
                tool_share[platform].append(tool / (api + tool))
        starts.append((session.first or "", platform, session.cwd, session.version, session.sid))
        for agent, _calls, first, last in session.subagents:
            seconds = _seconds(first, last) if first and last else None
            if seconds is not None:
                durations[platform][agent].append(seconds)
    starts.sort(key=lambda start: (start[0], start[1], start[4]))
    lines = ["SESSIONS BY PLATFORM (first/last start):"]
    for platform in ("wsl", "win"):
        chosen = [start for start in starts if start[1] == platform]
        if chosen:
            cwds = sorted({start[2] or "" for start in chosen})[:3]
            versions = sorted({start[3] or "" for start in chosen})
            lines.append(f"  {platform}: n={len(chosen)} first={chosen[0][0]} "
                         f"last={chosen[-1][0]} cwd-examples={cwds} "
                         f"versions={versions[:2]}..{versions[-1:]}")
    lines.append("\nTRANSITION (sessions ordered by start, platform changes):")
    previous = None
    for first, platform, cwd, version, sid in starts:
        if platform != previous:
            lines.append(" ".join(["  ", first, platform, str(cwd), str(version), sid[:8]]))
            previous = platform
    lines.append("\nTURN DURATION s (median / p90 / n):")
    for platform, values in turns.items():
        values.sort()
        lines.append(f"  {platform}: {_median(values):.0f} / {_at(values, .9):.0f} / {len(values)}")
    lines.append("\nTOOL-TIME SHARE of (API+tool) per session (median):")
    for platform, values in tool_share.items():
        lines.append(f"  {platform}: {_median(values):.2f} n={len(values)}")
    lines.append("\nMAIN-THREAD BASH round-trip s (median / p90 / n):")
    for platform, values in bash.items():
        values.sort()
        lines.append(f"  {platform}: {_median(values):.1f} / {_at(values, .9):.1f} / {len(values)}")
    lines.append("\nSUBAGENT DURATION s by type (median wsl -> win; n):")
    for agent in sorted(set(durations["wsl"]) | set(durations["win"])):
        wsl = sorted(durations["wsl"].get(agent, []))
        win = sorted(durations["win"].get(agent, []))
        before = statistics.median(wsl) if wsl else float("nan")
        after = statistics.median(win) if win else float("nan")
        lines.append(f"  {agent:20s} {before:7.0f} -> {after:7.0f}   (n {len(wsl)} -> {len(win)})")
    return lines


def usage_report(directory, root, since):
    paths = usage_transcripts(directory, root)
    if not paths:
        print(f"usage_report: no transcripts found under {directory} for {project_slug(root)}")
        return 0
    sessions = [usage_session(path, since) for path in paths]
    calls = [call for session in sessions for call in session.calls.values()]
    calls += [call for session in sessions for _agent, sub_calls, _first, _last
              in session.subagents for call in sub_calls.values()]
    subagents = sum(len(session.subagents) for session in sessions)
    print(f"usage_report: {len(sessions)} main and {subagents} subagent transcripts under "
          f"{directory} for {project_slug(root)}; {len(calls)} calls, "
          f"{sum(_call_tokens(call['usage']) for call in calls)} tokens")
    for name, section in (("recount", usage_recount), ("tokens_by", usage_tokens_by),
                          ("main_calls", usage_main_calls),
                          ("platform_split", usage_platform_split)):
        print(f"\n--- {name} ---")
        print("\n".join(section(sessions)))
    return 0


def format_row(row, warn=False):
    line = f"{row.code}  {row.path}  {row.message}"
    return f"warn  {line}" if warn else line


def print_report(banners, failures, warnings, verb):
    for banner in banners:
        print(banner)
    for row in failures:
        print(format_row(row))
    for row in warnings:
        print(format_row(row, warn=True))
    print(f"{verb}: FAIL" if failures else f"{verb}: PASS")
    return 1 if failures else 0


def _directory(value):
    path = Path(value).resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {value}")
    return path


def _target(value):
    path = Path(value).resolve()
    if not path.parent.is_dir():
        raise argparse.ArgumentTypeError(f"parent directory does not exist: {value}")
    return path


def _date(value):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value}") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="harness.py",
        description="The base repo's thirteen commands, list, validate, scaffold, add, doctor, "
                    "upgrade, promote, outline, usage_report, budget, bounds, close-class and "
                    "automode. "
                    "List and validate a harness base, scaffold a project from it, "
                    "add packs, check a project with doctor, plan its upgrade, "
                    "promote one local project file into a pack of the base, outline a "
                    "Markdown file, report token usage from the project's transcripts, "
                    "report a project's budget items for a gate, check a light-lane "
                    "changeset against its class's bounds, resolve a light-lane close's "
                    "class from its evidence, and compose a workspace's "
                    "autoMode entries, print their diff against the user settings and, "
                    "with --apply, write them there.")
    commands = parser.add_subparsers(dest="command", required=True)
    lister = commands.add_parser(
        "list", help="print the base's packs and presets",
        description="list [--json] prints the packs and presets a base holds (design §7.1).")
    lister.add_argument("--json", action="store_true", help="print the JSON payload instead")
    lister.add_argument("--root", type=_directory, default=DEFAULT_ROOT,
                        help="the base to read (default: the base this script sits in)")
    validator = commands.add_parser(
        "validate", help="run the base's self-validation rows",
        description="validate runs the self-validation rows of design §5.6 over a base or a "
                    "project and exits 0 only when no row fails.")
    validator.add_argument("--root", type=_directory, default=DEFAULT_ROOT,
                           help="the base to read (default: the base this script sits in)")
    scaffolder = commands.add_parser(
        "scaffold", help="write a new project from the base's packs",
        description="scaffold writes a new project from the base's packs; it reads the base, "
                    "writes only inside its target, and shells out to nothing.")
    scaffolder.add_argument("target", type=_target, help="the project directory to write")
    scaffolder.add_argument("--packs", default="", help="comma-separated pack names")
    scaffolder.add_argument("--preset", default=None, help="a preset in the base, by name")
    child = scaffolder.add_mutually_exclusive_group()
    child.add_argument("--parent", type=_directory, default=None,
                       help="an existing project this one is a child of")
    child.add_argument("--rewrite-managed-block", action="store_true",
                       help="rewrite only the CLAUDE.md managed block of an existing project")
    child.add_argument("--adopt", action="store_true",
                       help="write what is absent into a target that already has content")
    scaffolder.add_argument("--base", type=_directory, default=DEFAULT_ROOT,
                            help="the base to read (default: the base this script sits in)")
    adder = commands.add_parser(
        "add", help="compose one more pack into an existing project",
        description="add composes one more pack into an existing project; it reads the base, "
                    "writes only inside its target, and shells out to nothing.")
    adder.add_argument("pack", help="the pack to add, by name")
    adder.add_argument("--root", type=_directory, default=Path.cwd(),
                       help="the project to grow (default: the current working directory)")
    checker = commands.add_parser(
        "doctor", help="report a project's drift, local items and broken state; writes nothing",
        description="doctor [--all] reads a project against its base, or with --all a workspace "
                    "root and its immediate children, reports drift, local items and broken "
                    "state, writes nothing, and exits 1 only for a broken project.")
    checker.add_argument("--root", type=_directory, default=Path.cwd(),
                         help="the project to check, or the workspace root with --all "
                              "(default: the current working directory)")
    checker.add_argument("--all", action="store_true",
                         help="check the root and each immediate child directory holding "
                              ".claude/harness.json")
    upgrader = commands.add_parser(
        "upgrade",
        help="plan a project's upgrade against its base, report it, and apply the plan",
        description="upgrade [--dry-run] [--all] plans a project against its base, reports one "
                    "outcome per file, and applies it unless --dry-run or --all.")
    upgrader.add_argument("--root", type=_directory, default=Path.cwd(),
                          help="the project to upgrade, or the workspace root with --all "
                               "(default: the current working directory)")
    upgrader.add_argument("--dry-run", action="store_true",
                          help="plan and report, writing nothing")
    picked = upgrader.add_mutually_exclusive_group()
    picked.add_argument("--take-theirs", default=None, metavar="FILE",
                        help="a project-relative ledgered file to replace even though it is "
                             "locally modified")
    picked.add_argument("--all", action="store_true",
                        help="dry-run the root and each immediate child directory holding "
                             ".claude/harness.json")
    promoter = commands.add_parser(
        "promote", help="copy one local project file into a pack of the base",
        description="promote PATH copies one local project file the other way — into a pack of "
                    "the base, editing that pack's provides list, and writing a new pack's stub "
                    "under --new-pack NAME --kind KIND.")
    promoter.add_argument("path", help="the project-relative file to promote")
    promoter.add_argument("--root", type=_directory, default=Path.cwd(),
                          help="the project to promote from "
                               "(default: the current working directory)")
    into = promoter.add_mutually_exclusive_group(required=True)
    into.add_argument("--to", default=None, metavar="PACK",
                      help="a pack of the base to promote into, by name")
    into.add_argument("--new-pack", default=None, metavar="NAME",
                      help="a new pack of the base to create for it, with --kind")
    promoter.add_argument("--kind", default=None, metavar="KIND",
                          help="the new pack's kind, with --new-pack: "
                               + ", ".join(PACK_KINDS))
    outliner = commands.add_parser(
        "outline", help="print a Markdown file's headings with their line numbers",
        description="outline FILE prints a Markdown file's headings with their line numbers. "
                    "It only reads.")
    outliner.add_argument("file", help="the Markdown file to read")
    reporter = commands.add_parser(
        "usage_report",
        help="print token accounting from the project's Claude Code transcripts; writes nothing",
        description="usage_report prints token accounting from the project's Claude Code "
                    "transcripts, one API call per message.id. It only reads.")
    reporter.add_argument("--dir", type=Path, default=Path.home() / ".claude" / "projects",
                          help="the transcripts root (default: ~/.claude/projects)")
    reporter.add_argument("--since", type=_date, default=None, metavar="YYYY-MM-DD",
                          help="only calls on or after this UTC date")
    reporter.add_argument("--root", type=_target, default=Path.cwd(),
                          help="the project whose transcripts to read "
                               "(default: the current working directory)")
    budgeter = commands.add_parser(
        "budget", help="report budget items for a gate; writes nothing",
        description="budget [--hub DIR] [--feature NAME] reports a project's budget items for a "
                    "gate — STATUS, and with --feature that feature's architecture-doc body and "
                    "plan files — one line each, then budget: PASS or budget: FAIL; it exits 1 "
                    "on a FAIL and only reads.")
    budgeter.add_argument("--root", type=_directory, default=Path.cwd(),
                          help="the project to check (default: the current working directory)")
    budgeter.add_argument("--hub", type=_directory, default=None,
                          help="the hub whose memory/STATUS.md is checked (default: --root)")
    budgeter.add_argument("--feature", default=None, metavar="NAME",
                          help="the feature whose architecture-doc body and plan files are "
                               "also checked")
    bounder = commands.add_parser(
        "bounds", help="check a light-lane changeset against its class's bounds; writes nothing",
        description="bounds [--class CLASS] [--numstat FILE] [--item ID] checks a saved diff "
                    "read against the class's classes bounds; it exits 1 on a FAIL and only "
                    "reads.")
    bounder.add_argument("--root", type=_directory, default=Path.cwd(),
                         help="the project to check (default: the current working directory)")
    bounder.add_argument("--class", dest="declared", default="slim", metavar="CLASS",
                         help="the class the work declared: slim, prose or trivial "
                              "(default: slim)")
    bounder.add_argument("--numstat", default=None, metavar="FILE",
                         help="the saved per-file line-count read of the changeset; prose and "
                              "trivial need it")
    bounder.add_argument("--item", action="append", dest="items", metavar="ID",
                         help="one batch item's id; repeat it once per item")
    closer = commands.add_parser(
        "close-class",
        help="resolve a light-lane close to delegated, audited or human from its evidence; "
             "writes nothing",
        description="close-class [--class CLASS] [--numstat FILE] [--item ID] [--branch NAME] "
                    "[--status FILE] [--brief FILE] [--review READING] [--preflight READING] "
                    "[--slot] resolves a light-lane close to delegated, audited or human from "
                    "its evidence against the classes Delegated classes slot, or with --slot "
                    "reads that slot alone; it exits 1 only on a refusal and only reads.")
    closer.add_argument("--root", type=_directory, default=Path.cwd(),
                        help="the project to check (default: the current working directory)")
    closer.add_argument("--class", dest="declared", default="slim", metavar="CLASS",
                        help="the class the work declared: slim, prose or trivial "
                             "(default: slim)")
    closer.add_argument("--numstat", default=None, metavar="FILE",
                        help="the per-file line-count read saved at the closing head")
    closer.add_argument("--item", action="append", dest="items", metavar="ID",
                        help="one batch item's id; repeat it once per item")
    closer.add_argument("--branch", default=None, metavar="NAME",
                        help="the branch whose block the STATUS file holds")
    closer.add_argument("--status", default=None, metavar="FILE",
                        help="the STATUS file holding the branch's block under ## Current")
    closer.add_argument("--brief", default=None, metavar="FILE",
                        help="the launch brief whose ## Lane declares the batch")
    closer.add_argument("--review", default=None, metavar="READING",
                        help="the PM's reading of the review at the closing head: clean or open")
    closer.add_argument("--preflight", default=None, metavar="READING",
                        help="the PM's reading of PREFLIGHT: PASS")
    closer.add_argument("--slot", action="store_true",
                        help="print only the Delegated classes slot's reading")
    composer = commands.add_parser(
        "automode",
        help="compose a workspace's autoMode entries and print their diff against the user "
             "settings",
        description="automode [--root DIR] [--apply] composes the autoMode entries of the packs "
                    "a workspace's named projects compose, each placeholder filled from that "
                    "project's bindings and the root, and prints them with their diff against "
                    "the user settings; --apply, the human's run, refused in a Claude Code "
                    "shell, writes them there whole.")
    composer.add_argument("--root", type=_directory, default=Path.cwd().resolve(),
                          help="the workspace root, scanned as doctor --all scans it "
                               "(default: the current working directory)")
    composer.add_argument("--apply", action="store_true",
                          help="write the composed entries into the user settings, whole — the "
                               "human's run; refused in a Claude Code shell")
    args = parser.parse_args(argv)

    if args.command == "list":
        payload = list_packs(args.root)
        if not payload["packs"]:
            print(f"list: no pack found under {args.root}", file=sys.stderr)
            return 1
        print(render_list_json(payload) if args.json else render_list_text(payload))
        return 0

    if args.command == "scaffold":
        return scaffold(args.target, args.base, args.packs, args.preset,
                        args.rewrite_managed_block, args.parent, args.adopt)

    if args.command == "add":
        return add(args.pack, args.root)

    if args.command == "doctor":
        return doctor_all(args.root) if args.all else doctor(args.root)

    if args.command == "upgrade":
        return (upgrade_all(args.root) if args.all
                else upgrade(args.root, args.dry_run, args.take_theirs))

    if args.command == "promote":
        return promote(args.path, args.root, args.to, args.new_pack, args.kind)

    if args.command == "outline":
        return outline(args.file)

    if args.command == "usage_report":
        return usage_report(args.dir, args.root, args.since)

    if args.command == "budget":
        return budget(args.root, args.hub, args.feature)

    if args.command == "bounds":
        return bounds(args.root, args.declared, args.numstat, args.items or [])

    if args.command == "close-class":
        return close_class(args.root, args.declared, args.numstat, args.items or [],
                           args.branch, args.status, args.brief, args.review, args.preflight,
                           args.slot)

    if args.command == "automode":
        return automode(args.root, args.apply)

    failures, warnings, banners = validate_report(args.root)
    return print_report(banners, failures, warnings, "validate")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
