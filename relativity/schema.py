from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Type, Any
from typing import dataclass_transform


class Schema:
    def __init__(self) -> None:
        self._tables: Dict[type, Dict[int, Any]] = {}
        schema = self

        @dataclass_transform()
        class Table:
            def __init_subclass__(cls, **kwargs):  # type: ignore[override]
                dataclass(eq=False, frozen=True)(cls)
                schema._tables.setdefault(cls, {})

        self.Table = Table

    def add(self, row: Any) -> None:
        self._tables[row.__class__][id(row)] = row

    def remove(self, row: Any) -> None:
        del self._tables[row.__class__][id(row)]

    def all(self, table: Type[Any]) -> Iterator[Any]:
        return iter(self._tables.get(table, {}).values())
