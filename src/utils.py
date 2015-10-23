def replicate(count, ch):
	return [ch for x in range(0, count)]

# (a -> [b]) -> [a] -> [b]
def concatMap(f, lst):
	return concat(map(f, lst))

def concat(lst):
	return reduce (lambda x,y: x+y, lst, [])

# intersperse(["a","b","c"], "_") == ["a","_","b","_","c"]
# intersperse(['struct', 'field'], [" "]) == ['struct', [' '], 'field']]
def intersperse(xs, delimiter):
	if len(xs) == 0:
		return []

	iter_xs = iter(xs)
	first = next(iter_xs) 
	r = [first]

	for x in iter_xs:
		r += [delimiter]
		r += [x]
	return r

# return [list-satisfying-f, list-not-satisfying-f]
# e.g) splitBy(odd, [1,2,3,4]) => [[1,3], [2,4]]
def splitBy(f, xs):
	trues = []
	falses = []
	for x in xs:
		if f(x):
			trues += [x]
		else:
			falses += [x]

	return [trues, falses]

