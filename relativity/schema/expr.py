from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Set


class Expr:
    def __and__(self, other: "Expr") -> "Expr":
        return And(self, other)

    def __or__(self, other: "Expr") -> "Expr":
        return Or(self, other)

    def __invert__(self) -> "Expr":
        return Not(self)

    def eval(self, env: Dict[type[object], object]) -> Any:  # pragma: no cover - abstract
        raise NotImplementedError


@dataclass(frozen=True)
class Column(Expr):
    table: type["Table"]
    name: str

    def __get__(self, inst: object | None, owner: type["Table"]) -> object:
        if inst is None:
            return self
        return inst.__dict__[self.name]

    def __eq__(self, other: object) -> "Eq":  # type: ignore[override]
        return Eq(self, other)

    def __lt__(self, other: object) -> "Lt":  # type: ignore[override]
        return Lt(self, other)

    def __le__(self, other: object) -> "Le":  # type: ignore[override]
        return Le(self, other)

    def __gt__(self, other: object) -> "Gt":  # type: ignore[override]
        return Gt(self, other)

    def __ge__(self, other: object) -> "Ge":  # type: ignore[override]
        return Ge(self, other)

    def eval(self, env: Dict[type[object], object]) -> Any:  # pragma: no cover - trivial
        row = env[self.table]
        val = getattr(row, self.name)
        if hasattr(val, "id") and type(val).__name__ == "Ref":
            return val.id
        return val


@dataclass(frozen=True, init=False)
class Tuple(Expr):
    exprs: tuple[Expr, ...]

    def __init__(self, *exprs: Expr):
        object.__setattr__(self, "exprs", tuple(exprs))

    def __eq__(self, other: object) -> "Eq":  # type: ignore[override]
        return Eq(self, other)

    def __lt__(self, other: object) -> "Lt":  # type: ignore[override]
        return Lt(self, other)

    def __le__(self, other: object) -> "Le":  # type: ignore[override]
        return Le(self, other)

    def __gt__(self, other: object) -> "Gt":  # type: ignore[override]
        return Gt(self, other)

    def __ge__(self, other: object) -> "Ge":  # type: ignore[override]
        return Ge(self, other)

    def eval(self, env: Dict[type[object], object]) -> Any:  # pragma: no cover - trivial
        return tuple(expr.eval(env) for expr in self.exprs)


def _value(val: object, env: Dict[type[object], object]) -> object:
    if isinstance(val, Expr):
        return val.eval(env)
    if hasattr(val, "id") and type(val).__name__ == "Ref":
        return val.id
    if isinstance(val, type) and val in env:
        row = env[val]
        schema = getattr(val, "__schema__", getattr(getattr(val, "__table__", None), "__schema__", None))
        if schema is not None:
            return schema._row_ids[row]
        return row
    return val


def _tables_in_expr(expr: Expr) -> Set[type["Table"]]:
    if isinstance(expr, Column):
        return {expr.table}
    if isinstance(expr, Tuple):
        tables: Set[type["Table"]] = set()
        for sub in expr.exprs:
            tables |= _tables_in_expr(sub)
        return tables
    if isinstance(expr, (Eq, Lt, Le, Gt, Ge)):
        return _tables_in_expr(expr.left) | _tables_in_expr(expr.right)
    if isinstance(expr, And) or isinstance(expr, Or):
        return _tables_in_expr(expr.left) | _tables_in_expr(expr.right)
    if isinstance(expr, Not):
        return _tables_in_expr(expr.expr)
    return set()


@dataclass(frozen=True)
class Eq(Expr):
    left: object
    right: object

    def eval(self, env: Dict[type[object], object]) -> bool:
        return _value(self.left, env) == _value(self.right, env)


@dataclass(frozen=True)
class Lt(Expr):
    left: object
    right: object

    def eval(self, env: Dict[type[object], object]) -> bool:
        return _value(self.left, env) < _value(self.right, env)


@dataclass(frozen=True)
class Le(Expr):
    left: object
    right: object

    def eval(self, env: Dict[type[object], object]) -> bool:
        return _value(self.left, env) <= _value(self.right, env)


@dataclass(frozen=True)
class Gt(Expr):
    left: object
    right: object

    def eval(self, env: Dict[type[object], object]) -> bool:
        return _value(self.left, env) > _value(self.right, env)


@dataclass(frozen=True)
class Ge(Expr):
    left: object
    right: object

    def eval(self, env: Dict[type[object], object]) -> bool:
        return _value(self.left, env) >= _value(self.right, env)


@dataclass(frozen=True)
class And(Expr):
    left: Expr
    right: Expr

    def eval(self, env: Dict[type[object], object]) -> bool:
        return self.left.eval(env) and self.right.eval(env)


@dataclass(frozen=True)
class Or(Expr):
    left: Expr
    right: Expr

    def eval(self, env: Dict[type[object], object]) -> bool:
        return self.left.eval(env) or self.right.eval(env)


@dataclass(frozen=True)
class Not(Expr):
    expr: Expr

    def eval(self, env: Dict[type[object], object]) -> bool:
        return not self.expr.eval(env)


__all__ = [
    "Expr",
    "Column",
    "Tuple",
    "_value",
    "_tables_in_expr",
    "Eq",
    "Lt",
    "Le",
    "Gt",
    "Ge",
    "And",
    "Or",
    "Not",
]
