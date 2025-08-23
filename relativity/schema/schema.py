from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from itertools import count
from bisect import bisect_left, bisect_right, insort
from typing import ClassVar, Generic, Iterable, Iterator, Sequence, TypeVar, get_args, get_origin

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


from ._util import _dict_field
from .expr import Expr, Column, Tuple, _tables_in_expr
from .index import Index, OrderedIndex

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
        from .query import RowStream  # import here to avoid circular
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


def alias(table: type[Table]) -> type[Table]:
    class _Alias:
        __table__ = table

    for name in table.__dataclass_fields__:  # type: ignore[attr-defined]
        setattr(_Alias, name, Column(_Alias, name))

    return _Alias


__all__ = ["Schema", "Table", "Ref", "alias"]
