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
		self.col_vals = {col: set() for col in cols}
		# column label to set-of-values
		self.rels = {}
		# relationships among columns
		self.col_users = {col: set() for col in cols}
		# relationships / indices / etc that make use of cols

	def add_col(self, col):
		assert col not in self.col_vals
		self.col_vals[col] = set()
		self.col_users[col] = []

	def remove_col(self, col):
		assert col in self.col_vals
		if self.col_users[col]:
			raise ValueError('cannot remove {}, still in use by {}'.format(
				col, self.col_users[col]))

	def add(self, col, val):
		self.col_vals[col].add(val)

	def remove(self, col, val):
		self.col_vals[col].remove(val)
