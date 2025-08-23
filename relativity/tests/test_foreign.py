from relativity.schema import Schema, Ref
import pytest


def test_foreign_keys_and_reverse_lookup():
    schema = Schema()

    class Student(schema.Table):
        name: str

    class Course(schema.Table):
        title: str

    class Enrollment(schema.Table):
        student: Ref[Student]
        course: Ref[Course]

    schema.index(Enrollment.student)
    schema.index(Enrollment.course)

    alice = Student("alice")
    math = Course("math")
    schema.add(alice)
    schema.add(math)

    enr = Enrollment(schema.ref(alice), schema.ref(math))
    schema.add(enr)

    res = list(
        schema.all(Student, Course, Enrollment).filter(
            Student.name == "alice",
            Student == Enrollment.student,
            Course == Enrollment.course,
        )
    )
    assert res == [(alice, math, enr)]

    alice2 = schema.replace(alice, name="Alice")
    assert schema.get(enr.student) is alice2

    res = list(
        schema.all(Student, Course, Enrollment).filter(
            Student.name == "Alice",
            Student == Enrollment.student,
            Course == Enrollment.course,
        )
    )
    assert res == [(alice2, math, enr)]

    with pytest.raises(KeyError):
        schema.remove(alice2)

    schema.remove(enr)
    schema.remove(alice2)
