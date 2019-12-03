from relativity import M2M


class M2MTree(object):
    """
    An M2MTree is an internal node of a tree
    that keeps track of pairs across a sequence
    of underlying M2M dicts.

    The intention is that this tree keeps track
    of relationships and some other data structure
    (e.g. M2MGraph, Table) manages the M2M relationships
    that form the leaves of the tree.
    """
    def __init__(self, left, right):
        self.left, self.right = left, right
        if type(left) is M2MTree:
            left.add_parent(self)
        if type(right) is M2MTree:
            right.add_parent(self)
        self.pair_counts = {}
        self.pairs = M2M()
        self.parents = []

    def add_parent(self, parent):
        assert type(parent) is M2MTree
        self.parents.append(parent)

    def _pairs(self, child, a, b):
        pairs = []
        if child is self.left:
            for right in self.right.get(b):
                pairs.append((a, right))
        elif child is self.right:
            if type(self.left) is M2MTree:
                for left in self.left.pairs.inv.get(a):
                    pairs.append((left, b))
            else:
                for left in self.left.inv.get(a):
                    pairs.append((left, b))
        else:
            raise ValueError('{} is not a child of this tree'.format(child))
        return pairs

    def notify_add(self, child, a, b):
        pairs = self._pairs(child, a, b)
        for pair in pairs:
            if pair not in self.pair_counts:
                self.pair_counts[pair] = 1
                self.pairs.add(*pair)
                for parent in self.parents:
                    parent.notify_add(self, *pair)
            else:
                self.pair_counts[pair] += 1

    def notify_remove(self, child, a, b):
        pairs = self._pairs(child, a, b)
        for pair in pairs:
            assert pair in self.pair_counts
            if self.pair_counts[pair] == 1:
                del self.pair_counts[pair]
                self.pairs.remove(*pair)
                for parent in self.parents:
                    parent.notify_remove(self, *pair)
            else:
                self.pair_counts[pair] -= 1

    def __contains__(self, pair):
        return pair in self.pair_counts

    def __getitem__(self, key):
        return self.pairs[key]

    def get(self, key):
        return self.pairs.get(key)

    def iteritems(self):
        return self.pairs.iteritems()


class TreeIndexer(object):
    """
    manages construction and maintenance of trees
    """
    # TODO: can M2MGraph public API be extended to support this?
    def __init__(self, pair_m2m_map):
        self.pair_m2m_map = pair_m2m_map
        self.tree_map = {}  # {(lhs, rhs): M2MTree}
        self.parents_of = {id(m2m): [] for m2m in pair_m2m_map.values()}

    def add_index(self, *cols):
        # this would synergize well with find_paths from M2MGraph
        pairs = tuple(zip(cols[:-1], cols[1:]))
        for pair in pairs:
            assert pair in self.pair_m2m_map
        assert len(pairs) >= 2
        self._add_index2(pairs)

    def _add_index2(self, pairs):
        cur_col_pair = (pairs[0][0], pairs[-1][1])
        if cur_col_pair in self:
            return self[cur_col_pair]
        if len(pairs) > 3:
            split = len(pairs) // 2
            left_pairs, right_pairs = pairs[:split], pairs[split:]
            left, right = self._add_index2(left_pairs), self._add_index2(right_pairs)
        if len(pairs) == 3:  # asymmetric case
            left, right = self._add_index2(pairs[:2]), self[pairs[2]]
        if len(pairs) == 2:  # stopping case
            left, right = self[pairs[0]], self[pairs[1]]
        if len(pairs) < 2:
            assert False, "shouldn't be able to get here"
        ret = self.tree_map[cur_col_pair] = M2MTree(left, right)
        if id(left) in self.parents_of:
            self.parents_of[id(left)].append(ret)
        if id(right) in self.parents_of:
            self.parents_of[id(right)].append(ret)
        return ret

    def notify_add(self, rel, a, b):
        m2m = self.pair_m2m_map[rel]
        for parent in self.parents_of[id(m2m)]:
            parent.notify_add(m2m, a, b)

    def notify_remove(self, rel, a, b):
        m2m = self.pair_m2m_map[rel]
        for parent in self.parents_of[id(m2m)]:
            parent.notify_remove(m2m, a, b)

    def __getitem__(self, pair):
        if pair in self.pair_m2m_map:
            return self.pair_m2m_map[pair]
        return self.tree_map[pair]

    def __contains__(self, pair):
        return pair in self.pair_m2m_map or pair in self.tree_map
