# commands/info_test.py

from __future__ import annotations

from commands import RunInfoCommand


def info_returns_eight_rows_test() -> None:
    print(f"[{__name__}] info_returns_eight_rows_test")
    rows = RunInfoCommand().execute()
    assert len(rows) == 8
    assert all(len(r) == 4 for r in rows)


def info_numbers_are_sequential_test() -> None:
    print(f"[{__name__}] info_numbers_are_sequential_test")
    rows = RunInfoCommand().execute()
    numbers = [r[0] for r in rows]
    assert numbers == [str(i) for i in range(1, 9)]


def info_contains_expected_commands_test() -> None:
    print(f"[{__name__}] info_contains_expected_commands_test")
    commands = {r[1] for r in RunInfoCommand().execute()}
    for expected in (
        "config set <key> <value>",
        "config get <key>",
        "config delete <key>",
        "config clear",
        "info",
        "init",
        "run task <id>",
        "run workflow <id>",
    ):
        assert expected in commands


def info_fields_are_non_empty_test() -> None:
    print(f"[{__name__}] info_fields_are_non_empty_test")
    for _, cmd, desc, example in RunInfoCommand().execute():
        assert cmd and desc and example
