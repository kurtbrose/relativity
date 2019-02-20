from relativity import M2M


class Table(object):
    def __init__(self, cols, key_cols):
        # TODO: key_cols None means counter / integer rowid
        self.key_cols, self.cols = tuple(key_cols), tuple(cols)
        self.rows = {}  # should this be dict-of-tuples or tuple-of-dicts?
        self.indices = {}  # {(cols): M2M({col-vals: keys})
        self.fk_in = []
        self.fk_out = []

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

    def __contains__(self, key):
        return key in self.rows

    def add_index(self, cols):
        assert set(cols) not in [set(icols) for icols in self.indices]
        assert set(cols) != set(self.key_cols)
        self.indices[tuple(cols)] = _Index(self, cols)

    def col_index(self, col):
        all_col_idx = dict([
            (c, i) for i, c in
            enumerate(self.key_cols + self.cols)])
        return all_col_idx[col]


class _Index(object):
    """
    index usable by Table
    """
    def __init__(self, table, cols):
        self.col_idxs = [table.col_index(col) for col in cols]
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


CASCADE, PROTECT, NULL = object(), object(), object()


class _ForeignKeyConstraint(object):
    def __init__(self, table, col, target, on_delete=CASCADE):
        assert on_delete in (CASCADE, PROTECT, NULL)
        self.col_idx = table.col_index(col)
        self.table, self.col, self.target = table, col, target
        self.on_delete = on_delete
        self.data = M2M()
        for key in table.rows:
            self.add_row(key, table.rows[key])

    def add_row(self, key, val):
        row = key + val
        fk = row[self.col_idx]
        self.data.add(fk, key)

    def check_add_row(self, key, val):
        # should be called before add_row to check
        # no constraints violated
        row = key + val
        fk = row[self.col_idx]
        assert fk in self.target

    def remove_row(self, key):
        del self.data.inv[key]

    def check_remove_target_row(self, target_key):
        if target_key not in self.data:
            return
        if self.on_delete is PROTECT:
            raise ValueError('deleting {} would cause constraint violation')
        elif self.on_delete is CASCADE:
            self.table.check_remove_rows(self.data[target_key])

    def remove_target_row(self, target_key):
        if target_key not in self.data:
            return
        if self.on_delete is CASCADE:
            self.table.remove_rows(self.data[target_key])
        if self.on_delete is NULL:
            pass  # reach out to null out cols on table
    