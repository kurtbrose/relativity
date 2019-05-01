import pytest

from relativity.table import Table


def test():
    users = Table(['name', 'age'])
    users.insert('alice', 42)
    users.insert('bob', 42)
    users.insert('carol', 42)
    assert set(users) == set([
        (0, 'alice', 42),
        (1, 'bob', 42),
        (2, 'carol', 42),
    ])
    del users[0]
    del users[1]
    assert set(users) == set([(2, 'carol', 42)])


"""
def test_new_api():
    switchboard = Table(['vendor-id', 'matter-id'])
    matter_oa_foo = Table(['matter-id', 'foo'])
    switchboard = switchboard.join(matter_oa_foo, on="matter-id")
"""