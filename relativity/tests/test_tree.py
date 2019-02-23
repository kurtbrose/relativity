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
