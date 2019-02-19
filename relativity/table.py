from relativity import M2M


class Table(object):
    def __init__(self, cols, key_cols):
        # TODO: key_cols None means counter / integer rowid
        self.key_cols, self.cols = key_cols, cols
        self.rows = {}
        self.indices = {}  # {(cols): M2M({col-vals: keys})

    def __getitem__(self, key):
        return key + self.rows[key]

    def __setitem__(self, key, val):
        assert len(val) == len(self.cols)
        if len(self.key_cols) != 1:
            assert len(key) == len(self.key_cols)
        if key in self.rows:
            for idx in self.indices.values():
                idx.remove_row(key)
        self.rows[key] = val
        for idx in self.indices.values():
            idx.add_row(key, val)

    def __delitem__(self, key):
        del self.rows[key]
        for idx in self.indices.values():
            idx.remove_row(key)

    def __iter__(self):
        if len(self.key_cols) == 1:
            for key, vals in self.rows.iteritems():
                yield (key,) + vals
        else:
            for key, vals in self.rows.iteritems():
                yield key + vals

    def add_index(self, cols):
        for col in cols:
            assert col in self.cols or col in self.key_cols
        assert set(cols) not in [set(icols) for icols in self.indices]
        assert set(cols) != set(self.key_cols)
        self.indices[tuple(cols)] = _Index(self, cols)


class _Index(object):
    """
    index usable by Table
    """
    def __init__(self, table, cols):
        all_col_idx = dict([(col, i) for i, col in enumerate(table.key_cols + table.cols)])
        self.col_idxs = [all_col_idx[col] for col in cols]
        self.table, self.cols = table, cols
        self.data = M2M()
        for key in table.rows:
            self.add_row(key, table.rows[key])

    def add_row(self, key, val):
        if len(self.table.key_cols) == 1:
            row = (key,) + val
        else:
            row = key + val
        if len(self.col_idxs) == 1:
            self.data.add(row[self.col_idxs[0]], key)
        else:
            self.data.add(tuple([row[idx] for idx in self.col_idxs]), key)

    def remove_row(self, key):
        del self.data.inv[key]

    def __getitem__(self, key):
        return self.data[key]
