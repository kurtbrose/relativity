from relativity import tree, M2M

def test():
    cols = 'abcdefghi'
    idx = tree.TreeIndexer({(a, b): M2M() for a, b in zip(cols[:-1], cols[1:])})
    idx.add_index(*'abcde')
    idx.add_index(*'abcdefghi')
