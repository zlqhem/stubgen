from compiler.ast import flatten
from elftools.elf.elffile import ELFFile
from operator import add
import pretty as P

def generate_doc(filename):
	with open(filename, 'rb') as f:
		elffile = ELFFile(f)

		if not elffile.has_dwarf_info():
			print('    ' + filename + ' has no DWARF info')
			return None

		dwarfinfo = elffile.get_dwarf_info()

		# cu: compilation unit
		# DIE: debug information entry
		docs = [mkDoc(cu, cu.get_top_DIE()) for cu in dwarfinfo.iter_CUs()]
		result = flatten(P.intersperse(filter(None, flatten(docs)), P.space()))
		return reduce(add, result, "")

def mkDoc(cu, die):
	dispatch = {
		'DW_TAG_compile_unit': mkDoc_compile_unit,
		'DW_TAG_structure_type': mkDoc_structure_type,
		'DW_TAG_typedef': mkDoc_typedef,
		# skip if DW_AT_declaration  == 1
		'DW_TAG_subprogram': mkDoc_subprogram,
		'DW_TAG_pointer_type': mkDoc_empty,
		'DW_TAG_base_type': mkDoc_empty,

		'DW_TAG_union_type': mkDoc_empty,
		'DW_TAG_base_type': mkDoc_empty,
		'DW_TAG_variable': mkDoc_empty,
		'DW_TAG_volatile_type': mkDoc_empty,
		'DW_TAG_array_type': mkDoc_empty,
		'DW_TAG_constant': mkDoc_empty,
		'DW_TAG_packed_type': mkDoc_empty
	}

	if die.tag in dispatch:
		return dispatch[die.tag](cu, die)
	else:
		print(die.tag + " not supported")
		return P.empty()

def mkDoc_compile_unit(cu, die):
	docs = [mkDoc(cu, child) for child in die.iter_children()]
	return flatten(P.intersperse(docs, P.newline()))

def mkDoc_structure_type(cu, die):
	# struct <name> " {" [<member>] " };"
	name = mkDoc_diename(cu, die)
	members = [mkDoc_member(cu, member) for member in die.iter_children()]
#	return P.text("struct") + name + P.newline() + P.block(flatten(members)) + P.text(";")
	return P.text("struct") + name + P.newline() + P.block(P.intersperse(members, P.newline())) + P.text(";")

def mkDoc_member(cu, die):
	name = mkDoc_diename(cu, die)
	print "member " + P.pretty(80, name)
	dieType = get_die_type(cu, die)
	if dieType == None:
		print dieType
	return mkDoc_typeref(cu, dieType) + P.space() + name + P.text(";")

def mkDoc_typedef(cu, die):
	name = 	mkDoc_diename(cu, die)
	return P.text("typedef") + mkDoc_typeref(cu, get_die_type(cu, die)) + name + P.text(";")

def mkDoc_subprogram(cu, die):
	# <return-type> <function-name> <params>	
	returnType = get_die_type(cu, die)
	name = mkDoc_diename(cu, die)
	params = [mkDoc_formalparameter(cu, child) for child in die.iter_children()
									   if child.tag == 'DW_TAG_formal_parameter']
	docParams = P.intersperse(params, P.comma())
	
	if returnType == None:
		docReturnType = P.text("void")
	else:
		docReturnType = mkDoc_typeref(cu, returnType)
	
	return docReturnType + name + P.text("(") + docParams + P.text(")") + mkDoc_body(cu, returnType)

def mkDoc_formalparameter(cu, die):
	return mkDoc_typeref(cu, get_die_type(cu, die)) + mkDoc_diename(cu, die)

def mkDoc_body(cu, dieType):
	# FIXME
	# case pointer_type => return (void*)0;
	# case void => P.empty
	# case base_type => return base_type
	if dieType == None:
		return P.block(P.empty())
	else:
		return P.block(P.text("return 0;"))

def mkDoc_typeref(cu, die):
	genDoc = {
		'DW_TAG_structure_type': lambda cu, die: P.text("struct") + mkDoc_diename(cu, die),
		'DW_TAG_typedef': mkDoc_diename,
		'DW_TAG_union_type': mkDoc_diename,
		'DW_TAG_base_type': mkDoc_diename,
		'DW_TAG_pointer_type': 
				lambda cu, die: mkDoc_typeref(cu, get_die_type(cu, die)) + P.text("*"),
	}

	if die.tag in genDoc:
		return genDoc[die.tag](cu, die)
	else:
		print("typeref of " + die.tag + " is not supported")
		return P.empty()

def mkDoc_empty(cu, die):
	return P.empty()

def mkDoc_diename(cu, die):
	if 'DW_AT_name' not in die.attributes:
		return P.empty()

	return P.text(die.attributes['DW_AT_name'].value)

# -> DIE | None
def get_die_type(cu, die):
	if 'DW_AT_type' not in die.attributes:
		return None

	offset = die.attributes['DW_AT_type'].value
	return get_die_by_offset(cu, offset)

def get_die_by_offset(cu, offset):
	print "    offset:", offset
	for die in cu.iter_DIEs():
		if die.offset == offset:
			return die
	print "    fail to get die for ", offset
	return None



