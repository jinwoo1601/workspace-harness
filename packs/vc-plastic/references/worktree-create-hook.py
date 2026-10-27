# =============================================================================
# Purpose:  WorktreeCreate hook cutting a parallel writer's workspace per the trees binding
# Layer:    Hooks
# Owns:     (script, no public types)
# Depends:  (none)
# =============================================================================

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BINDINGS_REL = ".claude/bindings/vc-plastic.md"
PREFIX = "worktree-create-hook: "
NOT_AN_OBJECT = "the input on stdin is not a JSON object"
SESSION = ("session worktree requests are refused: open a plain claude session in a "
           "branch tree cut by the Create procedure of ## trees in "
           ".claude/bindings/vc-plastic.md")
NO_CWD = "input key cwd is missing or names no directory"
NO_NAME = "input key name is missing or not a plain name"
ABSENT = ("## trees in .claude/bindings/vc-plastic.md reads absent ({form}); writer trees "
          "are refused until it is filled")
NO_LOCATION = ("## trees slot Location needs a backticked absolute Windows-form path holding "
               "both <branch> and <unit>")
NO_NAMING = ("## trees slot Writer-branch naming needs a backticked child name beginning "
             "<branch>/ and holding <unit>, with no further /")
NO_CM = "cm is not on PATH; nothing was made"
WI_FAILED = "cm wi in {cwd} exited {code}: {message}"
NO_BRANCH = ("the dispatching workspace {cwd} is on no branch; a writer workspace is cut "
             "from a branch's head")
PATH_EXISTS = "the writer workspace path {path} already exists"
BRANCH_EXISTS = "the writer branch {branch} already exists"
FIND_FAILED = "cm find branch in {cwd} exited {code}: {message}"
CUT_FAILED = "the cut failed: cm {command} exited {code}: {message}"


class Refused(Exception):
    pass


class CutFailed(Exception):
    pass


def resolve_root(argv):
    if len(argv) > 1:
        candidate = Path(argv[1])
        if candidate.is_dir():
            return candidate
    return Path.cwd()


def parse_payload(data):
    try:
        document = json.loads(data)
    except (ValueError, RecursionError):
        return None
    return document if isinstance(document, dict) else None


def is_plain_name(value):
    if not isinstance(value, str) or not value:
        return False
    if "/" in value or "\\" in value or ":" in value:
        return False
    return value.strip(".") != ""


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
    path = root / BINDINGS_REL
    if not path.is_file():
        return "missing", None
    lines = trees_section(path.read_text(encoding="utf-8"))
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


def slot_token(lines, label):
    for line in lines:
        if line.lstrip().startswith(f"- {label}:"):
            for token in re.findall(r"`([^`]+)`", line):
                if "<branch>" in token and "<unit>" in token:
                    return token
            return None
    return None


def cm(cwd, *args):
    return subprocess.run([shutil.which("cm"), *args], cwd=cwd, stdin=subprocess.DEVNULL,
                          capture_output=True, encoding="utf-8", errors="replace")


def said(result):
    for stream in (result.stderr, result.stdout):
        lines = [line.strip() for line in stream.splitlines() if line.strip()]
        if lines:
            return " ".join(lines)
    return "no message"


def find_branch(cwd, writer_branch):
    leaf = writer_branch.rsplit("/", 1)[-1]
    found = cm(cwd, "find", "branch", f"where name='{leaf}'", "--nototal", "--format={name}")
    return found, writer_branch in [line.strip() for line in found.stdout.splitlines()]


def plan_writer(payload, root):
    prompt_id = payload.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise Refused(SESSION)
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd or not Path(cwd).is_dir():
        raise Refused(NO_CWD)
    name = payload.get("name")
    if not is_plain_name(name):
        raise Refused(NO_NAME)
    form, lines = absent_form(root)
    if form is not None:
        raise Refused(ABSENT.format(form=form))
    location = slot_token(lines, "Location")
    if location is None or not re.match(r"^[A-Za-z]:[\\/]", location):
        raise Refused(NO_LOCATION)
    naming = slot_token(lines, "Writer-branch naming")
    if (naming is None or not naming.startswith("<branch>/")
            or "/" in naming[len("<branch>/"):]):
        raise Refused(NO_NAMING)
    if shutil.which("cm") is None:
        raise CutFailed(NO_CM)
    read = cm(cwd, "wi")
    if read.returncode != 0:
        raise CutFailed(WI_FAILED.format(cwd=cwd, code=read.returncode,
                                         message=said(read)))
    selector = next((line.strip() for line in read.stdout.splitlines()
                     if line.strip().startswith("Branch ")), "")
    full, _, repository = selector[len("Branch "):].partition("@")
    if not full or not repository:
        raise Refused(NO_BRANCH.format(cwd=cwd))
    branch = full.rsplit("/", 1)[-1]
    path = location.replace("<branch>", branch).replace("<unit>", name).replace("/", "\\")
    suffix = naming[len("<branch>"):].replace("<branch>", branch).replace("<unit>", name)
    writer_branch = full + suffix
    workspace = path.rsplit("\\", 1)[-1]
    if os.path.lexists(path):
        raise Refused(PATH_EXISTS.format(path=path))
    found, listed = find_branch(cwd, writer_branch)
    if found.returncode != 0:
        raise CutFailed(FIND_FAILED.format(cwd=cwd, code=found.returncode,
                                           message=said(found)))
    if listed:
        raise Refused(BRANCH_EXISTS.format(branch=writer_branch))
    return cwd, repository, path, workspace, writer_branch


def cut(cwd, repository, path, workspace, writer_branch):
    steps = (("branch create", cwd, ("branch", "create", "br:" + writer_branch)),
             ("workspace create", cwd,
              ("workspace", "create", workspace, path, "rep:" + repository)),
             ("switch", path, ("switch", "br:" + writer_branch)))
    ran = []
    for command, directory, args in steps:
        ran.append(command)
        done = cm(directory, *args)
        if done.returncode != 0:
            break
    if done.returncode == 0:
        return
    if "workspace create" in ran:
        cm(cwd, "workspace", "delete", path)
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    if find_branch(cwd, writer_branch)[1]:
        cm(cwd, "branch", "delete", "br:" + writer_branch)
    text = CUT_FAILED.format(command=command, code=done.returncode, message=said(done))
    remains = []
    if os.path.lexists(path):
        remains.append(path)
    if find_branch(cwd, writer_branch)[1]:
        remains.append(writer_branch)
    if remains:
        text += "; left behind: " + ", ".join(remains)
    raise CutFailed(text)


def main(argv):
    try:
        payload = parse_payload(sys.stdin.buffer.read())
        if payload is None:
            raise Refused(NOT_AN_OBJECT)
        cwd, repository, path, workspace, writer_branch = plan_writer(
            payload, resolve_root(argv))
        cut(cwd, repository, path, workspace, writer_branch)
    except Refused as refusal:
        print(PREFIX + str(refusal), file=sys.stderr)
        return 2
    except CutFailed as failure:
        print(PREFIX + str(failure), file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
