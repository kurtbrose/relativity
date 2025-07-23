from relativity import M2M

def test_replace_merges_when_target_exists():
    m2m = M2M()
    m2m.add(1, 'a')
    m2m.add(2, 'b')
    m2m.add(2, 'c')
    m2m.replace(1, 2)
    assert set(m2m[2]) == {'a', 'b', 'c'}
    assert 1 not in m2m
    for val in ['a', 'b', 'c']:
        assert m2m.inv[val] == frozenset([2])
