# =============================================================================
# Purpose:  PreToolUse guard refusing a subagent's cm command that changes version-control state
# Layer:    Hooks
# Owns:     (script, no public types)
# Depends:  (none)
# =============================================================================

import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

PUNCTUATION = "();<>|&\n"
REDIRECTS = frozenset(("<", ">", ">>", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|", "<>"))
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = frozenset(("command", "exec", "time", "nohup", "then", "do", "else", "!"))
ENV_VALUED = frozenset(("-u", "--unset", "-C", "--chdir", "-S", "--split-string"))
XARGS_VALUED = frozenset(("-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s"))
SUDO_VALUED = frozenset(("-u", "--user", "-g", "--group", "-C", "--close-from", "-D", "--chdir",
                         "-h", "--host", "-p", "--prompt", "-r", "--role", "-t", "--type",
                         "-U", "--other-user", "-T", "--command-timeout", "-R", "--chroot"))
UNRESOLVED = "an unresolved directory"
REASON = ("vc-guard: subagents never change version-control state (cm {verb} in {tree}); "
          "report the need to the PM — read forms such as cm status, find, log, diff and "
          "wk list stay allowed.")
READ_VERBS = frozenset((
    "status", "find", "log", "diff", "ls", "cat", "wi", "workspaceinfo", "whoami", "version",
    "getstatus", "lrep", "lwk", "showowner", "showselector", "annotate", "help", "history"))
LIST_OBJECTS = frozenset(("workspace", "wk", "branch", "label", "lock"))


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


def tokenize(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace_split = True
    lexer.escape = ""
    lexer.commenters = ""
    lexer.whitespace = lexer.whitespace.replace("\n", "")
    try:
        return list(lexer)
    except ValueError:
        tokens = []
        for line in command.split("\n"):
            tokens.extend(line.split())
            tokens.append("\n")
        return tokens


def is_break(token):
    if token in ("{", "}"):
        return True
    return (bool(token) and all(character in PUNCTUATION for character in token)
            and token not in REDIRECTS)


def split_segments(tokens):
    segments = [[]]
    for token in tokens:
        if is_break(token):
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def command_name(token):
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name[:-len(".exe")] if name.endswith(".exe") else name


def command_start(segment):
    index = 0
    while index < len(segment):
        token = segment[index]
        if ASSIGNMENT.match(token):
            index += 1
            continue
        name = command_name(token)
        if token in WRAPPERS:
            valued = frozenset()
        elif name == "env":
            valued = ENV_VALUED
        elif name == "xargs":
            valued = XARGS_VALUED
        elif name == "sudo":
            valued = SUDO_VALUED
        else:
            break
        index += 1
        while index < len(segment) and (segment[index].startswith("-")
                                        or (name == "env" and ASSIGNMENT.match(segment[index]))):
            index += 2 if segment[index] in valued else 1
    return index


def to_path(text, base):
    if os.name != "nt":
        if text[:1] == "/":
            return os.path.normpath(text)
    elif text[:1] == "/" and text.split("/", 2)[1] == "tmp":
        text = tempfile.gettempdir() + text[len("/tmp"):]
    elif (len(text) >= 2 and text[0] == "/" and text[1].isalpha()
            and (len(text) == 2 or text[2] == "/")):
        text = text[1].upper() + ":/" + text[3:]
    if len(text) >= 2 and text[1] == ":" and text[0].isalpha():
        if len(text) == 2 or text[2] not in "/\\":
            return None
        return os.path.normpath(text)
    if not text or text[0] in "/\\~" or base is None:
        return None
    return os.path.normpath(os.path.join(base, text))


def invocations(command, cwd):
    working = cwd
    found = []
    for segment in split_segments(tokenize(command)):
        start = command_start(segment)
        if start >= len(segment):
            continue
        name = command_name(segment[start])
        arguments = segment[start + 1:]
        if name == "cd":
            operands = [word for word in arguments if word not in ("-L", "-P")]
            working = (to_path(operands[0], working)
                       if operands and operands[0] != "-" else None)
            continue
        found.append((name, arguments, working))
    return found


def is_read_form(arguments):
    verb = arguments[0].lower()
    if verb in READ_VERBS:
        return True
    if verb == "merge":
        return "--merge" not in arguments[1:]
    return verb in LIST_OBJECTS and len(arguments) > 1 and arguments[1].lower() == "list"


def decide(payload, root):
    if not payload.get("agent_id") or payload.get("agent_type") == "vc-checkin":
        return None
    if payload.get("tool_name") != "Bash":
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    cwd = payload.get("cwd")
    working = to_path(cwd, None) if isinstance(cwd, str) else None
    for name, arguments, directory in invocations(command, working):
        if name != "cm" or not arguments or is_read_form(arguments):
            continue
        return REASON.format(verb=arguments[0], tree=directory or UNRESOLVED)
    return None


def deny_document(reason):
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                              "permissionDecision": "deny",
                                              "permissionDecisionReason": reason}})


def main(argv):
    payload = parse_payload(sys.stdin.buffer.read())
    if payload is None:
        return 0
    reason = decide(payload, resolve_root(argv))
    if reason is not None:
        print(deny_document(reason))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
