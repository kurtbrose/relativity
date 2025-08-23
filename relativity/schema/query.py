from __future__ import annotations

from bisect import bisect_left, bisect_right
from itertools import product
from typing import Iterable, Iterator, Sequence

from .expr import Expr, Eq, Lt, Le, Gt, Ge, _value
from .index import OrderedIndex

if True:  # pragma: no cover - for type checking without runtime import
    from .schema import Schema, Table  # type: ignore


class RowStream(Iterable[object]):
    def __init__(self, schema: "Schema", tables: Sequence[type["Table"]], preds: Sequence[Expr] | None = None) -> None:
        self._schema = schema
        self._tables = list(tables)
        self._preds = list(preds or [])

    def filter(self, *exprs: Expr) -> "RowStream":
        return RowStream(self._schema, self._tables, self._preds + list(exprs))

    def __iter__(self) -> Iterator[object]:
        preds = list(self._preds)
        sources = []
        row_ids = self._schema._row_ids
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
                                source = sorted(bucket, key=row_ids.__getitem__)
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
                            source = sorted(bucket, key=row_ids.__getitem__)
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
                        source = sorted(bucket, key=row_ids.__getitem__)
                        preds.remove(pred)
                        break
            if source is None:
                source = sorted(self._schema._tables.get(base, set()), key=row_ids.__getitem__)
            sources.append(source)
        for combo in product(*sources):
            env = {t: r for t, r in zip(self._tables, combo)}
            if all(pred.eval(env) for pred in preds):
                yield combo if len(combo) > 1 else combo[0]


__all__ = ["RowStream"]
