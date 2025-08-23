import pytest

from relativity.schema import Schema, Table, Eq


class CountingExpr(Eq):
    def __init__(self, base):
        self.count = 0
        super().__init__(base.left, base.right)

    def eval(self, env):
        self.count += 1
        return super().eval(env)


def test_index_updates_and_queries():
    schema = Schema()

    class Student(schema.Table):
        name: str
        parent: str

    expr = Student.parent
    schema.index(expr)

    a = Student("a", "p1")
    b = Student("b", "p2")
    schema.add(a)
    schema.add(b)
    pred = Student.parent == "p1"
    assert list(schema.all(Student).filter(pred)) == [a]

    c = Student("c", "p1")
    schema.add(c)
    assert set(schema.all(Student).filter(pred)) == {a, c}

    schema.remove(a)
    assert list(schema.all(Student).filter(pred)) == [c]


def test_query_planner_uses_index():
    schema = Schema()

    class Student(schema.Table):
        name: str

    for n in ["a", "b", "c", "d"]:
        schema.add(Student(n))

    expr = CountingExpr(Student.name == "a")
    list(schema.all(Student).filter(expr))
    assert expr.count == 4

    schema.index(Student.name)

    expr2 = CountingExpr(Student.name == "a")
    list(schema.all(Student).filter(expr2))
    assert expr2.count == 0
