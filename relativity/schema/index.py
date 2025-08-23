from __future__ import annotations

from dataclasses import dataclass, field

from .expr import Expr


@dataclass
class Index:
    expr: Expr
    table: type["Table"]
    data: dict[object, set[int]]
    unique: bool = False
    where: Expr | None = None


@dataclass
class OrderedIndex(Index):
    data: dict[object, list[int]] = field(init=False, default_factory=dict)
    keys: list[tuple[object, int]] = field(default_factory=list)


__all__ = ["Index", "OrderedIndex"]
