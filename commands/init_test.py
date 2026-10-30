# commands/init_test.py

from __future__ import annotations

from pathlib import Path

from commands import RunInitCommand


def init_reports_missing_files_test(tmp_path: Path) -> None:
    print(f"[{__name__}] init_reports_missing_files_test")
    results = RunInitCommand(root=tmp_path).execute()
    assert results[0].startswith("missing:")
    assert results[1].startswith("missing:")
    assert results[0].endswith("AGENT.md")
    assert results[1].endswith("AGENT.yaml")


def init_reports_existing_files_test(tmp_path: Path) -> None:
    print(f"[{__name__}] init_reports_existing_files_test")
    (tmp_path / "AGENT.md").write_text("x", encoding="utf-8")
    (tmp_path / "AGENT.yaml").write_text("x", encoding="utf-8")
    results = RunInitCommand(root=tmp_path).execute()
    assert results[0].startswith("exists:")
    assert results[1].startswith("exists:")


def init_creates_directories_test(tmp_path: Path) -> None:
    print(f"[{__name__}] init_creates_directories_test")
    RunInitCommand(root=tmp_path).execute()
    for name in ("skills", "tasks", "workflows"):
        assert (tmp_path / name).is_dir()


def init_returns_five_lines_test(tmp_path: Path) -> None:
    print(f"[{__name__}] init_returns_five_lines_test")
    results = RunInitCommand(root=tmp_path).execute()
    assert len(results) == 5
    assert all(r.startswith(("exists:", "missing:", "ready:")) for r in results)


def init_creates_nested_root_test(tmp_path: Path) -> None:
    print(f"[{__name__}] init_creates_nested_root_test")
    nested = tmp_path / "deep" / "root"
    RunInitCommand(root=nested).execute()
    assert (nested / "skills").is_dir()
    assert (nested / "tasks").is_dir()
    assert (nested / "workflows").is_dir()
