from operator import add

def empty():
	return []

def space():
	return [" "]

def text(str):
	return [str]

def newline():
	return ["\n"]

def comma():
	return [","]

def block(doc):
	return ["{"] + newline() + nest(4, doc) + newline() + ["}"]

def nest(width, doc):
	return [' ' for x in range(0, width)] + doc

def group(doc):
	return [doc]

# FIXME
# int -> Doc -> Layout
def pretty(width, doc):
	return reduce(add, doc, "")

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

