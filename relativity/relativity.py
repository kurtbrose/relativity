from typing import Any, Iterable, Iterator, FrozenSet, Tuple, TypeVar, Generic

# Generic key and value type variables used throughout M2M
K = TypeVar("K")
V = TypeVar("V")

# Many-to-many mapping implemented as a full ``dict`` subclass
class M2M(dict, Generic[K, V]):
    """
    a dict-like entity that represents a many-to-many relationship
    between two groups of objects

    behaves like a dict-of-tuples; also has .inv which is kept
    up to date which is a dict-of-tuples in the other direction

    also, can be used as a directed graph among hashable python objects
    """
    __slots__ = ('inv', 'listeners')

    def __init__(self, items: Iterable[tuple[K, V]] | "M2M[K, V]" | None = None):
        dict.__init__(self)
        self.listeners: list[Any] = []
        self.inv: M2M[V, K] = self.__class__.__new__(self.__class__)
        dict.__init__(self.inv)
        self.inv.listeners = []
        self.inv.inv = self
        if items.__class__ is self.__class__:
            dict.update(self, {k: set(v) for k, v in dict.items(items)})
            dict.update(self.inv, {k: set(v) for k, v in dict.items(items.inv)})
            return
        if items:
            self.update(items)


    def _notify_add(self, key: K, val: V) -> None:
        for listener in self.listeners:
            listener.notify_add(key, val)
        for listener in self.inv.listeners:
            listener.notify_add(val, key)

    def _notify_remove(self, key: K, val: V) -> None:
        for listener in self.listeners:
            listener.notify_remove(key, val)
        for listener in self.inv.listeners:
            listener.notify_remove(val, key)

    def get(self, key: K, default: FrozenSet[V] = frozenset()) -> FrozenSet[V]:
        try:
            return self[key]
        except KeyError:
            return default

    def getall(self, keys: Iterable[K]) -> FrozenSet[V]:
        """
        since an M2M maps a key to a set of results
        rather than a single result, unlike a normal dict
        an M2M can combine the results of many keys together
        without changing the return type
        """
        empty, sofar = set(), set()
        for key in keys:
            sofar |= dict.get(self, key, empty)
        return frozenset(sofar)

    def pop(self, key: K) -> FrozenSet[V]:
        val = frozenset(dict.__getitem__(self, key))
        del self[key]
        return val

    def __getitem__(self, key: K) -> FrozenSet[V]:
        return frozenset(dict.__getitem__(self, key))

    def __setitem__(self, key: K, vals: Iterable[V]) -> None:
        vals = set(vals)
        if key in self:
            current = dict.__getitem__(self, key)
            to_remove = current - vals
            vals -= current
            for val in to_remove:
                self.remove(key, val)
        for val in vals:
            self.add(key, val)

    def __delitem__(self, key: K) -> None:
        for val in dict.pop(self, key):
            if self.listeners:
                self._notify_remove(key, val)
            rev = dict.__getitem__(self.inv, val)
            rev.remove(key)
            if not rev:
                del self.inv[val]

    def update(self, iterable: Iterable[tuple[K, V]] | "M2M[K, V]" | dict[K, V]) -> None:
        """given an iterable of (key, val), add them all"""
        if type(iterable) is type(self):
            for k, vals in dict.items(iterable):
                for v in vals:
                    self.add(k, v)
        elif callable(getattr(iterable, 'keys', None)):
            for k in iterable.keys():
                self.add(k, iterable[k])
        else:
            for key, val in iterable:
                self.add(key, val)
    
    def only(self, keys: Iterable[K]) -> "M2M[K, V]":
        """
        return a new M2M with only the data associated
        with the corresponding keys
        """
        return M2M([
            item for item in self.iteritems() if item[0] in keys])

    def add(self, key: K, val: V) -> None:
        if key not in self:
            dict.__setitem__(self, key, set())
        dict.__getitem__(self, key).add(val)
        if val not in self.inv:
            dict.__setitem__(self.inv, val, set())
        dict.__getitem__(self.inv, val).add(key)
        self._notify_add(key, val)

    def remove(self, key: K, val: V) -> None:
        fwd = dict.__getitem__(self, key)
        fwd.remove(val)
        if not fwd:
            del self[key]
        rev = dict.__getitem__(self.inv, val)
        rev.remove(key)
        if not rev:
            del self.inv[val]
        self._notify_remove(key, val)

    def discard(self, key: K, val: V) -> None:
        if key not in self or val not in self.inv:
            return
        self.remove(key, val)

    def replace(self, key: K, newkey: K) -> None:
        """
        replace instances of key by newkey
        """
        if key not in self:
            return
        vals = dict.pop(self, key)
        if newkey in self:
            dest_set = dict.__getitem__(self, newkey)
        else:
            dest_set = set()
            dict.__setitem__(self, newkey, dest_set)

        for val in vals:
            if self.listeners:
                self._notify_remove(key, val)
            revset = dict.__getitem__(self.inv, val)
            revset.remove(key)
            revset.add(newkey)
            if val not in dest_set:
                dest_set.add(val)
                if self.listeners:
                    self._notify_add(newkey, val)

    def iteritems(self) -> Iterable[Tuple[K, V]]:
        for key in self:
            for val in dict.__getitem__(self, key):
                yield key, val

    # Python mapping API -------------------------------------------------
    def items(self) -> Iterable[Tuple[K, FrozenSet[V]]]:
        return ((k, frozenset(v)) for k, v in dict.items(self))

    def clear(self) -> None:
        for key in list(self.keys()):
            del self[key]

    def popitem(self) -> Tuple[K, FrozenSet[V]]:
        key, vals = dict.popitem(self)
        for val in list(vals):
            rev = dict.__getitem__(self.inv, val)
            rev.remove(key)
            if not rev:
                del self.inv[val]
            if self.listeners:
                self._notify_remove(key, val)
        return key, frozenset(vals)

    def setdefault(self, key: K, default: Iterable[V] | None = None) -> FrozenSet[V]:
        if key not in self:
            if default is None:
                default = []
            self[key] = default
        return self[key]

    @classmethod
    def fromkeys(cls, keys: Iterable[K], value: Iterable[V] | None = None) -> "M2M[K, V]":
        m2m = cls()
        for k in keys:
            if value is not None:
                m2m[k] = value
            else:
                m2m[k] = []
        return m2m

    # dict.keys() already has the correct behavior
    def values(self) -> Iterable[V]:
        return self.inv.keys()

    def copy(self) -> "M2M[K, V]":
        """
        a full copy can be done a lot faster since items don't
        need to be added one-by-one to sets
        """
        return self.__class__(self)

    def __copy__(self) -> "M2M[K, V]":
        return self.copy()

    def __deepcopy__(self, memo: dict) -> "M2M[K, V]":
        return self.copy()
    # NOTE: __copy__ by default will be pretty useless so
    # it is overridden here; __deepcopy__ is correct by default
    # because it copies the underlying dict of sets as well as self.inv
    # so we don't bother to override the behavior

    def __contains__(self, key: K) -> bool:
        return dict.__contains__(self, key)

    def __iter__(self) -> Iterator[K]:
        return dict.__iter__(self)

    def __len__(self) -> int:
        return dict.__len__(self)

    def __eq__(self, other):
        return type(self) == type(other) and dict.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self) -> str:
        cn = self.__class__.__name__
        return '%s(%r)' % (cn, list(self.iteritems()))


import itertools


def chain(*rels):
    """
    Chain M2Ms or M2MChains together into an M2MChain
    """
    m2ms = []
    for obj in rels:
        if type(obj) is M2M:
            m2ms.append(obj)
        elif type(obj) is M2MChain:
            m2ms.extend(obj.m2ms)
    return M2MChain(m2ms, copy=False)


class M2MChain(object):
    """
    Represents a sequence of ManyToMany relationships

    Basically, an M2MChain is a compressed representation of a
    sequence of values across all of it's columns.

    The Chain can be iterated over, yielding all of the unique
    combinations of values that span each of its relationships.

    The relationships in the Chain can be updated, and the Chain
    will immediately reflect those updates.

    Chains may share their internal state with M2MGraph, M2Ms, and
    other M2MChains; in this case updates to objects sharing the
    same underlying data will immediately be reflected in each
    other.
    """
    def __init__(self, m2ms, copy=True):
        if m2ms.__class__ is self.__class__:
            m2ms = m2ms.m2ms
        for m2m in m2ms:
            if type(m2m) is not M2M:
                raise TypeError('can only chain M2Ms, not {}'.format(type(m2m)))
        if copy:
            self.m2ms = [M2M(d) for d in m2ms]
        else:
            self.m2ms = m2ms

    def only(self, keyset):
        """
        returns a chain that is filtered so that only keys in ``keyset`` are
        kept. ``keyset`` may be a single iterable of keys for the first column
        (existing behaviour) or an iterable of keysets matching the width of the
        chain (one keyset per column).
        """

        # detect ``keyset`` as a sequence of keysets.  A multi-keyset must have
        # exactly one entry for each column of data (``len(self.m2ms) + 1``) and
        # the entries themselves should be iterable containers (strings are
        # treated as single keysets for backwards compatibility).
        multi = False
        if isinstance(keyset, (list, tuple)) and len(keyset) == len(self.m2ms) + 1:
            if all(not isinstance(ks, (str, bytes)) for ks in keyset):
                multi = True

        if not multi:
            keysets = [keyset] + [None] * len(self.m2ms)
        else:
            keysets = list(keyset)

        m2ms = []

        # initial set of allowed keys for the first column
        cur_keys = keysets[0]
        if cur_keys is None:
            cur_keys = self.m2ms[0].keys()
        m2m = self.m2ms[0].only(cur_keys)

        # optionally restrict values of the first relationship
        if keysets[1] is not None:
            m2m = m2m.inv.only(keysets[1]).inv
            cur_keys = keysets[1]
        else:
            cur_keys = m2m.values()
        m2ms.append(m2m)

        for idx, rel in enumerate(self.m2ms[1:], start=1):
            lhs_keys = cur_keys
            if lhs_keys is None:
                lhs_keys = rel.keys()
            m2m = rel.only(lhs_keys)

            next_keys = keysets[idx + 1] if idx + 1 < len(keysets) else None
            if next_keys is not None:
                m2m = m2m.inv.only(next_keys).inv
                cur_keys = next_keys
            else:
                cur_keys = m2m.values()
            m2ms.append(m2m)

        return M2MChain(m2ms, copy=False)

    def _roll_lhs(self, key):
        # fold up keys left-to-right
        if key[0] == slice(None, None, None):
            lhs = self.m2ms[0]
        else:
            lhs = [key[0]]
        lhs = set(lhs)
        rkey_data = zip(key[1:], self.m2ms)
        for rkey, m2m in rkey_data:
            new_lhs = set()
            for lkey in lhs:
                new_lhs |= m2m[lkey]
            if rkey != slice(None, None, None):
                if rkey in new_lhs:
                    new_lhs = set([rkey])
            lhs = new_lhs
        return lhs

    def __getitem__(self, key):
        if type(key) is slice:
            data = self.m2ms[key]
            return M2MChain(data, copy=False)
        if type(key) is not tuple:
            raise TypeError("expected tuple, not {!r}".format(type(key)))
        assert len(key) <= len(self.m2ms)
        lhs = self._roll_lhs(key)
        if len(key) == len(self.m2ms) + 1:
            return lhs
        # build a chain of the remaining columns
        m2ms = []
        for cur in self.m2ms[len(key) - 1:]:
            new = M2M()
            for val in lhs:
                if val in cur:
                    new[val] = cur[val]
            m2ms.append(new)
            lhs = new.inv
        return M2MChain(m2ms, copy=False)

    def __contains__(self, vals: Tuple[Any, ...]) -> bool:
        if type(vals) is not tuple:
            raise TypeError("expected tuple, not {!r}".format(type(vals)))
        return bool(self._roll_lhs(vals))

    def add(self, *vals: Any) -> None:
        assert len(self.m2ms) + 1 == len(vals)
        val_pairs = zip(vals[:-1], vals[1:])
        for m2m, val_pair in zip(self.m2ms, val_pairs):
            m2m.add(*val_pair)

    def update(self, vals_seq: Iterable[Tuple[Any, ...]]) -> None:
        if len(self.m2ms) == 1 and type(vals_seq) is M2M:
            self.m2ms[0].update(vals_seq)
        else:
            for vals in vals_seq:
                self.add(*vals)

    def pairs(self, start: int = 0, end: int | None = None) -> "M2M":
        """
        return pairs between the given indices of data
        """
        pairing = M2MChain(self.m2ms[start:end], copy=False)
        return M2M([(row[0], row[-1]) for row in pairing])

    def copy(self):
        return M2MChain(self)

    def __copy__(self):
        return self.copy()

    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and self.m2ms == other.m2ms

    def __repr__(self):
        return "M2MChain({})".format(self.m2ms)

    def __nonzero__(self) -> bool:
        try:
            next(iter(self))
            return True
        except StopIteration:
            return False

    __bool__ = __nonzero__

    def __iter__(self) -> Iterable[Tuple[Any, ...]]:
        """
        iterate over all of the possible paths through the
        chain of many to many dicts

        these are sequences of values, such that a value
        from M2M N is the key in M2M N+1 across the whole
        set of M2Ms
        """
        m2ms = self.m2ms
        rows = itertools.chain.from_iterable(
            [_join_all(key, m2ms[0], m2ms[1:]) for key in m2ms[0]])
        for row in rows:
            yield tuple(row)


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
        m2ms = {}
        cols = M2M()
        rels = []
        for lhs, rhs in relationships.iteritems():
            # check that only one direction is present
            assert lhs not in relationships.get(rhs)
            if data:
                if (lhs, rhs) in data:
                    m2ms[lhs, rhs] = data[lhs, rhs]
                    m2ms[rhs, lhs] = data[lhs, rhs].inv
                    rels.append((lhs, rhs))
                elif (rhs, lhs) in data:
                    m2ms[lhs, rhs] = data[rhs, lhs].inv
                    m2ms[rhs, lhs] = data[lhs, rhs]
                    rels.append((rhs, lhs))
            else:
                rels.append((lhs, rhs))
                m2ms[lhs, rhs] = M2M()
                m2ms[rhs, lhs] = m2ms[lhs, rhs].inv
            cols.add(lhs, (lhs, rhs))
            cols.add(rhs, (rhs, lhs))
        self.m2ms = m2ms
        self.cols = cols
        self.rels = rels

    @classmethod
    def from_rel_data_map(cls, rel_data_map):
        """
        convert a map of column label relationships to M2Ms
        into a M2MGraph

        rel_data_map -- { (lhs_col, rhs_col): {lhs_val: rhs_val} }
        """
        # TODO: better checking
        return cls(rel_data_map.keys(), rel_data_map)

    def __getitem__(self, key):
        """
        return a M2M, M2MChain, or M2MGraph
        over the same underlying data structure for easy
        mutation
        """
        if type(key) is dict or type(key) is M2M:
            return M2MGraph(
                key,
                dict([((lhs, rhs), self.m2ms[lhs, rhs]) for lhs, rhs in key.items()]))
        if key in self.cols:
            return self._all_col(key)
        if type(key) is tuple:
            return self.chain(*key)
        raise KeyError(key)

    def chain(self, *cols):
        """
        return an M2MChain along the given columns
        """
        assert cols[0] is not Ellipsis  # ... at the beginning is invalid
        col_pairs = tuple(zip(cols[:-1], cols[1:]))
        m2ms = []
        for lhs_col_pair, rhs_col_pair in zip(col_pairs[:-1], col_pairs[1:]):
            if lhs_col_pair[0] is Ellipsis:
                continue  # skip, was handled by lhs
            if lhs_col_pair[1] is Ellipsis:
                assert rhs_col_pair[0] is Ellipsis
                # join ... in the middle via pairs
                lhslhs, rhsrhs = lhs_col_pair[0], rhs_col_pair[1]
                m2ms.append(self.pairs(lhslhs, rhsrhs))
                continue
            m2ms.append(self.m2ms[lhs_col_pair])
        assert col_pairs[-1][1] is not Ellipsis  # ... on the end is invalid
        if col_pairs[-1][0] is not Ellipsis:
            m2ms.append(self.m2ms[col_pairs[-1]])
        return M2MChain(m2ms, False)

    def __setitem__(self, key, val):
        if type(key) is not tuple:
            raise TypeError("expected tuple, not {!r}".format(type(key)))
        if type(val) is M2M:
            data = [val]
        elif type(val) is M2MChain:
            data = val.m2ms
        else:
            raise TypeError("expected M2MChain or M2M for val, not {!r}".format(type(val)))
        if len(data) != len(key) - 1:
            raise ValueError("value wrong width ({}) for key {}".format(len(data), key))
        for colpair, m2m in zip(zip(key[:-1], key[1:]), data):
            lhs, rhs = colpair
            self.cols.add(lhs, (lhs, rhs))
            self.cols.add(rhs, (rhs, lhs))
            self.m2ms[lhs, rhs] = m2m
            self.m2ms[rhs, lhs] = m2m.inv

    def _all_col(self, col):
        """get all the values for a given column"""
        sofar = set()
        for edge in self.cols[col]:
            sofar.update(self.m2ms[edge].keys())
        return frozenset(sofar)

    def pairs(self, lhs: Any, rhs: Any, paths: Iterable[Tuple[Any, ...]] | None = None, ignore: Iterable[Any] | None = None) -> "M2M":
        """
        get all the unique pairs of values from lhs col and rhs col

        ignore is a set of column names to exclude from building paths

        paths is a list-of-lists of column names; if specified, will
        follow exactly the chain of relationships specified by
        each list of column names in paths rather than searching
        for paths between lhs and rhs columns
        """
        missing = lhs if lhs not in self.cols else rhs if rhs not in self.cols else None
        if missing:
            raise KeyError('no col named {}; valid cols are {}'.format(missing, ", ".join(self.cols)))
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
        return [tuple(path) for path in self._all_paths2(lhs, rhs, already_visited)]

    def _all_paths2(self, lhs, rhs, already_visited):
        if lhs == rhs:
            return [[lhs]]
        paths = []
        for col_pair in self.cols[lhs]:
            assert lhs in col_pair
            nxt = col_pair[1] if lhs == col_pair[0] else col_pair[0]
            if nxt in already_visited:
                continue
            paths.extend(
                [[lhs] + sub_path for sub_path in self._all_paths2(
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
                    if key in self.m2ms:
                        to_add.append((key, row[key[0]], row[key[1]]))
                        exists = True
            if not exists:
                raise ValueError('could not find any relationships for col {}'.format(lhs))
        for key, lval, rval in to_add:
            self[key].add(lval, rval)

    def remove(self, col, val):
        """
        given a column label and value, remove that value from
        all relationships involving that column label
        """
        for key in self.cols[col]:
            del self.m2ms[key][val]

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
        if type(other) is dict:
            relationships = other.keys()
            for r in relationships:
                assert type(r) is tuple and len(r) == 2
            data = {k: M2M(v) for k, v in other.items()}
            other = M2MGraph(relationships, data)
        assert type(other) is type(self)
        # TODO: allow attaching of sequences?
        # check that relationships do not overlap
        overlaps = set([frozenset(e) for e in self.m2ms]) & (
            set([frozenset(e) for e in other.m2ms]))
        if overlaps:
            raise ValueError('relationships are specified by both graphs: {}'.format(
                ", ".join([tuple(e) for e in overlaps])))
        self.m2ms.update(other.m2ms)
        self.cols.update(other.cols)

    def replace_col(self, col: Any, valmap: dict) -> None:
        """
        replace every value in col by the value in valmap
        raises KeyError if there is a value not in valmap
        """
        current_vals = set()
        for key in self.cols[col]:
            if col == key[0]:
                m2m = self.m2ms[key]
            else:
                m2m = self.m2ms[key].inv
            current_vals.update(m2m.keys())

        missing = current_vals - set(valmap)
        if missing:
            raise KeyError("missing mappings for values: {}".format(sorted(missing)))

        for key in self.cols[col]:
            if col == key[0]:
                m2m = self.m2ms[key]
            else:
                m2m = self.m2ms[key].inv
            for oldval, newval in valmap.items():
                m2m.replace(oldval, newval)

    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and self.m2ms == other.m2ms

    def __contains__(self, rel):
        return rel in self.m2ms

    def __repr__(self):
        return "M2MGraph({}, ...)".format(self.rels)
