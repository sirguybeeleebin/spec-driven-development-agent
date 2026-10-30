# tools/bash.py

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any


_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        # Destructive / privileged
        r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f",
        r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r",
        r"\bmkfs\b",
        r"\bdd\s+.*\bof=/dev/",
        r"\bsudo\b",
        r"\bsu\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bchmod\s+[0-7]*777\s+/",
        r":\(\)\s*\{.*\};:",
        r">\s*/dev/sd",
        r">\s*/dev/nvme",
        # Network
        r"\bcurl\b",
        r"\bwget\b",
        r"\bnc\b",
        r"\bnetcat\b",
        r"\bssh\b",
        r"\bscp\b",
        # Python runtime — bash is for exploration, not for running tests
        r"\bpython[0-9]*(?:\.[0-9]+)?\b",
        r"\bpytest\b",
        r"\bpip[0-9]*\b",
        r"\bpoetry\b",
        r"\bpipenv\b",
        r"\bpdm\b",
        r"\bpyenv\b",
        r"\buv\s+run\b",
    )
)


class BashTool:
    def __init__(self, *, root: Path) -> None:
        self._root = root.resolve()

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "bash",
                "description": (
                    "Run a shell command inside the workspace and return "
                    "stdout, stderr, and exit code. Use for exploring the "
                    "repository (ls, find, cat, grep), inspecting diffs, "
                    "and verifying edits. Runs shell utilities only — "
                    "python, pytest, and package managers are blocked; "
                    "use the dedicated test runner for tests."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute.",
                        },
                        "cwd": {
                            "type": "string",
                            "description": (
                                "Workspace-relative working directory. "
                                "Defaults to workspace root."
                            ),
                        },
                        "timeout_sec": {
                            "type": "number",
                            "description": (
                                "Kill after this many seconds. "
                                "Default 30, max 120."
                            ),
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    def execute(self, args: dict[str, Any]) -> dict:
        command = args.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"bash: 'command' must be a non-empty string, got {command!r}")

        cwd_value = args.get("cwd")
        if cwd_value is None:
            cwd = self._root
        else:
            if not isinstance(cwd_value, str):
                raise ValueError(f"bash: 'cwd' must be a string, got {cwd_value!r}")
            candidate = (self._root / cwd_value).resolve()
            if not candidate.is_relative_to(self._root):
                raise ValueError(f"bash: 'cwd' escapes workspace: {cwd_value!r}")
            if not candidate.is_dir():
                raise ValueError(f"bash: 'cwd' is not a directory: {cwd_value!r}")
            cwd = candidate

        timeout_value = args.get("timeout_sec")
        if timeout_value is None:
            timeout = 30.0
        else:
            if isinstance(timeout_value, bool) or not isinstance(timeout_value, (int, float)):
                raise ValueError(
                    f"bash: 'timeout_sec' must be a number, got {timeout_value!r}"
                )
            if timeout_value <= 0:
                raise ValueError(
                    f"bash: 'timeout_sec' must be positive, got {timeout_value!r}"
                )
            timeout = min(float(timeout_value), 120.0)

        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(command):
                return {
                    "ok": False,
                    "error": f"command blocked by policy: {pattern.pattern}",
                    "command": command,
                }

        started = time.monotonic()
        try:
            proc = subprocess.Popen(
                ["/bin/sh", "-c", command],
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                text=True,
                errors="replace",
            )
        except OSError as exc:
            return {
                "ok": False,
                "error": f"failed to spawn: {exc}",
                "command": command,
            }

        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""

        duration_ms = int((time.monotonic() - started) * 1000)
        exit_code = proc.returncode

        streams: dict[str, str] = {}
        for name, raw in (("stdout", stdout), ("stderr", stderr)):
            if not raw:
                streams[name] = "<empty>"
            elif len(raw) <= 8000:
                streams[name] = raw
            else:
                head = raw[:4000]
                tail = raw[-4000:]
                cut = len(raw) - 8000
                streams[name] = f"{head}\n...[truncated {cut} chars]...\n{tail}"

        result = {
            "ok": not timed_out and exit_code == 0,
            "command": command,
            "cwd": str(cwd.relative_to(self._root)) or ".",
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout": streams["stdout"],
            "stderr": streams["stderr"],
        }
        if timed_out:
            result["timed_out"] = True
            result["error"] = f"killed after {timeout:g}s"

        print(
            f"[tools.bash] cmd={command!r} exit={exit_code} "
            f"ms={duration_ms} out={len(stdout)} err={len(stderr)}"
            + (" TIMEOUT" if timed_out else ""),
            flush=True,
        )
        return result