"""
A Schema is a more general container for Python objects.
In addition to tracking relationships between objects,
it can also keep other kind of indexing structures.
Will need a more flexible query object that can represent
comparisons.
NOTE -- not sure if this is really worth it since it only
kicks in with relatively large amounts of data.
At that point is it better off to use a SQLite anyway?
A M2M can be used to store a reverse mapping of
attribute : column values.
For something like "index foo.bar" followed by
"select foo where bar = 1" this is sufficient.
Range queries require an additional structure --
maybe ManyToMany that uses a SortedDict for one of its directions?
(SortedDict alone wouldn't be able to support fast deletes.)
What about indices over many or combinations?
This would basically be the same thing, with multiple values.
E.g. index of (a.b, a.c) is... just an M2M or M2MS of
{a: (a.b, a.c)}
"""
from . import relativity


class Schema(object):
    def __init__(self, cols):
        self.col_set = {col: set() for col in cols}
        # column label to set-of-values
        self.rel_set = set()
        # relationships among columns
        self.col_users = {col: set() for col in cols}
        # relationships / indices / etc that make use of cols

        self.version = 0  # increment this when schema changes are made

    def add_col(self, col):
        """
        column labels aren't limited to strings -- any
        hashable python object will do;
        just keep in mind that if one column label is a tuple
        of other column labels it will lead to ambiguous queries
        """
        assert col not in self.col_set
        self.col_set.add(col)

    def remove_col(self, col):
        self.col_set.pop(col)


class RelDB(object):
    """
    RelDB = Schema + data
    """
    def __init__(self, cols):
        self.schema = Schema(cols)
        self.col_vals = {col: set() for col in cols}
        # column label to set-of-values
        self.rels = {}
        # relationships among columns

    def add(self, col, val):
        self.col_vals[col].add(val)

    def remove(self, col, val):
        self.col_vals[col].remove(val)

    # TODO: pub-sub linking schema mutations to RelDB
    def add_col(self, col):
        """
        column labels aren't limited to strings -- any
        hashable python object will do;
        just keep in mind that if one column label is a tuple
        of other column labels it will lead to ambiguous queries
        """
        assert col not in self.col_vals
        self.col_vals[col] = set()
        self.col_users[col] = []

    def remove_col(self, col):
        assert col in self.col_vals
        if self.col_users[col]:
            raise ValueError('cannot remove {}, still in use by {}'.format(
                col, self.col_users[col]))

    def add_relationship(self, col_a, col_b):
        """
        create an (initially empty) relationship between two columns
        """
        assert col_a in self.col_vals
        assert col_b in self.col_vals
        self.rels[col_a, col_b] = fwd = M2M()
        self.rels[col_b, col_a] = fwd.inv

    def __getitem__(self, key):
        if key in self.cols:
            return self.col_vals[col]
        if type(key) is tuple:
            pass
        if key is Ellipsis:
            # iterate over all unique tuples in some order?
            raise KeyError()


# what is the structure of a ResultSet?
# (M2M, ((M2M, M2M), (M2M,)),  )
# tuple of M2Ms -- anything inside a sub tuple = not part of output
# multi layer sub-tuple = multiple paths
# BUT, what if tuples are being used as keys?

class ResultSet(object):
    __slots__ = ('rels', 'schema')

    def __init__(self, rels, schema):
        self.rels = rels



