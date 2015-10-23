from operator import add
from utils import replicate
from utils import concatMap

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
	return ["{"] + nest(4, newline() + doc) + newline() + ["}"]

# indents a document by inserting i spaces after every newline.
def nest(i, doc):
	return map(lambda elm: nestl(i, elm), doc)

def nestl(i, doc):
	return concatMap(lambda x: indent(i, x), doc)

def indent(i, c):
	if c == '\n':
		return [c] + replicate(i, ' ')
	else:
		return [c]

# FIXME
# int -> Doc -> Layout
def pretty(width, doc):
	return reduce(add, doc, "")

