from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from itertools import product
from bisect import bisect_left, bisect_right, insort
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


@dataclass
class Index:
    expr: "Expr"
    table: type[object]
    data: dict[object, set[object]]
    unique: bool = False


@dataclass
class OrderedIndex(Index):
    keys: list[object] = field(default_factory=list)


class Schema:
    def __init__(self) -> None:
        self._tables: dict[type[object], dict[int, object]] = {}
        self._indices: dict[Expr, Index] = {}

    @property
    def Table(self) -> type[Table]:
        Table._schema_ctx = self

        class _Shim:
            @staticmethod
            def __mro_entries__(bases):  # drop self, keep Table
                return (Table,)

        return _Shim()  # type: ignore[misc]

    def add(self, row: object) -> None:
        vals: list[tuple[Index, object]] = []
        for idx in self._indices.values():
            base = getattr(idx.table, "__table__", idx.table)
            if base is type(row):
                val = idx.expr.eval({idx.table: row})
                if idx.unique and idx.data.get(val):
                    raise KeyError("duplicate key for unique index")
                vals.append((idx, val))
        self._tables[type(row)][id(row)] = row
        for idx, val in vals:
            if isinstance(idx, OrderedIndex) and val not in idx.data:
                insort(idx.keys, val)
            bucket = idx.data.setdefault(val, set())
            bucket.add(row)

    def remove(self, row: object) -> None:
        del self._tables[type(row)][id(row)]
        for idx in self._indices.values():
            base = getattr(idx.table, "__table__", idx.table)
            if base is type(row):
                val = idx.expr.eval({idx.table: row})
                bucket = idx.data.get(val)
                if bucket is not None:
                    bucket.discard(row)
                    if not bucket:
                        idx.data.pop(val, None)
                        if isinstance(idx, OrderedIndex):
                            pos = bisect_left(idx.keys, val)
                            if pos < len(idx.keys) and idx.keys[pos] == val:
                                idx.keys.pop(pos)

    def all(self, *tables: type[object]) -> "RowStream":
        if not tables:
            raise TypeError("Schema.all() requires at least one table")
        return RowStream(self, tables)

    def index(self, *exprs: Expr, unique: bool = False) -> Index:
        if not exprs:
            raise TypeError("Schema.index() requires at least one expression")
        expr = exprs[0] if len(exprs) == 1 else Tuple(*exprs)
        tables = _tables_in_expr(expr)
        if len(tables) != 1:
            raise TypeError("index expressions must reference exactly one table")
        tbl = tables.pop()
        base = getattr(tbl, "__table__", tbl)
        data: dict[object, set[object]] = {}
        for row in self._tables.get(base, {}).values():
            val = expr.eval({tbl: row})
            bucket = data.setdefault(val, set())
            bucket.add(row)
            if unique and len(bucket) > 1:
                raise KeyError("non-unique value for unique index")
        idx = Index(expr, tbl, data, unique)
        self._indices[expr] = idx
        return idx

    def ordered_index(self, *exprs: Expr, unique: bool = False) -> OrderedIndex:
        if not exprs:
            raise TypeError("Schema.ordered_index() requires at least one expression")
        expr = exprs[0] if len(exprs) == 1 else Tuple(*exprs)
        tables = _tables_in_expr(expr)
        if len(tables) != 1:
            raise TypeError("index expressions must reference exactly one table")
        tbl = tables.pop()
        base = getattr(tbl, "__table__", tbl)
        data: dict[object, set[object]] = {}
        for row in self._tables.get(base, {}).values():
            val = expr.eval({tbl: row})
            bucket = data.setdefault(val, set())
            bucket.add(row)
            if unique and len(bucket) > 1:
                raise KeyError("non-unique value for unique index")
        keys = sorted(data.keys())
        idx = OrderedIndex(expr, tbl, data, unique=unique, keys=keys)
        self._indices[expr] = idx
        return idx

    def replace(self, row: object, **changes: object) -> object:
        new_row = dataclasses.replace(row, **changes)
        for idx in self._indices.values():
            base = getattr(idx.table, "__table__", idx.table)
            if base is type(row):
                val = idx.expr.eval({idx.table: new_row})
                bucket = idx.data.get(val, set())
                if idx.unique and bucket and bucket != {row}:
                    raise KeyError("duplicate key for unique index")
        self.remove(row)
        self.add(new_row)
        return new_row

class Expr:
    def __and__(self, other: "Expr") -> "Expr":
        return And(self, other)

    def __or__(self, other: "Expr") -> "Expr":
        return Or(self, other)

    def __invert__(self) -> "Expr":
        return Not(self)

    def eval(self, env: dict[type[object], object]) -> object:  # pragma: no cover - abstract
        raise NotImplementedError


@dataclass(frozen=True)
class Column(Expr):
    table: type[object]
    name: str

    def __get__(self, inst: object | None, owner: type[object]) -> object:
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

    def eval(self, env: dict[type[object], object]) -> object:  # pragma: no cover - trivial
        row = env[self.table]
        return getattr(row, self.name)


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

    def eval(self, env: dict[type[object], object]) -> object:  # pragma: no cover - trivial
        return tuple(expr.eval(env) for expr in self.exprs)


def _value(val: object, env: dict[type[object], object]) -> object:
    if isinstance(val, Expr):
        return val.eval(env)
    return val


def _tables_in_expr(expr: Expr) -> set[type[object]]:
    if isinstance(expr, Column):
        return {expr.table}
    if isinstance(expr, Tuple):
        tables: set[type[object]] = set()
        for sub in expr.exprs:
            tables |= _tables_in_expr(sub)
        return tables
    if isinstance(expr, (Eq, Lt, Le, Gt, Ge)):
        return _tables_in_expr(expr.left) | _tables_in_expr(expr.right)
    if isinstance(expr, And) or isinstance(expr, Or):
        return _tables_in_expr(expr.left) | _tables_in_expr(expr.right)  # type: ignore[arg-type]
    if isinstance(expr, Not):
        return _tables_in_expr(expr.expr)
    return set()


@dataclass(frozen=True)
class Eq(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[object], object]) -> bool:
        return _value(self.left, env) == _value(self.right, env)


@dataclass(frozen=True)
class Lt(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[object], object]) -> bool:
        return _value(self.left, env) < _value(self.right, env)


@dataclass(frozen=True)
class Le(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[object], object]) -> bool:
        return _value(self.left, env) <= _value(self.right, env)


@dataclass(frozen=True)
class Gt(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[object], object]) -> bool:
        return _value(self.left, env) > _value(self.right, env)


@dataclass(frozen=True)
class Ge(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[object], object]) -> bool:
        return _value(self.left, env) >= _value(self.right, env)


@dataclass(frozen=True)
class And(Expr):
    left: Expr
    right: Expr

    def eval(self, env: dict[type[object], object]) -> bool:
        return self.left.eval(env) and self.right.eval(env)


@dataclass(frozen=True)
class Or(Expr):
    left: Expr
    right: Expr

    def eval(self, env: dict[type[object], object]) -> bool:
        return self.left.eval(env) or self.right.eval(env)


@dataclass(frozen=True)
class Not(Expr):
    expr: Expr

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
                            tbl, rows = idx.table, idx.data
                            idx_base = getattr(tbl, "__table__", tbl)
                            if idx_base is base and not isinstance(other, Expr):
                                bucket = rows.get(other, set())
                                source = list(bucket)
                                preds.remove(pred)
                                used = True
                                break
                    if used:
                        break
                if isinstance(pred, (Lt, Le, Gt, Ge)):
                    comps: list[tuple[object, object, str]] = []
                    if isinstance(pred, Lt):
                        comps = [(pred.left, pred.right, "<"), (pred.right, pred.left, ">")]
                    elif isinstance(pred, Le):
                        comps = [(pred.left, pred.right, "<="), (pred.right, pred.left, ">=")]
                    elif isinstance(pred, Gt):
                        comps = [(pred.left, pred.right, ">"), (pred.right, pred.left, "<")]
                    elif isinstance(pred, Ge):
                        comps = [(pred.left, pred.right, ">="), (pred.right, pred.left, "<=")]
                    for expr, other, op in comps:
                        idx = self._schema._indices.get(expr)
                        if isinstance(idx, OrderedIndex) and not isinstance(other, Expr):
                            keys, rows = idx.keys, idx.data
                            if op == "<":
                                pos = bisect_left(keys, other)
                                sel = keys[:pos]
                            elif op == "<=":
                                pos = bisect_right(keys, other)
                                sel = keys[:pos]
                            elif op == ">":
                                pos = bisect_right(keys, other)
                                sel = keys[pos:]
                            else:  # >=
                                pos = bisect_left(keys, other)
                                sel = keys[pos:]
                            bucket: list[object] = []
                            for k in sel:
                                bucket.extend(rows.get(k, set()))
                            source = bucket
                            preds.remove(pred)
                            used = True
                            break
                    if used:
                        break
                idx = self._schema._indices.get(pred)
                if idx:
                    tbl, rows = idx.table, idx.data
                    idx_base = getattr(tbl, "__table__", tbl)
                    if idx_base is base:
                        bucket = rows.get(True, set())
                        source = list(bucket)
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

