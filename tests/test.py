from relativity import *


def test():
    m2m = Relation()
    m2m.add(1, 'a')
    m2m.add(1, 'b')
    assert m2m[1] == ('a', 'b')
    assert m2m.inv['a'] == (1,)
    del m2m.inv['a']
    assert m2m[1] == ('b',)
    assert 1 in m2m
    del m2m.inv['b']
    assert 1 not in m2m
    m2m[1] = ('a', 'b')
    assert set(m2m.iteritems()) == set([(1, 'a'), (1, 'b')])
    m2m.replace(1, 2)
    assert set(m2m.iteritems()) == set([(2, 'a'), (2, 'b')])
    m2m.remove(2, 'a')
    m2m.remove(2, 'b')
    assert 2 not in m2m
    m2m.update([(1, 'a'), (2, 'b')])
    assert m2m.get(2) == ('b',)
    assert m2m.get(3) == ()
    assert Relation(['ab', 'cd']) == Relation(['ba', 'dc']).inv
    assert Relation(Relation(['ab', 'cd'])) == Relation(['ab', 'cd'])

    m2ms = RelChain('employee', 'manager', 'director')
    m2ms['employee', 'manager'].add('alice', 'bob')
    m2ms['manager', 'director'].add('bob', 'carol')
    m2ms['employee', 'manager'].add('dave', 'bob')
    m2ms['employee', 'manager'].add('eve', 'bob')
    assert sorted(m2ms) == sorted([
        ['alice', 'bob', 'carol'],
        ['dave', 'bob', 'carol'],
        ['eve', 'bob', 'carol'],
    ])

    m2ms = RelChain('letters', 'numbers', 'greek', 'roman')
    m2ms['letters', 'numbers'].add('a', 1)
    m2ms['numbers', 'greek'].add(1, 'alpha')
    m2ms['greek', 'roman'].add('alpha', 'I')
    m2ms['letters', 'numbers'].add('b', 2)
    m2ms['numbers', 'greek'].add(2, 'beta')
    m2ms['greek', 'roman'].add('beta', 'II')
    assert list(m2ms) == [['a', 1, 'alpha', 'I'], ['b', 2, 'beta', 'II']]

    assert list(m2ms['letters', 'numbers', 'greek']
        ) == [['a', 1, 'alpha'], ['b', 2, 'beta']]
    assert m2ms['letters'] == ['a', 'b']

    m2mg = ManyToManyGraph(
        {'letters': 'numbers', 'roman': 'numbers', 'greek': 'numbers'})
    m2mg['letters', 'numbers'].update([('a', 1), ('b', 2)])
    assert set(m2mg['letters']) == set(['a', 'b'])
    assert list(m2mg['letters', 'numbers', 'roman']) == []
    assert type(m2mg['letters', 'numbers', 'roman']) is RelChain
    assert type(m2mg[{'letters': 'numbers', 'greek': 'numbers'}]) is ManyToManyGraph
    ManyToManyGraph(m2mg.edge_m2m_map.keys())

    m2mg = ManyToManyGraph({'roman': 'numbers', 'numbers': 'greek', 'greek': 'roman'})
    m2mg['roman', 'numbers'].update([('i', 1), ('v', 5)])
    m2mg['greek', 'numbers'].add('beta', 2)
    assert set(m2mg['numbers']) == set([1, 2, 5])
    assert m2mg.pairs('roman', 'numbers') == set(m2mg['roman', 'numbers'].iteritems())
    m2mg = ManyToManyGraph([('a', 'b'), ('a', 'c'), ('b', 'd'), ('c', 'd')])
    m2mg['a', 'b', 'd'].add(1, 2, 3)
    m2mg['a', 'c', 'd'].add('x', 'y', 'z')
    assert m2mg.pairs('a', 'd') == set([(1, 3), ('x', 'z')])
    m2mg.add({'a': 10, 'b': 11, 'c': 12, 'd': 13})
    assert 11 in m2mg['a', 'b'][10]
    assert 13 in m2mg['b', 'd'][11]
    assert 12 in m2mg['a', 'c'][10]
    assert 13 in m2mg['c', 'd'][12]
    m2mg.attach(ManyToManyGraph([('d', 'e'), ('e', 'f')]))
    m2mg.replace_col('a', {1: 'cat', 10: 'dog', 'x': 'mouse'})
    assert set(m2mg['a']) == set(['cat', 'dog', 'mouse'])
    m2mg.build_chain('a', 'b', 'd')