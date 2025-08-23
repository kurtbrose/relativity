from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_left, bisect_right
from typing import Any, Iterable, Iterator, Sequence
import sys

from .expr import Expr, Eq, InRange, Tuple, _value
from .index import OrderedIndex
if True:  # pragma: no cover - for type checking without runtime import
    from .schema import Schema, Table  # type: ignore


@dataclass(frozen=True)
class SourcePlan:
    table: type["Table"]
    scan: "Scan"


class Scan:
    def run(self, schema: "Schema", env: dict[type["Table"], object] | None = None) -> list[object]:
        raise NotImplementedError


@dataclass(frozen=True)
class FullScan(Scan):
    base: type

    def run(self, s: "Schema", env: dict[type["Table"], object] | None = None) -> list[object]:
        row_ids = s._row_ids
        return sorted(s._tables.get(self.base, set()), key=row_ids.__getitem__)


@dataclass(frozen=True)
class EqScan(Scan):
    base: type
    index_expr: Expr
    key: Any
    ordered: bool

    def run(self, s: "Schema", env: dict[type["Table"], object] | None = None) -> list[object]:
        row_ids = s._row_ids
        idx = s._indices[self.index_expr]
        key_env = env or {}
        key = (
            tuple(_value(k, key_env) for k in self.key)
            if isinstance(self.key, tuple)
            else _value(self.key, key_env)
        )
        if self.ordered:
            ids = idx.data.get(key, [])
            return [s._all_rows[i] for i in ids]
        bucket = idx.data.get(key, set())
        return sorted(bucket, key=row_ids.__getitem__)


@dataclass(frozen=True)
class RangeScan(Scan):
    base: type
    index: OrderedIndex
    lo: tuple[Any, int] | None
    hi: tuple[Any, int] | None

    def run(self, s: "Schema", env: dict[type["Table"], object] | None = None) -> list[object]:
        keys = self.index.keys
        lo_pos = 0 if self.lo is None else bisect_left(keys, self.lo)
        hi_pos = len(keys) if self.hi is None else bisect_right(keys, self.hi)
        return [s._all_rows[rid] for _, rid in keys[lo_pos:hi_pos]]


@dataclass(frozen=True)
class BoolScan(Scan):
    base: type
    index_expr: Expr

    def run(self, s: "Schema", env: dict[type["Table"], object] | None = None) -> list[object]:
        row_ids = s._row_ids
        idx = s._indices[self.index_expr]
        bucket = idx.data.get(True, set())
        return sorted(bucket, key=row_ids.__getitem__)


def _norm_one(pred: Expr) -> Expr:
    if isinstance(pred, Eq):
        left, right = pred.left, pred.right
        if isinstance(right, Expr) and not isinstance(left, Expr):
            return Eq(right, left)
        if isinstance(left, Expr) and not isinstance(right, Expr):
            return pred
        if repr(left) > repr(right):
            return Eq(right, left)
        return pred
    return pred


def _normalize(preds: Sequence[Expr]) -> list[Expr]:
    ranges: dict[Expr, InRange] = {}
    others: list[Expr] = []
    for p in preds:
        np = _norm_one(p)
        if isinstance(np, InRange):
            col = np.col
            existing = ranges.get(col)
            if existing:
                lo, lo_inc = existing.lo, existing.lo_inc
                hi, hi_inc = existing.hi, existing.hi_inc
                if np.lo is not None:
                    if lo is None or np.lo > lo or (np.lo == lo and not np.lo_inc):
                        lo, lo_inc = np.lo, np.lo_inc
                    elif np.lo == lo:
                        lo_inc = lo_inc and np.lo_inc
                if np.hi is not None:
                    if hi is None or np.hi < hi or (np.hi == hi and not np.hi_inc):
                        hi, hi_inc = np.hi, np.hi_inc
                    elif np.hi == hi:
                        hi_inc = hi_inc and np.hi_inc
                ranges[col] = InRange(col, lo, lo_inc, hi, hi_inc)
            else:
                ranges[col] = np
        else:
            others.append(np)
    return list(ranges.values()) + others


class Planner:
    def __init__(self, schema: "Schema") -> None:
        self.s = schema

    def plan(
        self, tables: Sequence[type["Table"]], preds: Sequence[Expr]
    ) -> tuple[list[SourcePlan], list[Expr]]:
        remaining = list(preds)
        plans: list[SourcePlan] = []
        for t in tables:
            base = getattr(t, "__table__", t)
            scan = self._pick_scan_for_table(base, remaining)
            plans.append(SourcePlan(t, scan))
        return plans, remaining

    def _pick_scan_for_table(self, base: type, preds: list[Expr]) -> Scan:
        # Check for composite indexes matching multiple equality predicates
        for idx_expr, idx in self.s._indices.items():
            if not self._same_base(idx.table, base):
                continue
            if not isinstance(idx_expr, Tuple):
                continue
            if idx.where is not None and idx.where not in preds:
                continue
            keys: list[object] = []
            used: list[Expr] = []
            for sub in idx_expr.exprs:
                match = False
                for pred in preds:
                    if isinstance(pred, Eq):
                        for expr, other in ((pred.left, pred.right), (pred.right, pred.left)):
                            if expr is sub:
                                keys.append(other)
                                used.append(pred)
                                match = True
                                break
                        if match:
                            break
                if not match:
                    break
            else:
                for p in used:
                    preds.remove(p)
                if idx.where is not None:
                    preds.remove(idx.where)
                ordered = isinstance(idx, OrderedIndex)
                return EqScan(base, idx_expr, tuple(keys), ordered)

        for pred in list(preds):
            if isinstance(pred, Eq):
                for expr, other in ((pred.left, pred.right), (pred.right, pred.left)):
                    idx = self.s._indices.get(expr)
                    if idx and self._same_base(idx.table, base):
                        if idx.where is not None and idx.where not in preds:
                            continue
                        ordered = isinstance(idx, OrderedIndex)
                        preds.remove(pred)
                        if idx.where is not None:
                            preds.remove(idx.where)
                        if not isinstance(other, Expr) and not isinstance(other, type):
                            key = _value(other, {})
                            return EqScan(base, expr, key, ordered)
                        return EqScan(base, expr, other, ordered)
        for pred in list(preds):
            r = self._range_scan_for_pred(base, pred, preds)
            if r is not None:
                preds.remove(pred)
                return r
        for pred in list(preds):
            idx = self.s._indices.get(pred)
            if idx and self._same_base(idx.table, base):
                if idx.where is not None and idx.where not in preds:
                    continue
                preds.remove(pred)
                if idx.where is not None:
                    preds.remove(idx.where)
                return BoolScan(base, pred)
        return FullScan(base)
    def _range_scan_for_pred(self, base: type, pred: Expr, preds: list[Expr]) -> RangeScan | None:
        def ordered_idx(expr: Expr) -> OrderedIndex | None:
            idx = self.s._indices.get(expr)
            if (
                isinstance(idx, OrderedIndex)
                and self._same_base(idx.table, base)
                and (idx.where is None or idx.where in preds)
            ):
                return idx
            return None

        if isinstance(pred, InRange):
            idx = ordered_idx(pred.col)
            if idx:
                if idx.where is not None:
                    preds.remove(idx.where)
                lo = None
                hi = None
                if pred.lo is not None:
                    key = _value(pred.lo, {})
                    lo = (key, 0 if pred.lo_inc else sys.maxsize)
                if pred.hi is not None:
                    key = _value(pred.hi, {})
                    hi = (key, sys.maxsize if pred.hi_inc else -1)
                return RangeScan(base, idx, lo, hi)
        return None

    @staticmethod
    def _same_base(tbl: type, base: type) -> bool:
        idx_base = getattr(tbl, "__table__", tbl)
        return idx_base is base


class RowStream(Iterable[object]):
    def __init__(
        self,
        schema: "Schema",
        tables: Sequence[type["Table"]],
        preds: Sequence[Expr] | None = None,
        order: tuple[Expr, bool] | None = None,
    ) -> None:
        self._schema = schema
        self._tables = list(tables)
        self._preds = list(preds or [])
        self._order = order

    def filter(self, *exprs: Expr) -> "RowStream":
        return RowStream(self._schema, self._tables, self._preds + list(exprs), self._order)

    def order_by(self, key: Expr, id: bool = True) -> "RowStream":
        if len(self._tables) != 1:
            raise TypeError("order_by() requires exactly one table")
        return RowStream(self._schema, self._tables, self._preds, (key, id))

    def __iter__(self) -> Iterator[object]:
        planner = Planner(self._schema)
        plans, residual = planner.plan(self._tables, _normalize(self._preds))
        row_ids = self._schema._row_ids
        results: list[object | tuple[object, ...]] = []
        env: dict[type["Table"], object] = {}

        def backtrack(i: int, combo: tuple[object, ...]) -> None:
            if i == len(plans):
                if all(pred.eval(env) for pred in residual):
                    results.append(combo if len(combo) > 1 else combo[0])
                return
            plan = plans[i]
            rows = plan.scan.run(self._schema, env)
            for row in rows:
                env[plan.table] = row
                backtrack(i + 1, combo + (row,))
            env.pop(plan.table, None)

        backtrack(0, tuple())

        if self._order:
            key_expr, use_id = self._order
            tbl = self._tables[0]

            def _sort_key(row: object):
                val = key_expr.eval({tbl: row})
                return (val, row_ids[row]) if use_id else val

            results.sort(key=_sort_key)

        yield from results


__all__ = ["RowStream"]
