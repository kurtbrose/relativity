import dataclasses
import importlib

import pytest

from relativity.schema import Schema, Table


def test_schema_storage_and_iteration():
    schema = Schema()

    class Student(schema.Table):
        name: str

    alice = Student("alice")
    bob = Student("bob")
    schema.add(alice)
    schema.add(bob)

    assert set(schema.all(Student)) == {alice, bob}
    schema.remove(alice)
    assert list(schema.all(Student)) == [bob]


def test_table_is_dataclass_and_identity_based():
    schema = Schema()

    class Student(schema.Table):
        name: str

    a = Student("a")
    b = Student("a")

    assert dataclasses.is_dataclass(a)
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.name = "b"

    assert a != b
    assert len({a, b}) == 2


def test_shim_removed_from_mro():
    schema = Schema()

    class Student(schema.Table):
        name: str

    assert Student.__mro__ == (Student, Table, object)


def test_dataclass_transform_fallback(monkeypatch):
    import typing
    import relativity.schema as schema_module

    monkeypatch.delattr(typing, "dataclass_transform", raising=False)
    schema_module = importlib.reload(schema_module)

    schema = schema_module.Schema()

    class Student(schema.Table):
        name: str

    alice = Student("alice")
    assert dataclasses.is_dataclass(alice)
    schema.add(alice)
    assert list(schema.all(Student)) == [alice]

    monkeypatch.undo()
    importlib.reload(schema_module)
