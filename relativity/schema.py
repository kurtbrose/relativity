from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from itertools import product, count
from bisect import bisect_left, bisect_right, insort
from typing import ClassVar, Iterable, Iterator, Sequence, Generic, TypeVar, get_args, get_origin

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


T = TypeVar("T")


@dataclass(slots=True, frozen=True)
class Ref(Generic[T]):
    id: int


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
        schema._tables.setdefault(cls, set())
        for name in cls.__dataclass_fields__:
            setattr(cls, name, Column(cls, name))
        Table._schema_ctx = None


@dataclass
class Index:
    expr: "Expr"
    table: type[Table]
    data: dict[object, set[Table]]
    unique: bool = False


@dataclass
class OrderedIndex(Index):
    keys: list[object] = field(default_factory=list)


def _dict_field() -> dataclasses.Field:
    return field(default_factory=dict)


@dataclass(repr=False)
class Schema:
    _tables: dict[type[Table], set[Table]] = _dict_field()
    _indices: dict[Expr, Index] = _dict_field()
    _all_rows: dict[int, Table] = _dict_field()
    _row_ids: dict[Table, int] = _dict_field()
    _next_id: count = field(default_factory=lambda: count(1))

    @property
    def Table(self) -> type[Table]:
        Table._schema_ctx = self

        class _Shim:
            @staticmethod
            def __mro_entries__(bases):  # drop self, keep Table
                return (Table,)

        return _Shim()  # type: ignore[misc]

    def ref(self, row: T) -> Ref[T]:
        return Ref(self._row_ids[row])

    def get(self, ref: Ref[T]) -> T:
        return self._all_rows[ref.id]

    def add(self, row: Table, row_id: int | None = None) -> None:
        for name, typ in getattr(type(row), "__annotations__", {}).items():
            if get_origin(typ) is Ref:
                ref = getattr(row, name)
                target = self._all_rows.get(ref.id)
                if target is None or not isinstance(target, get_args(typ)[0]):
                    raise KeyError("invalid reference")
        vals: list[tuple[Index, object]] = []
        for idx in self._indices.values():
            base = getattr(idx.table, "__table__", idx.table)
            if base is type(row):
                val = idx.expr.eval({idx.table: row})
                if idx.unique and idx.data.get(val):
                    raise KeyError("duplicate key for unique index")
                vals.append((idx, val))
        if row_id is None:
            row_id = next(self._next_id)
        self._tables.setdefault(type(row), set()).add(row)
        self._all_rows[row_id] = row
        self._row_ids[row] = row_id
        for idx, val in vals:
            if isinstance(idx, OrderedIndex) and val not in idx.data:
                insort(idx.keys, val)
            bucket = idx.data.setdefault(val, set())
            bucket.add(row)

    def remove(self, row: Table, *, check_refs: bool = True) -> None:
        row_id = self._row_ids[row]
        if check_refs:
            for tbl, rows in self._tables.items():
                for name, typ in getattr(tbl, "__annotations__", {}).items():
                    if get_origin(typ) is Ref and get_args(typ)[0] is type(row):
                        idx = self._indices.get(getattr(tbl, name))
                        if idx:
                            if idx.data.get(row_id):
                                raise KeyError("row is referenced")
                        else:
                            for other in rows:
                                ref = getattr(other, name)
                                if ref.id == row_id:
                                    raise KeyError("row is referenced")
        self._tables[type(row)].remove(row)
        del self._all_rows[row_id]
        del self._row_ids[row]
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

    def all(self, *tables: type[Table]) -> "RowStream":
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
        data: dict[object, set[Table]] = {}
        for row in self._tables.get(base, set()):
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
        data: dict[object, set[Table]] = {}
        for row in self._tables.get(base, set()):
            val = expr.eval({tbl: row})
            bucket = data.setdefault(val, set())
            bucket.add(row)
            if unique and len(bucket) > 1:
                raise KeyError("non-unique value for unique index")
        keys = sorted(data.keys())
        idx = OrderedIndex(expr, tbl, data, unique=unique, keys=keys)
        self._indices[expr] = idx
        return idx

    def replace(self, row: Table, **changes: object) -> Table:
        row_id = self._row_ids[row]
        new_row = dataclasses.replace(row, **changes)
        for idx in self._indices.values():
            base = getattr(idx.table, "__table__", idx.table)
            if base is type(row):
                val = idx.expr.eval({idx.table: new_row})
                bucket = idx.data.get(val, set())
                if idx.unique and bucket and bucket != {row}:
                    raise KeyError("duplicate key for unique index")
        self.remove(row, check_refs=False)
        self.add(new_row, row_id)
        return new_row

class Expr:
    def __and__(self, other: "Expr") -> "Expr":
        return And(self, other)

    def __or__(self, other: "Expr") -> "Expr":
        return Or(self, other)

    def __invert__(self) -> "Expr":
        return Not(self)

    def eval(self, env: dict[type[Table], Table]) -> object:  # pragma: no cover - abstract
        raise NotImplementedError


@dataclass(frozen=True)
class Column(Expr):
    table: type[Table]
    name: str

    def __get__(self, inst: Table | None, owner: type[Table]) -> object:
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

    def eval(self, env: dict[type[Table], Table]) -> object:  # pragma: no cover - trivial
        row = env[self.table]
        val = getattr(row, self.name)
        if isinstance(val, Ref):
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

    def eval(self, env: dict[type[Table], Table]) -> object:  # pragma: no cover - trivial
        return tuple(expr.eval(env) for expr in self.exprs)


def _value(val: object, env: dict[type[Table], Table]) -> object:
    if isinstance(val, Expr):
        return val.eval(env)
    if isinstance(val, Ref):
        return val.id
    if isinstance(val, type) and val in env:
        row = env[val]
        schema = getattr(val, "__schema__", getattr(getattr(val, "__table__", None), "__schema__", None))
        if schema is not None:
            return schema._row_ids[row]
        return row
    return val


def _tables_in_expr(expr: Expr) -> set[type[Table]]:
    if isinstance(expr, Column):
        return {expr.table}
    if isinstance(expr, Tuple):
        tables: set[type[Table]] = set()
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

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return _value(self.left, env) == _value(self.right, env)


@dataclass(frozen=True)
class Lt(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return _value(self.left, env) < _value(self.right, env)


@dataclass(frozen=True)
class Le(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return _value(self.left, env) <= _value(self.right, env)


@dataclass(frozen=True)
class Gt(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return _value(self.left, env) > _value(self.right, env)


@dataclass(frozen=True)
class Ge(Expr):
    left: object
    right: object

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return _value(self.left, env) >= _value(self.right, env)


@dataclass(frozen=True)
class And(Expr):
    left: Expr
    right: Expr

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return self.left.eval(env) and self.right.eval(env)


@dataclass(frozen=True)
class Or(Expr):
    left: Expr
    right: Expr

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return self.left.eval(env) or self.right.eval(env)


@dataclass(frozen=True)
class Not(Expr):
    expr: Expr

    def eval(self, env: dict[type[Table], Table]) -> bool:
        return not self.expr.eval(env)


class RowStream(Iterable[object]):
    def __init__(self, schema: "Schema", tables: Sequence[type[Table]], preds: Sequence[Expr] | None = None) -> None:
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
                            if idx_base is base and not isinstance(other, Expr) and not isinstance(other, type):
                                key = _value(other, {})
                                bucket = rows.get(key, set())
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
                        if isinstance(idx, OrderedIndex) and not isinstance(other, Expr) and not isinstance(other, type):
                            key = _value(other, {})
                            keys, rows = idx.keys, idx.data
                            if op == "<":
                                pos = bisect_left(keys, key)
                                sel = keys[:pos]
                            elif op == "<=":
                                pos = bisect_right(keys, key)
                                sel = keys[:pos]
                            elif op == ">":
                                pos = bisect_right(keys, key)
                                sel = keys[pos:]
                            else:  # >=
                                pos = bisect_left(keys, key)
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
                source = list(self._schema._tables.get(base, set()))
            sources.append(source)
        for combo in product(*sources):
            env = {t: r for t, r in zip(self._tables, combo)}
            if all(pred.eval(env) for pred in preds):
                yield combo if len(combo) > 1 else combo[0]


def alias(table: type[Table]) -> type[Table]:
    class _Alias:
        __table__ = table

    for name in table.__dataclass_fields__:  # type: ignore[attr-defined]
        setattr(_Alias, name, Column(_Alias, name))

    return _Alias

