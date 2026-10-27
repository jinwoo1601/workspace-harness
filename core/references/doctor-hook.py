# =============================================================================
# Purpose:  SessionStart hook relaying `harness.py doctor`'s report into a session
# Layer:    Hooks
# Owns:     (script, no public types)
# Depends:  (none)
# =============================================================================

import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_REL = ".claude/harness.json"
BINDINGS_REL = ".claude/bindings"
WAIT_SECONDS = 10
LIST_WAIT_SECONDS = 5
HUB_CHECKOUT = re.compile(r"the main checkout is `([^`]+)`")


def resolve_root(argv):
    if len(argv) > 1:
        candidate = Path(argv[1])
        if candidate.is_dir():
            return candidate
    return Path.cwd()


def trees_section(root, filler):
    named = filler.get("trees", "core")
    if not (isinstance(named, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", named)
            and ".." not in named):
        named = "core"
    path = root / BINDINGS_REL / f"{named}.md"
    return binding_section(path.read_text(encoding="utf-8"), "trees") if path.is_file() else None


def trees_hub(lines):
    line = next((line for line in lines or [] if line.startswith("- Hub:")), None)
    match = HUB_CHECKOUT.search(line) if line else None
    return match.group(1) if match else None


def harness_script(root):
    manifest = root / MANIFEST_REL
    if not manifest.is_file():
        return None
    try:
        document = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None
    base = document.get("base") if isinstance(document, dict) else None
    if not isinstance(base, str) or not base:
        return None
    base_dir = (root / base).resolve()
    if not base_dir.is_dir():
        filler = document.get("bindings")
        filler = filler if isinstance(filler, dict) else {}
        try:
            hub = trees_hub(trees_section(root, filler))
        except (OSError, UnicodeDecodeError):
            hub = None
        if hub is not None:
            candidate = (Path(hub) / base).resolve()
            if candidate.is_dir():
                base_dir = candidate
    script = base_dir / "scripts/harness.py"
    return script if script.is_file() else None


def doctor_stdout(root, script):
    try:
        result = subprocess.run([sys.executable, str(script), "doctor", "--root", str(root)],
                                cwd=str(root), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=WAIT_SECONDS)
    except (subprocess.TimeoutExpired, OSError):
        return b""
    return result.stdout


def binding_section(text, key):
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


def slot_value(lines, label):
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"- {label}:"):
            text = stripped[len(f"- {label}:"):].strip()
            if text.lower().startswith(("todo", "none")):
                return None
            match = re.search(r"`([^`]+)`", text)
            return match.group(1) if match else None
    return None


def hub_warning(root):
    try:
        for path in sorted((root / BINDINGS_REL).glob("*.md")):
            lines = binding_section(path.read_text(encoding="utf-8"), "session-launch")
            if lines is not None:
                break
        else:
            return None
        command = slot_value(lines, "List command")
        if command is None:
            return None
        where = path.relative_to(root).as_posix()
        name = slot_value(lines, "Hub session name")
        if name is None:
            return f"warn  HUB  {where}  Hub session name unbound while the List command is bound"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=LIST_WAIT_SECONDS)
        if result.returncode != 0:
            return None
        sessions = json.loads(result.stdout)
        if not isinstance(sessions, list):
            return None
        count = sum(1 for session in sessions
                    if isinstance(session, dict) and session.get("name") == name)
        if count < 2:
            return None
        return f"warn  HUB  {where}  {count} running sessions named {name}"
    except Exception:
        return None


def before_last_line(report, line):
    start = report.rstrip(b"\r\n").rfind(b"\n") + 1
    ending = b"\r\n" if b"\r\n" in report else b"\n"
    return report[:start] + line.encode("utf-8") + ending + report[start:]


def main(argv):
    try:
        root = resolve_root(argv)
        script = harness_script(root)
        if script is not None:
            report = doctor_stdout(root, script)
            if report:
                warning = hub_warning(root)
                if warning is not None:
                    report = before_last_line(report, warning)
                sys.stdout.buffer.write(report)
                sys.stdout.buffer.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
