from __future__ import annotations

from dataclasses import dataclass, field

from .expr import Expr


@dataclass
class Index:
    expr: Expr
    table: type["Table"]
    data: dict[object, set["Table"]]
    unique: bool = False
    where: Expr | None = None


@dataclass
class OrderedIndex(Index):
    data: dict[object, list[int]]
    keys: list[tuple[object, int]] = field(default_factory=list)


__all__ = ["Index", "OrderedIndex"]
