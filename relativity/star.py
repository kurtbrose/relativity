"""
A star is similar to a table -- one "primary" key
is used to select a bunch of "secondary" values

The underlying data structure is a list of M2Ms
"""
import itertools

from relativity import M2M


def star(*m2ms):
    return Star(m2ms, copy=False)

class Star(object):
    def __init__(self, m2ms, copy=True):
        # TODO: typecheck
        if m2ms.__class__ is self.__class__:
            m2ms = m2ms.m2ms
        if copy:
            self.m2ms = [M2M(m2m) for m2m in m2ms]
        else:
            self.m2ms = m2ms

    def __getitem__(self, key):
        return frozenset(itertools.product(*[
            m2m.get(key) for m2m in self.m2ms]))

    def __iter__(self):
        keys = set()
        for m2m in self.m2ms:
            keys.update(m2m)
        for key in keys:
            rows = itertools.product(*[
                m2m.get(key) for m2m in self.m2ms])
            for row in rows:
                yield (key,) + row


