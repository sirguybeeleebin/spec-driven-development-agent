# commands/info.py

from __future__ import annotations


class RunInfoCommand:
    def execute(self) -> list[tuple[str, str, str, str]]:
        return [
            (
                "1",
                "config set <key> <value>",
                "Set a config value",
                "config set max_fix_attempts 5",
            ),
            (
                "2",
                "config get <key>",
                "Show a config value",
                "config get max_fix_attempts",
            ),
            (
                "3",
                "config delete <key>",
                "Delete a config key",
                "config delete max_fix_attempts",
            ),
            (
                "4",
                "config clear",
                "Remove the config file",
                "config clear",
            ),
            ("5", "info", "Show this table", "info"),
            ("6", "init", "Scaffold the workspace", "init"),
            (
                "7",
                "run task <id>",
                "Run a single task",
                "run task 001_products_repository",
            ),
            (
                "8",
                "run workflow <id>",
                "Run a whole workflow",
                "run workflow end_to_end",
            ),
        ]
