from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import ClassVar, Iterable, Iterator, Sequence

try:  # pragma: no cover - for Python <3.11
    from typing import dataclass_transform
except ImportError:  # pragma: no cover - fallback for old Python
    try:
        from typing_extensions import dataclass_transform
    except ImportError:  # pragma: no cover - minimal stub
        def dataclass_transform(*args, **kwargs):  # type: ignore[unused-argument]
            def decorator(cls):
                return cls

            return decorator


@dataclass_transform()
class Table:
    """Base class for schema-bound tables."""

    __schema__: ClassVar["Schema"]
    _schema_ctx: ClassVar["Schema | None"] = None

    def __init_subclass__(cls, *, schema: "Schema" | None = None, **kw) -> None:  # type: ignore[override]
        super().__init_subclass__(**kw)
        if schema is None:
            schema = Table._schema_ctx
        if schema is None:  # pragma: no cover - defensive
            raise TypeError("schema.Table subclass without schema")
        dataclass(eq=False, frozen=True)(cls)
        cls.__schema__ = schema
        schema._tables.setdefault(cls, {})
        for name in cls.__dataclass_fields__:
            setattr(cls, name, Column(cls, name))
        Table._schema_ctx = None


class Schema:
    def __init__(self) -> None:
        self._tables: dict[type[object], dict[int, object]] = {}
        self._indices: dict[Expr, tuple[type[object], dict[object, dict[int, object]]]] = {}

    @property
    def Table(self) -> type[Table]:
        Table._schema_ctx = self

        class _Shim:
            @staticmethod
            def __mro_entries__(bases):  # drop self, keep Table
                return (Table,)

        return _Shim()  # type: ignore[misc]

    def add(self, row: object) -> None:
        self._tables[type(row)][id(row)] = row
        for expr, (tbl, idx) in self._indices.items():
            base = getattr(tbl, "__table__", tbl)
            if base is type(row):
                val = expr.eval({tbl: row})
                idx.setdefault(val, {})[id(row)] = row

    def remove(self, row: object) -> None:
        del self._tables[type(row)][id(row)]
        for expr, (tbl, idx) in self._indices.items():
            base = getattr(tbl, "__table__", tbl)
            if base is type(row):
                val = expr.eval({tbl: row})
                bucket = idx.get(val)
                if bucket is not None:
                    bucket.pop(id(row), None)
                    if not bucket:
                        idx.pop(val, None)

    def all(self, *tables: type[object]) -> "RowStream":
        if not tables:
            raise TypeError("Schema.all() requires at least one table")
        return RowStream(self, tables)

    def index(self, expr: Expr) -> None:
        tables = _tables_in_expr(expr)
        if len(tables) != 1:
            raise TypeError("index expressions must reference exactly one table")
        tbl = tables.pop()
        base = getattr(tbl, "__table__", tbl)
        data: dict[object, dict[int, object]] = {}
        for rid, row in self._tables.get(base, {}).items():
            val = expr.eval({tbl: row})
            data.setdefault(val, {})[rid] = row
        self._indices[expr] = (tbl, data)

class Expr:
    def __and__(self, other: "Expr") -> "Expr":
        return And(self, other)

    def __or__(self, other: "Expr") -> "Expr":
        return Or(self, other)

    def __invert__(self) -> "Expr":
        return Not(self)

    def eval(self, env: dict[type[object], object]) -> object:  # pragma: no cover - abstract
        raise NotImplementedError


class Column(Expr):
    def __init__(self, table: type[object], name: str) -> None:
        self.table = table
        self.name = name

    def __get__(self, inst: object | None, owner: type[object]) -> object:
        if inst is None:
            return self
        return inst.__dict__[self.name]

    def __eq__(self, other: object) -> "Eq":
        return Eq(self, other)

    def eval(self, env: dict[type[object], object]) -> object:  # pragma: no cover - trivial
        row = env[self.table]
        return getattr(row, self.name)

    __hash__ = object.__hash__


def _value(val: object, env: dict[type[object], object]) -> object:
    if isinstance(val, Expr):
        return val.eval(env)
    return val


def _tables_in_expr(expr: Expr) -> set[type[object]]:
    if isinstance(expr, Column):
        return {expr.table}
    if isinstance(expr, Eq):
        return _tables_in_expr(expr.left) | _tables_in_expr(expr.right)
    if isinstance(expr, And) or isinstance(expr, Or):
        return _tables_in_expr(expr.left) | _tables_in_expr(expr.right)  # type: ignore[arg-type]
    if isinstance(expr, Not):
        return _tables_in_expr(expr.expr)
    return set()


class Eq(Expr):
    def __init__(self, left: object, right: object) -> None:
        self.left = left
        self.right = right

    def eval(self, env: dict[type[object], object]) -> bool:
        return _value(self.left, env) == _value(self.right, env)


class And(Expr):
    def __init__(self, left: Expr, right: Expr) -> None:
        self.left = left
        self.right = right

    def eval(self, env: dict[type[object], object]) -> bool:
        return self.left.eval(env) and self.right.eval(env)


class Or(Expr):
    def __init__(self, left: Expr, right: Expr) -> None:
        self.left = left
        self.right = right

    def eval(self, env: dict[type[object], object]) -> bool:
        return self.left.eval(env) or self.right.eval(env)


class Not(Expr):
    def __init__(self, expr: Expr) -> None:
        self.expr = expr

    def eval(self, env: dict[type[object], object]) -> bool:
        return not self.expr.eval(env)


class RowStream(Iterable[object]):
    def __init__(self, schema: "Schema", tables: Sequence[type[object]], preds: Sequence[Expr] | None = None) -> None:
        self._schema = schema
        self._tables = list(tables)
        self._preds = list(preds or [])

    def filter(self, *exprs: Expr) -> "RowStream":
        return RowStream(self._schema, self._tables, self._preds + list(exprs))

    def __iter__(self) -> Iterator[object]:
        preds = list(self._preds)
        sources = []
        for t in self._tables:
            base = getattr(t, "__table__", t)
            source = None
            for pred in list(preds):
                used = False
                if isinstance(pred, Eq):
                    pairs = [(pred.left, pred.right), (pred.right, pred.left)]
                    for expr, other in pairs:
                        idx = self._schema._indices.get(expr)
                        if idx:
                            tbl, rows = idx
                            idx_base = getattr(tbl, "__table__", tbl)
                            if idx_base is base and not isinstance(other, Expr):
                                bucket = rows.get(other, {})
                                source = list(bucket.values())
                                preds.remove(pred)
                                used = True
                                break
                    if used:
                        break
                idx = self._schema._indices.get(pred)
                if idx:
                    tbl, rows = idx
                    idx_base = getattr(tbl, "__table__", tbl)
                    if idx_base is base:
                        bucket = rows.get(True, {})
                        source = list(bucket.values())
                        preds.remove(pred)
                        break
            if source is None:
                source = list(self._schema._tables.get(base, {}).values())
            sources.append(source)
        for combo in product(*sources):
            env = {t: r for t, r in zip(self._tables, combo)}
            if all(pred.eval(env) for pred in preds):
                yield combo if len(combo) > 1 else combo[0]


def alias(table: type[object]) -> type[object]:
    class _Alias:
        __table__ = table

    for name in table.__dataclass_fields__:  # type: ignore[attr-defined]
        setattr(_Alias, name, Column(_Alias, name))

    return _Alias

