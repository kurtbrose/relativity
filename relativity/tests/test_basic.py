import copy


from relativity import M2M, M2MChain, M2MGraph
from relativity.tree import M2MTree


def test_m2m_basic():
    m2m = M2M()
    assert len(m2m) == 0
    assert not m2m
    m2m.add(1, 'a')
    assert m2m
    m2m.add(1, 'b')
    assert len(m2m) == 1
    assert m2m.inv['a'] == frozenset([1])
    assert set(m2m.values()) == set(['a', 'b'])
    assert m2m.inv.only('a') == M2M([('a', 1)])
    assert m2m.inv.getall(['a', 'b']) == frozenset([1])

    del m2m.inv['a']
    assert m2m[1] == frozenset(['b'])
    assert 1 in m2m
    del m2m.inv['b']
    assert 1 not in m2m
    m2m[1] = ('a', 'b')
    assert set(m2m.iteritems()) == set([(1, 'a'), (1, 'b')])
    m2m.replace(1, 2)
    assert set(m2m.iteritems()) == set([(2, 'a'), (2, 'b')])
    m2m.remove(2, 'a')
    m2m.discard(2, 'b')
    m2m.discard(2, 'b')
    assert 2 not in m2m
    m2m.update([(1, 'a'), (2, 'b')])
    assert m2m.get(2) == frozenset(['b'])
    assert m2m.get(3) == frozenset()
    assert M2M(['ab', 'cd']) == M2M(['ba', 'dc']).inv
    assert M2M(M2M(['ab', 'cd'])) == M2M(['ab', 'cd'])


def test_m2m_copy():
    def _chk_dup(dup_func):
        m2m = M2M({1:2})
        other = dup_func(m2m)
        assert other == m2m
        m2m.add(1, 3)
        assert other != m2m
        assert other[1] != m2m[1]

    _chk_dup(copy.copy)
    _chk_dup(copy.deepcopy)
    _chk_dup(M2M)
    _chk_dup(M2M.copy)


def test_m2mchain_basic():
    m2ms = M2MChain([M2M()])
    assert not m2ms
    other = M2MChain(m2ms)
    assert other == m2ms
    m2ms.add('alice', 'bob')
    assert m2ms
    m2ms = M2MChain([M2M(), M2M()])
    m2ms[:1].add('alice', 'bob')
    m2ms[1:].add('bob', 'carol')
    m2ms[:1].add('dave', 'bob')
    m2ms[:1].add('eve', 'bob')
    assert sorted(m2ms) == sorted([
        ('alice', 'bob', 'carol'),
        ('dave', 'bob', 'carol'),
        ('eve', 'bob', 'carol'),
    ])
    assert m2ms[1:] == m2ms[:, 'bob']
    assert ('alice',) in m2ms
    assert ('bob',) in m2ms[1:]
    assert 'alice' in m2ms.pairs()
    # assert 'alice' not in m2ms[1:].pairs()
    # TODO: decide what pairs() on a chain with only 1 m:m should do
    m2ms.update([
        ('april', 'alice', 'anna'),
        ('brad', 'brent', 'bruce'),
        ('cathy', 'cynthia', 'claire'),
        ('dan', 'don', 'dale')])
    assert set(m2ms.only(('april', 'brad'))) == set([
        ('april', 'alice', 'anna'),
        ('brad', 'brent', 'bruce')])


# canonical example: (city, fast food franchise, food type)


def test_m2mgraph_basic():
    m2mg = M2MGraph(
        {'letters': 'numbers', 'roman': 'numbers', 'greek': 'numbers'})
    m2mg['letters', 'numbers'].update([('a', 1), ('b', 2)])
    assert set(m2mg['letters']) == set(['a', 'b'])
    assert list(m2mg['letters', 'numbers', 'roman']) == []
    assert type(m2mg['letters', 'numbers', 'roman']) is M2MChain
    assert type(m2mg[{'letters': 'numbers', 'greek': 'numbers'}]) is M2MGraph
    M2MGraph(m2mg.rels)

    m2mg = M2MGraph({'roman': 'numbers', 'numbers': 'greek', 'greek': 'roman'})
    m2mg['roman', 'numbers'].update([('i', 1), ('v', 5)])
    m2mg['greek', 'numbers'].add('beta', 2)
    assert set(m2mg['numbers']) == set([1, 2, 5])
    assert m2mg.pairs('roman', 'numbers') == M2M(m2mg['roman', 'numbers'])
    m2mg = M2MGraph([('a', 'b'), ('a', 'c'), ('b', 'd'), ('c', 'd')])
    m2mg['a', 'b', 'd'].add(1, 2, 3)
    m2mg['a', 'c', 'd'].add('x', 'y', 'z')
    assert m2mg.pairs('a', 'd') == M2M([(1, 3), ('x', 'z')])
    m2mg.add({'a': 10, 'b': 11, 'c': 12, 'd': 13})
    assert (10, 11) in m2mg['a', 'b']
    assert (11,) in m2mg['a', 'b'][10,]
    assert (11, 13) in m2mg['b', 'd']
    assert (10, 12) in m2mg['a', 'c']
    assert (12, 13) in m2mg['c', 'd']
    m2mg.attach(M2MGraph([('d', 'e'), ('e', 'f')]))
    m2mg.replace_col('a', {1: 'cat', 10: 'dog', 'x': 'mouse'})
    assert set(m2mg['a']) == set(['cat', 'dog', 'mouse'])
    m2mg['a', ..., 'b', ..., 'd']

    m2mg = M2MGraph(['ab', 'bc'])
    m2mg['a', 'b'].add(1, 'one')
    m2mg['b', 'c'].add('one', 'uno')
    m2mg['a', 'b'].add(2, 'two')
    m2mg['b', 'c'].add('two', 'dos')
    assert set([tuple(x) for x in m2mg['a', ..., 'b', ..., 'c']]) == set([
        (1, 'one', 'uno'),
        (2, 'two', 'dos'),
    ])
    assert ('a', 'c') not in m2mg
    m2mg['a', 'c'] = m2mg['a', ..., 'c']
    assert ('a', 'c') in m2mg


#TODO: test M2MGraph.add_rel


def test_listeners():
    """
    test that listeners work okay by ensuring that
    a dummy listener which simply mirrors the state
    of the base M2M remains in sync
    """
    class MirrorListener(object):
        def __init__(self):
            self.data = M2M()
        def notify_add(self, key, val):
            self.data.add(key, val)
        def notify_remove(self, key, val):
            print('remove', key, val)
            self.data.remove(key, val)
    test = M2M()
    test.listeners.append(MirrorListener())
    test.inv.listeners.append(MirrorListener())
    def chk():
        assert test == test.listeners[0].data
        assert test.inv == test.inv.listeners[0].data
    test.add(1, 1)
    chk()
    test.remove(1, 1)
    chk()
    test.update(M2M([(1, 1), (2, 2)]))
    print(test)
    chk()
    test[3] = [4]
    print(test)
    chk()
    test.pop(2)
    chk()
    del test[3]
    chk()
    test.discard(1, 1)
    chk()
