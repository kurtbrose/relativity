from __future__ import annotations

from dataclasses import dataclass, field

from .expr import Expr


@dataclass
class Index:
    expr: Expr
    table: type["Table"]
    data: dict[object, set["Table"]]
    unique: bool = False


@dataclass
class OrderedIndex(Index):
    keys: list[object] = field(default_factory=list)


__all__ = ["Index", "OrderedIndex"]
