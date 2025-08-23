from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Iterator
from typing import dataclass_transform


@dataclass_transform()
class Table:
    """Base class for schema-bound tables."""

    __schema__: ClassVar["Schema"]

    def __init_subclass__(cls, *, schema: "Schema", **kw) -> None:  # type: ignore[override]
        super().__init_subclass__(**kw)
        dataclass(eq=False, frozen=True)(cls)
        cls.__schema__ = schema
        schema._tables.setdefault(cls, {})


class Schema:
    def __init__(self) -> None:
        self._tables: dict[type[object], dict[int, object]] = {}

    @property
    def Table(self) -> type[Table]:
        schema = self

        class _Bound(Table, schema=schema):  # type: ignore[misc]
            def __init_subclass__(cls, **kw) -> None:
                super().__init_subclass__(schema=schema, **kw)

        return _Bound

    def add(self, row: object) -> None:
        self._tables[type(row)][id(row)] = row

    def remove(self, row: object) -> None:
        del self._tables[type(row)][id(row)]

    def all(self, table: type[object]) -> Iterator[object]:
        return iter(self._tables.get(table, {}).values())

