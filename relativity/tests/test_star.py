from relativity.star import star, Star


def test():
	data = [['ab', 'cd'], ['a1', 'c2']]
	assert set(Star(data)) == set([('a', 'b', '1'), ('c', 'd', '2')])
