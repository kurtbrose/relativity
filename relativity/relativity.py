_PAIRING = object()  # marker


# TODO: fill out the rest of dict API and inherit from dict
class M2M(object):
    """
    a dict-like entity that represents a many-to-many relationship
    between two groups of objects

    behaves like a dict-of-tuples; also has .inv which is kept
    up to date which is a dict-of-tuples in the other direction

    also, can be used as a directed graph among hashable python objects
    """
    def __init__(self, items=None):
        self.data = {}
        if type(items) is tuple and items and items[0] is _PAIRING:
            self.inv = items[1]
        else:
            self.inv = self.__class__((_PAIRING, self))
            if items:
                self.update(items)
        return

    def get(self, key, default=frozenset()):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        return frozenset(self.data[key])

    def __setitem__(self, key, vals):
        vals = set(vals)
        if key in self:
            to_remove = self.data[key] - vals
            vals -= self.data[key]
            for val in to_remove:
                self.remove(key, val)
        for val in vals:
            self.add(key, val)

    def __delitem__(self, key):
        for val in self.data.pop(key):
            self.inv.data[val].remove(key)
            if not self.inv.data[val]:
                del self.inv.data[val]

    def update(self, iterable):
        """given an iterable of (key, val), add them all"""
        if type(iterable) is type(self):
            other = iterable
            for k in other.data:
                if k not in self.data:
                    self.data[k] = other.data[k]
                else:
                    self.data[k].update(other.data[k])
            for k in other.inv.data:
                if k not in self.inv.data:
                    self.inv.data[k] = other.inv.data[k]
                else:
                    self.inv.data[k].update(other.inv.data[k])
        elif callable(getattr(iterable, 'keys', None)):
            for k in iterable.keys():
                self.add(k, iterable[k])
        else:
            for key, val in iterable:
                self.add(key, val)
        return

    def add(self, key, val):
        if key not in self.data:
            self.data[key] = set()
        self.data[key].add(val)
        if val not in self.inv.data:
            self.inv.data[val] = set()
        self.inv.data[val].add(key)

    def remove(self, key, val):
        self.data[key].remove(val)
        if not self.data[key]:
            del self.data[key]
        self.inv.data[val].remove(key)
        if not self.inv.data[val]:
            del self.inv.data[val]

    def replace(self, key, newkey):
        """
        replace instances of key by newkey
        """
        if key not in self.data:
            return
        self.data[newkey] = fwdset = self.data.pop(key)
        for val in fwdset:
            revset = self.inv.data[val]
            revset.remove(key)
            revset.add(newkey)

    def iteritems(self):
        for key in self.data:
            for val in self.data[key]:
                yield key, val

    def keys(self):
        return self.data.keys()

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return self.data.__iter__()

    def __len__(self):
        return self.data.__len__()

    def __eq__(self, other):
        return type(self) == type(other) and self.data == other.data

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r)' % (cn, list(self.iteritems()))


import itertools


_FROM_SLICE = object()  # marker to let M2MChain know it is being loaded with a slices


class M2MChain(object):
    """
    Represents a sequence of ManyToMany relationships

    Constructed with an ordered sequence of columns,
    relationships between values of those columns are stored.
    """
    def __init__(self, *cols):
        if len(cols) < 2:
            raise ValueError('need at least two columns; got {}'.format(cols))
        if cols[0] is _FROM_SLICE:
            self.data, self.cols = cols[1:]
        else:
            if len(set(cols)) != len(cols):
                raise ValueError('column names must be unique')
            self.cols = cols
            col_pairs = zip(cols[:-1], cols[1:])
            self.data = dict([
                ((lhs, rhs), M2M()) for lhs, rhs in col_pairs])

    def __getitem__(self, key):
        if key in self.cols:
            # if selecting a single column, give back all the unique values
            # for that column
            return self._all_col(key)
        if type(key) is tuple:
            if len(key) == 2:
                if key in self.data:
                    return self.data[key]
                return self.data[key[1], key[0]].inv
            # taking a larger slice -- this will return a conjoined M2MChain
            # check that cols are contiguous and in consistent direction
            first_idx, second_idx = self.cols.index(key[0]), self.cols.index(key[1])
            step = second_idx - first_idx
            assert step in (1, -1)
            cur_idx = second_idx
            for col in key[2:]:
                last_idx, cur_idx = cur_idx, self.cols.index(col)
                assert cur_idx - last_idx == step
            col_pairs = zip(key[:-1], key[1:])
            data = {}
            for lhs, rhs in col_pairs:
                if step == 1:
                    data[lhs, rhs] = self.data[lhs, rhs]
                else:
                    data[lhs, rhs] = self.data[rhs, lhs].inv
            return M2MChain(_FROM_SLICE, data, key)

    def _all_col(self, col):
        """
        all values for a certain column -- not sure if this should stay or not
        """
        if col == self.cols[-1]:
            return list(self.data[self.cols[-2], self.cols[-1]].inv)
        if col == self.cols[0]:
            return list(self.data[self.cols[0], self.cols[1]])
        idx = self.cols.index(col)
        return list(
            set(self.data[self.cols[idx], self.cols[idx + 1]].keys()) +
            set(self.data[self.cols[idx + 1], self.cols[idx]].inv.keys()))

    def iter_values(self):
        """
        as __iter__, but give back results in the form of dicts
        """
        for vals in iter(self):
            yield dict(zip(self.cols, vals))

    def add(self, *vals):
        assert len(self.cols) == len(vals)
        col_val_pairs = zip(
            zip(self.cols[:-1], self.cols[1:]),
            zip(vals[:-1], vals[1:]))
        for col_pair, val_pair in col_val_pairs:
            self[col_pair].add(*val_pair)

    def __eq__(self, other):
        return type(self) is type(other) and self.cols == other.cols and self.data == other.data

    def __repr__(self):
        return "M2MChain({}, ...)".format(self.cols)

    def __iter__(self):
        """
        iterate over all of the possible paths through the
        chain of many to many dicts

        these are sequences of values, such that a value
        from M2M N is the key in M2M N+1 across the whole
        set of M2Ms
        """
        col_pairs = zip(self.cols[:-1], self.cols[1:])
        m2ms = [self.data[pair] for pair in col_pairs]
        return itertools.chain.from_iterable(
            [_join_all(key, m2ms[0], m2ms[1:]) for key in m2ms[0]])


def _join_all(key, nxt, rest, sofar=()):
    if not rest:
        row = []
        while sofar:
            row.append(sofar[0])
            sofar = sofar[1]
        row.reverse()
        return [row + [key, val] for val in nxt.get(key)]
    return itertools.chain.from_iterable(
        [_join_all(val, rest[0], rest[1:], (key, sofar)) for val in nxt.get(key)])


def _is_connected(graph):
    """
    given a M2M dict representing a set of edges,
    returns if the graph is fully connected
    """
    to_check = [list(graph.keys())[0]]
    reached = set(to_check)
    while to_check:
        cur = to_check.pop()
        nxt = (set(graph.get(cur)) | set(graph.inv.get(cur)))
        nxt -= reached  # avoid loops
        to_check.extend(nxt)
        reached.update(nxt)
    return reached == (set(graph.keys()) | set(graph.inv.keys()))


class M2MGraph(object):
    """
    represents a graph, where each node is a set of keys,
    and each edge is a M2M dict connecting two sets
    of keys

    this is good at representing a web of relationships
    from which various sub relationships can be extracted
    for inspection / modification via [] operator

    the node set is specified as a M2M dict:
    {a: b, b: c, b: d} specifies a graph with nodes
    a, b, c, d; and edges (a-b, b-c, b-d)
    """
    def __init__(self, relationships, data=None):
        relationships = M2M(relationships)
        assert _is_connected(relationships)
        edge_m2m_map = {}
        cols = M2M()
        for lhs, rhs in relationships.iteritems():
            # check that only one direction is present
            assert lhs not in relationships.get(rhs)
            if data:
                if (lhs, rhs) in data:
                    edge_m2m_map[lhs, rhs] = data[lhs, rhs]
                elif (rhs, lhs) in data:
                    edge_m2m_map[lhs, rhs] = data[rhs, lhs].inv
            edge_m2m_map[lhs, rhs] = M2M()
            cols.add(lhs, (lhs, rhs))
            cols.add(rhs, (lhs, rhs))
        self.edge_m2m_map = edge_m2m_map
        self.cols = dict(cols)

    def __getitem__(self, key):
        """
        return a M2M, M2MChain, or M2MGraph
        over the same underlying data structure for easy
        mutation
        """
        if type(key) is dict or type(key) is M2M:
            return M2MGraph(
                key,
                dict([((lhs, rhs), self[lhs, rhs]) for lhs, rhs in key.items()]))
        if type(key) is list:
            key = tuple(key)
        if key in self.cols:
            return self._all_col(key)
        if type(key) is tuple:
            if len(key) == 2:
                if key in self.edge_m2m_map:
                    return self.edge_m2m_map[key]
                else:
                    rkey = (key[1], key[0])
                    if rkey in self.edge_m2m_map:
                        return self.edge_m2m_map[rkey].inv
                    raise KeyError("relationship {} not present in graph".format(key))
            elif len(key) == 3 and key[1] is Ellipsis:
                return self.pairs(key[0], key[2])
            else:
                col_pairs = zip(key[:-1], key[1:])
                filtered_col_pairs = []
                assert col_pairs[0][0] is not Ellipsis  # ... at the beginning is invalid
                for lhs_col_pair, rhs_col_pair in zip(col_pairs[:-1], col_pairs[1:]):
                    if lhs_col_pair[0] is Ellipsis:
                        continue  # skip, was handled by lhs
                    if lhs_col_pair[1] is Ellipsis:
                        assert rhs_col_pair[0] is Ellipsis
                        # join ... in the middle via pairs
                        lhslhs, rhsrhs = lhs_col_pair[0], rhs_col_pair[1]
                        filtered_col_pairs.append(((lhslhs, rhsrhs), self.pairs(lhslhs, rhsrhs)))
                        continue
                    filtered_col_pairs.append((lhs_col_pair, self[lhs_col_pair]))
                assert col_pairs[-1][1] is not Ellipsis  # ... on the end is invalid
                if col_pairs[-1][0] is not Ellipsis:
                    filtered_col_pairs.append((col_pairs[-1], self[col_pairs[-1]]))
                filtered_cols = tuple([k for k in key if k is not Ellipsis])
                return M2MChain(_FROM_SLICE, dict(filtered_col_pairs), filtered_cols)
        raise KeyError(key)

    def _all_col(self, col):
        """get all the values for a given column"""
        sofar = set()
        for edge in self.cols[col]:
            m2m = self[edge]
            if col == edge[0]:
                m2m = self[edge]
            if col == edge[1]:
                m2m = self[edge].inv
            sofar.update(m2m.keys())
        return list(sofar)

    def pairs(self, lhs, rhs, paths=None, ignore=None):
        """
        get all the unique pairs of values from lhs col and rhs col

        ignore is a set of column names to exclude from building paths

        paths is a list-of-lists of column names; if specified, will
        follow exactly the chain of relationships specified by
        each list of column names in paths rather than searching
        for paths between lhs and rhs columns
        """
        assert lhs in self.cols
        assert rhs in self.cols
        if ignore is None:
            ignore = set()
        if paths is None:
            paths = self._all_paths(lhs, rhs, ignore)
            if not paths:
                raise ValueError('no paths between col {} and {}'.format(lhs, rhs))
        pairs = M2M()
        for path in paths:
            m2ms = self[path]
            if type(m2ms) is M2M:
                pairs.update(m2ms.iteritems())
            else:
                for row in m2ms:
                    pairs.add(row[0], row[-1])
        return pairs

    def _all_paths(self, lhs, rhs, already_visited):
        """
        lhs - start col
        rhs - end col
        already_visited - cols that are already on the current
        path to avoid loops
        returns [[str]]
        """
        if lhs == rhs:
            return [[lhs]]
        paths = []
        for col_pair in self.cols[lhs]:
            assert lhs in col_pair
            nxt = col_pair[1] if lhs == col_pair[0] else col_pair[0]
            if nxt in already_visited:
                continue
            paths.extend(
                [[lhs] + sub_path for sub_path in self._all_paths(
                    nxt, rhs, set([lhs]) | already_visited)])
        return paths

    def add(self, row):
        """
        given a row-dict that specifies a bunch of values,
        add these values to all of the direct relationships
        among the columns specified by the row-dict keys
        """
        assert set(row) <= set(self.cols)
        to_add = []
        for lhs in row:
            exists = False
            for rhs in row:
                for key in (lhs, rhs), (rhs, lhs):
                    if key in self.edge_m2m_map:
                        to_add.append((key, row[key[0]], row[key[1]]))
                        exists = True
            if not exists:
                raise ValueError('could not find any relationships for col {}'.format(lhs))
        for key, lval, rval in to_add:
            self[key].add(lval, rval)

    def attach(self, other):
        """
        attach all of the relationships from other into the
        columns and relationships of the current graph

        the underlying data structures remain connected -- modifications
        of self or other will be reflected

        (this is a relatively cheap operation since only meta-data
        is modified)

        the set of relationships in self and other must be disjoint,
        and there must be at least one link between the columns
        of self and other
        """
        assert type(other) is type(self)
        # TODO: allow attaching of sequences?
        # check that relationships do not overlap
        overlaps = set([frozenset(e) for e in self.edge_m2m_map]) & (
            set([frozenset(e) for e in other.edge_m2m_map]))
        if overlaps:
            raise ValueError('relationships are specified by both graphs: {}'.format(
                ", ".join([tuple(e) for e in overlaps])))
        # check that columns do overlap
        if not set(self.cols) & set(other.cols):
            raise ValueError('graphs are disjoint {}, {}'.format(
                list(self.cols), list(other.cols)))
        self.edge_m2m_map.update(other.edge_m2m_map)
        for col in other.cols:
            if col in self.cols:
                self.cols[col] |= other.cols[col]
            else:
                self.cols[col] = other.cols[col]

    def replace_col(self, col, valmap):
        """
        replace every value in col by the value in valmap
        raises KeyError if there is a value not in valmap
        """
        for key in self.cols[col]:
            if col == key[0]:
                m2m = self.edge_m2m_map[key]
            else:
                m2m = self.edge_m2m_map[key].inv
            for oldval, newval in valmap.items():
                m2m.replace(oldval, newval)

    def add_rel(self, from_, to, m2m):
        """add a relationship"""
        assert (to, from_) not in self.edge_m2m_map
        assert from_ in self.cols or to in self.cols
        assert type(m2m) is M2M
        self.edge_m2m_map[from_, to] = m2m
        if from_ not in self.cols:
            self.cols[from_] = set()
        self.cols[from_].add((from_, to))
        if to not in self.cols:
            self.cols[to] = set()
        self.cols[to].add((from_, to))

    def build_chain(self, *cols):
        """
        build a new M2MChain over a set of not neccesarily contiguous
        columns

        relatively expensive because it copies the underlying data structure
        """
        return M2MChain(
            _FROM_SLICE,
            dict([
                (col_pair, M2M(self.pairs(col_pair[0], col_pair[1])))
                for col_pair in zip(cols[:-1], cols[1:])]),
            cols)

    def filtered(self, filters):
        """
        return an M2MGraph with all columns filtered by predicates
        specified in filters dict
        """
        f_copy = M2MGraph(self.edge_m2m_map.keys())
        for lhs, rhs in self.edge_m2m_map:
            m2m = self.edge_m2m_map[lhs, rhs]
            if lhs not in filters and rhs not in filters:
                f_copy[lhs, rhs].update(m2m)
                continue
            dst = f_copy[lhs, rhs]
            for key, val in m2m.iteritems():
                if lhs not in filters or filters[lhs](key):
                    if rhs not in filters or filters[rhs](key):
                        dst.add(key, val)
        return f_copy

    def __eq__(self, other):
        return type(self) is type(other) and self.edge_m2m_map == other.edge_m2m_map

    def __contains__(self, rel):
        return rel in self.edge_m2m_map

    def __repr__(self):
        return "M2MGraph({}, ...)".format(self.edge_m2m_map.keys())
