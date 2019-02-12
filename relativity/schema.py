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

        self.ver = 0  # increment this when schema changes are made

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



class View(object):
    __slots__ = ('reldb', 'schema_ver')
    """
    A View is a live attachement to some subset of the data
    inside a RelDB; Views allow for more focused read/write APIs
    """
# this is only to provide isinstance() checks for users


class _RelView(View):
    """
    View of a single relationship

    This is basically an M2M.
    """
    __slots__ = ('lhs_col', 'rhs_col')

    def __init__(self, reldb, lhs_col, rhs_col):
        assert lhs_col in reldb.cols
        assert rhs_col in reldb.cols
        self.lhs_col, self.rhs_col, self.reldb = lhs_col, rhs_col, reldb
        self.schema_version = self.reldb.schema.ver

    def add(self, key, val):
        if key not in self.reldb.



# what is the structure of a Query?
# (M2M, [M2M, M2M],  ..., M2M)
# tuple of M2Ms -- anything inside a list = not part of output
# multi layer sub-list = multiple paths

# a paths is something like (col, [col, col], ..., col)

class _Query(object):
    """
    represents an abstract query; not intended to be instantied directly,
    should be created by methods / getitem of DB
    """
    __slots__ = ('cols', 'path', 'database', 'schema_version', 'grouped_by', 'sorted_on')
    # cols - the columns that will be output (must be part of path)
    # path - the join path through the DB that will be walked
    # database - the RelDB over which the query will be evaluated
    # schema_version - integer schema version
    # grouped_by - subset of cols which will be combined into tuples as keys (?)
    #       -- an alternative interpretation of grouped_by is anything NOT grouped by must be aggregated,
    #           perhaps with an implicit / default aggregation being "build a list of"
    # sorted_on - subset of cols that will be used to sort

    def __init__(self, cols, path, database):
        self.cols, self.path, self.database = cols, path, database
        self.schema_version = database.schema.version
        self.grouped_by = self.sorted_on = ()

    def groupby(self, cols):
        assert set(cols) < set(self.cols)
        assert not set(cols) & set(self.grouped_by)
        ret = _Query(self.cols, self.path, self.database)
        ret.grouped_by += cols
        return ret

    def sort(self, cols):
        assert set(cols) < set(self.cols)
        assert not set(cols) & set(self.sorted_on)
        ret = _Query(self.cols, self.path, self.database)
        ret.sorted_on += cols
        return ret

    def validate(self, database):
        assert set(self.cols) <= set(self.path)


class _ResultSet(object):
    """
    a resultset obtained by executing a query; not intended to be constructed
    directly should be built by a _Query
    """
    __slots__ = ('query', 'results')

    def __init__(self, query):
        if query.database.schema.version != query.schema_version:
            pass  # re-validate that query is still valid
        # evaluate the query against it's database
        self.results = fetch()  # ...

    def __iter__(self):
        return iter(self.results)
