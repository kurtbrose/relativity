from relativity import tree, M2M

def test():
    cols = 'abcdefghi'
    idx = tree.TreeIndexer({(a, b): M2M() for a, b in zip(cols[:-1], cols[1:])})
    idx.add_index(*'abcde')
    idx.add_index(*'abcdefghi')

    for colpair in zip(cols[:-1], cols[1:]):
        for i in range(3):
            a, b = colpair[0] + str(i), colpair[1] + str(i)
            idx[colpair].add(a, b)
            idx.notify_add(colpair, a, b)

    for lhs in cols:
        for rhs in cols:
            if (lhs, rhs) not in idx:
                continue
            assert set(idx[lhs, rhs].iteritems()) == set(
                [(lhs + str(i), rhs + str(i)) for i in range(3)])


def test_notify_remove_updates_pairs():
    """TreeIndexer should drop pairs when underlying data is removed."""
    idx = tree.TreeIndexer({('a', 'b'): M2M(), ('b', 'c'): M2M()})
    idx.add_index('a', 'b', 'c')

    # establish two paths through the tree
    idx['a', 'b'].add('x', 'y')
    idx.notify_add(('a', 'b'), 'x', 'y')
    idx['b', 'c'].add('y', 'z')
    idx.notify_add(('b', 'c'), 'y', 'z')

    idx['a', 'b'].add('w', 'y')
    idx.notify_add(('a', 'b'), 'w', 'y')

    assert ('x', 'z') in idx['a', 'c']
    assert ('w', 'z') in idx['a', 'c']

    # remove one edge and notify the indexer
    idx['a', 'b'].remove('x', 'y')
    idx.notify_remove(('a', 'b'), 'x', 'y')

    assert ('x', 'z') not in idx['a', 'c']
    assert ('w', 'z') in idx['a', 'c']
