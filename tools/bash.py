# tools/bash.py

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {"ls", "cat", "grep", "head", "sed", "tree"}
)

MAX_LINES = 30

TIMEOUT_SEC = 30.0


class BashTool:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "bash",
                "description": (
                    "Run exactly one shell command in the workspace "
                    "root. Only these six commands are available:\n"
                    "\n"
                    "  - `ls <path>` — list a directory.\n"
                    "  - `cat <path>` — print a file.\n"
                    "  - `grep [flags] <pattern> <path>` — search "
                    "inside files; `grep -r <pattern> <dir>` searches "
                    "recursively.\n"
                    "  - `head <path>` — first lines of a file.\n"
                    "  - `sed -n <range> <path>` — a slice of a file.\n"
                    "  - `tree [flags] <path>` — print the directory "
                    "tree; `tree -L 3 --noreport -I __pycache__ .` is "
                    "the recommended invocation for a workspace scan.\n"
                    "\n"
                    "Each call runs one command, with no pipes, no "
                    "`&&`, no `;`, no redirects. stdout is capped at "
                    "30 lines."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "One shell command starting with `ls`, "
                                "`cat`, `grep`, `head`, `sed`, or "
                                "`tree`. Example: `tree -L 3 --noreport "
                                "-I __pycache__ .`."
                            ),
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    def execute(self, args: dict) -> dict:
        command = args.get("command")
        if not isinstance(command, str) or not command.strip():
            return {
                "ok": False,
                "exit_code": -1,
                "error": "'command' must be a non-empty string",
            }

        first_word = command.strip().split()[0]
        if first_word not in ALLOWED_COMMANDS:
            return {
                "ok": False,
                "exit_code": -1,
                "error": (
                    f"command not allowed: {first_word!r}. "
                    f"Allowed: {sorted(ALLOWED_COMMANDS)}."
                ),
            }

        try:
            proc = subprocess.run(
                ["/bin/sh", "-c", command],
                cwd=str(self._root),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "exit_code": -1,
                "error": f"killed after {TIMEOUT_SEC:g}s",
            }
        except OSError as exc:
            return {
                "ok": False,
                "exit_code": -1,
                "error": f"failed to spawn: {exc}",
            }

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        stderr_stripped = stderr.strip()
        exit_code = proc.returncode

        lines = stdout.splitlines()
        total_lines = len(lines)
        if total_lines <= MAX_LINES:
            output = "\n".join(lines)
            line_count = total_lines
            truncated = 0
        else:
            output = "\n".join(lines[:MAX_LINES])
            line_count = total_lines
            truncated = total_lines - MAX_LINES

        if exit_code == 0 or (exit_code == 1 and not stderr_stripped):
            result: dict[str, Any] = {
                "ok": True,
                "exit_code": exit_code,
                "output": output,
                "line_count": line_count,
                "truncated": truncated,
            }
        else:
            error_lines = stderr_stripped.splitlines()
            if len(error_lines) <= MAX_LINES:
                error_text = "\n".join(error_lines)
            else:
                error_text = "\n".join(error_lines[:MAX_LINES])
            result = {
                "ok": False,
                "exit_code": exit_code,
                "output": output,
                "line_count": line_count,
                "truncated": truncated,
                "error": error_text or f"exit {exit_code}",
            }

        return result
