from itertools import count

from relativity import M2M


class Table(object):
    """
    column-oriented table
    """
    def __init__(self, colnames):
        self.colnames = tuple(colnames)
        self.colvals = tuple([{} for name in colnames])
        self.rowids = set()  # sorted list?
        self.rowid_seq = count()

    def insert(self, *vals):
        # TODO: simulate args/kwargs of table columns
        assert len(vals) == len(self.colnames)
        rowid = self.rowid_seq.next()
        for col, val in zip(self.colvals, vals):
            col[rowid] = val
        self.rowids.add(rowid)

    def __getitem__(self, rowid):
        return tuple([col.get(rowid) for col in self.colvals])

    def __delitem__(self, rowid):
        if rowid not in self.rowids:
            raise KeyError()
        for col in self.colvals:
            del col[rowid]
        self.rowids.remove(rowid)

    def __iter__(self):
        for rowid in sorted(self.rowids):
            yield (rowid,) + self[rowid]
