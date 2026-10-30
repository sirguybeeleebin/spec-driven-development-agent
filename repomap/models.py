from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    name: str
    kind: str
    scope: tuple[str, ...] = ()
    header: str = ""
    docstring: str = ""
    line: int = -1
    caller: str | None = None
