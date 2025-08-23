import pytest

from relativity.schema import Schema, Table, Eq, Gt, Tuple


class CountingExpr(Eq):
    def __init__(self, base):
        object.__setattr__(self, "count", 0)
        super().__init__(base.left, base.right)

    def eval(self, env):
        object.__setattr__(self, "count", self.count + 1)
        return super().eval(env)


class CountingGt(Gt):
    def __init__(self, base):
        object.__setattr__(self, "count", 0)
        super().__init__(base.left, base.right)

    def eval(self, env):
        object.__setattr__(self, "count", self.count + 1)
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


def test_unique_index_rejects_duplicate_add():
    schema = Schema()

    class Student(schema.Table):
        name: str

    schema.index(Student.name, unique=True)
    schema.add(Student("a"))
    with pytest.raises(KeyError):
        schema.add(Student("a"))


def test_ordered_index_updates_and_queries():
    schema = Schema()

    class Student(schema.Table):
        name: str
        score: int

    schema.ordered_index(Student.score)

    a = Student("a", 10)
    b = Student("b", 20)
    c = Student("c", 30)
    for s in (a, b, c):
        schema.add(s)

    pred_gt = Student.score > 15
    pred_lt = Student.score < 25
    assert set(schema.all(Student).filter(pred_gt)) == {b, c}
    assert set(schema.all(Student).filter(pred_lt)) == {a, b}

    schema.remove(b)
    assert list(schema.all(Student).filter(pred_gt)) == [c]


def test_range_query_planner_uses_index():
    schema = Schema()

    class Student(schema.Table):
        name: str
        score: int

    for i in range(4):
        schema.add(Student(str(i), i))

    expr = CountingGt(Student.score > 1)
    list(schema.all(Student).filter(expr))
    assert expr.count == 4

    schema.ordered_index(Student.score)

    expr2 = CountingGt(Student.score > 1)
    list(schema.all(Student).filter(expr2))
    assert expr2.count == 0


def test_composite_index_queries():
    schema = Schema()

    class Student(schema.Table):
        first: str
        last: str

    schema.index(Student.first, Student.last)

    a = Student("a", "x")
    b = Student("a", "y")
    schema.add(a)
    schema.add(b)

    pred = Tuple(Student.first, Student.last) == ("a", "x")
    assert list(schema.all(Student).filter(pred)) == [a]


def test_composite_ordered_index_range_queries():
    schema = Schema()

    class Student(schema.Table):
        score: int
        name: str

    schema.ordered_index(Student.score, Student.name)

    a = Student(10, "a")
    b = Student(20, "b")
    c = Student(20, "c")
    for s in (a, b, c):
        schema.add(s)

    pred = Tuple(Student.score, Student.name) >= (20, "b")
    assert set(schema.all(Student).filter(pred)) == {b, c}
