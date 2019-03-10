from relativity.table import Table

def mk_users():
    t = Table(['name', 'age'], ['user-id'])
    t[0] = ('alice', 42)
    t[1] = ('bob', 42)
    t[2] = ('carol', 42)
    return t


def test_rows():
    t = mk_users()
    assert set(t) == set([
        (0, 'alice', 42),
        (1, 'bob', 42),
        (2, 'carol', 42),
    ])
    del t[0]
    del t[1]
    assert set(t) == set([(2, 'carol', 42)])


def test_indices():
    t = mk_users()
    t.add_index(['name'])
    assert t.indices['name',]['bob'] == set([1])
    t.add_index(['age'])
    assert t.indices['age',][42] == set([0, 1, 2])
    del t[0]
    del t[1]
    assert t.indices['age',][42] == set([2])
