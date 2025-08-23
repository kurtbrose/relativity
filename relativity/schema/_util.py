from __future__ import annotations

from dataclasses import Field, field


def _dict_field() -> Field:
    return field(default_factory=dict)


__all__ = ["_dict_field"]
