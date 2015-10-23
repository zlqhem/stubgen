import os
import argparse
import sys
import arpy
from itertools import count
from itertools import izip
from compiler.ast import flatten
from elftools.elf.elffile import ELFFile
from operator import add
from utils import intersperse
#from src.utils import intersperse
from utils import splitBy
#from src.utils import splitBy
import pretty as P

'''
 WIP:
 * use Monad to lower complexity
 * void XXX_StubReturns (<Type of XXX function> value)

 TODO: 
 * distinguish naming of mkDoc from DIE and from Doc
 * handle union type
 * DW_TAG_unspecified_parameters
 * stub initialization for each test case run
 * adjust level of abstraction 

 DONE:
 * typedef <type> (*STUB_XXX_CALLBACK) (param-list, int stubCallCount)
 * static STUBGEN_XXX_CALLBACK s_callback_XXX = 0;
 * void XXX_StubWithCallback (STUBGEN_XXX_CALLBACK cb)
 * CLI support 
 * handle DW_TAG_subroutine_type has no DW_AT_type attr for function pointer

'''

# =------------------------------------------------
# monad
# =------------------------------------------------
# bind(mv, mf) -> mv
#'''
# (a -> b) -> F  a -> F b
def fmap(f, mval):
	return bind(mval, lambda a: unit(f(a)))
	
def unit(a):
	return (a, None)

# M a -> (a -> M b) -> M b
def bind(mval, mf):
	(cv, err_msg) = mval
	if (cv == None):
		return error(err_msg)
	return mf(cv)

def nothing():
	return (None, '')

def error(message):
	return (None, message)

def value(mval):
	(_, val) = mval
	return val

def context(mval):
	(cu, _) = mval
	return cu

def orElse(mval, elseVal):
	(val) = mval
	if val:
		mval
	else:
		elseVal

# [M a] -> M [a]
def sequence(xs):
	m_r = unit([])
	for m_x in xs:
		m_r = bind(m_x, lambda x: 
			  bind(m_r, lambda r: r + [x]))
	return m_r

# a -> [(a -> M a)] -> M a
def chain(v, fs):
	m_ret = unit(v)
	for f in fs:
		m_ret = bind(m_ret, f)
	return m_ret

# start 
# .a
# string -> string -> [string]
def generate_stubs_from_staticlib(libpath, outdir='./'):
	ar = arpy.Archive(libpath)
	return [doc2file(doc, get_stub_path(libpath + '-' + f.header.name, outdir))
			for f in ar
				for doc in generate_docs_from_stream(f.header.name, f)]

# .o | .so
# string -> string -> [string]
def generate_stubs_from_bin(binpath, outdir='./'):
	return [doc2file(doc, get_stub_path(binpath + '-' + str(idx), outdir))
			for doc,idx in izip(generate_docs(binpath),count(0))]

def get_stub_path(orgPath, outdir='./'):
	return os.path.join(outdir, os.path.basename(orgPath) + '-stub.c')

def pretty(doc, outstream=sys.stdout):
	contents = P.pretty(80, doc)
	outstream.write(contents)

# returns filename if success, otherwise None
def doc2file(doc, filename):
	with open(filename, 'w+') as outstream:
		pretty(doc, outstream)
	return filename

def generate_docs(filename):
	with open(filename, 'rb') as fd:
		return generate_docs_from_stream(filename, fd)

def generate_docs_from_stream(filename, fd):
	elffile = ELFFile(fd)

	if not elffile.has_dwarf_info():
		print('    ' + filename + ' has no DWARF info')
		return []

	dwarfinfo = elffile.get_dwarf_info()

	# cu: compilation unit
	# DIE: debug information entry
	
	docs = [mkDoc((cu, cu.get_top_DIE())) for cu in dwarfinfo.iter_CUs()]
	return docs

# cv -> M doc
def mkDoc(cv):
	dispatch = {
		'DW_TAG_compile_unit': mkDoc_compile_unit,
		'DW_TAG_structure_type': mdoc_structure_type,
		'DW_TAG_typedef': mdoc_typedef,
		'DW_TAG_subprogram': mkDoc_subprogram,
		'DW_TAG_pointer_type': mkDoc_empty,
		'DW_TAG_base_type': mkDoc_empty,
		'DW_TAG_variable': mkDoc_variable,

		# FIXME: TBD
		'DW_TAG_union_type': mkDoc_empty,

		# the following types don't need to handle in mkDoc. 
		# Or mkDoc_typeref supports are enough.
		'DW_TAG_base_type': mkDoc_empty,
		'DW_TAG_volatile_type': mkDoc_empty,
		'DW_TAG_array_type': mkDoc_empty,
		'DW_TAG_constant': mkDoc_empty,
		'DW_TAG_packed_type': mkDoc_empty,
		'DW_TAG_const_type': mkDoc_empty
	}

	if ((cv) == (None)):
		print("[warning] ignored " + die.tag + "(%s) type not supported" % mkDoc_diename(cu, die))
		return nothing()

	(_, die) = cv
	if die.tag in dispatch:
		return dispatch[die.tag](cv)

# cv -> M doc
def mkDoc_compile_unit((cu, die)):
	notOrdered = [child for child in die.iter_children()]

	# all subprogram which is a kind of function should be placed at bottom
	children = flatten(splitBy(isTagNotSubprogram, notOrdered))
	# [M doc]
	definitions = [mkDoc((cu, child)) for child in children]
	# (a -> b) -> F  a -> F b
	return fmap(lambda xs: flatten(intersperse(xs, P.newline())), 
				sequence(definitions))
	#return flatten(intersperse(definitions, P.newline()))

def isTagNotSubprogram(die):
	return die.tag != 'DW_TAG_subprogram'

def mkDoc_variable(cu, die):
	name = mkDoc_diename(cu, die)
	varType = get_die_type(cu, die)
	#FIXME function pointer declaration 
	return mkDoc_typeref(cu, varType) + P.space() + name + P.text(";") 

# cv -> M doc
def mdoc_structure_type((cu, die)):
	cv = (cu, die)
	# struct <name> " {" [<member>] " };"
	return bind(mdoc_name(cv), lambda name:
		   bind(mdoc_decl_function_struct_type_getter(cv), lambda struct_getter:
		   bind(unit(die.iter_children()), lambda members:
		   bind(unit(P.block(intersperse([mdoc_member(cv) for member in members], P.newline()))), lambda docMembers:
		   unit(P.text("struct ") + name + P.space() + docMembers + P.text(";") + P.newline() + struct_getter)))))

'''
	name = mdoc_name(cv)
	# FIXME: use sequence Monad for error handling for each member
	members = [mdoc_member(cv) for member in die.iter_children()]
	print 'CHECK(members):' 
	print members
	exit(0)
	docMembers = P.block(intersperse(members, P.newline()))
	print 'CHECK(docMembers):' + docMembers
	decl_default_type_value_getter = mkDoc_decl_function_struct_type_getter(cu, die)
	return unit(P.text("struct ") + name + P.space() + docMembers + P.text(";") + P.newline() + decl_default_type_value_getter)
'''

# cv -> M doc
def mdoc_decl_function_struct_type_getter(cv):
	returnType = mdoc_typeref(cv)
	name = P.text('default_value_') + mdoc_name(cv)
	params = P.empty()
	decl_temp = mkDoc_decl_var(returnType, P.text('temp'), P.text('{0, }'))
	stmt_return = mkDoc_stmt_return(P.text('temp'))
	block = P.block(decl_temp + P.newline() + stmt_return)
	return unit(P.text("static ") + mkDoc_decl_function(returnType, name, params, block))

# cv -> M doc
def mdoc_member(cv):
	return bind(mdoc_name(cv), lambda name:
		   bind(die_type(cv), lambda dieType:
		   mdoc_typeref(cv) + P.space() + name + P.text(";")))

def mkDoc_formalparameter(cu, die):
	return mkDoc_typeref(cu, get_die_type(cu, die)) + P.space() + mkDoc_diename(cu, die)

# FIXME: refactor
def mkDoc_subprogram(cu, die):
	# <return-type> <function-name> <params>	
	name = mkDoc_diename(cu, die)
	typeDie = get_die_type(cu, die) 
	# TODO: use Monad. if die has no DW_AT_type, return P.text("void "), otherwise typeref(die.type)
	returnType = mkDoc_typeref(cu, typeDie) if typeDie else P.text("void ")
	params = [mkDoc_formalparameter(cu, child) for child in die.iter_children()
									   if child.tag == 'DW_TAG_formal_parameter']
	paramsCallback = params + P.text("int stubCallCount")

	varType = P.text("STUBGEN_") + name + P.text("_CALLBACK")
	decl_typedef_callback = mkDoc_decl_typedef_fp(returnType, paramsCallback, varType)
	
	
	varFp = name + P.text("_Callback")
	value = P.text("(") + varType + P.text(") 0")
	decl_var_callback_fp = mkDoc_decl_static_var(varType, varFp, value)

	
	paramNamesCallback = [mkDoc_diename(cu, child) for child in die.iter_children()
				if child.tag == 'DW_TAG_formal_parameter'] + P.text("stubCallCount++")
	callExp = mkDoc_exp_function_call(varFp, paramNamesCallback)
	thenBlock = P.block(P.text("static int stubCallCount = 0;") + P.newline() + (P.text("return ") if typeDie else P.empty()) + callExp + P.text(";"))
	# FIXME: use monad
	elseBlock = P.block(mkDoc_stmt_return(mkDoc_exp_call_default_type_value(cu, typeDie)))
	if_stmt = mkDoc_stmt_if(varFp, thenBlock, elseBlock)
	# return, name, params, block
	stub_function = mkDoc_decl_function(returnType, name, params, P.block(if_stmt))

	# decl callback setter function
	# void XXX_StubWithCallback (STUBGEN_XXX_CALLBACK cb)
	setter = name + P.text('_StubWithCallback')
	setter_param = [varType + P.text(' cb')] 
	setter_body = P.block(varFp + P.text(' = cb;'))
	setter_function = mkDoc_decl_function(P.text('void'), setter, setter_param, setter_body)
	return intersperse([decl_typedef_callback, decl_var_callback_fp, stub_function, setter_function], P.newline()) + P.newline() 

# FIXME: use monad
def mkDoc_stmt_return(doc):
	if doc == None:
		return P.empty()
	else:
		return P.text("return ") + doc + P.text(";")

# typeDie = None | DIE of type
# FIXME: how about const type?
def mkDoc_exp_call_default_type_value(cu, typeDie):
	if typeDie == None:
		return None
	originType = get_origin_type(cu, typeDie)
	if originType.tag == 'DW_TAG_base_type':
		return P.text('0')
	elif originType.tag == 'DW_TAG_pointer_type':
		return P.text('0')
	
	# composite(struct) type
	return mkDoc_exp_function_call(P.text('default_value_') + mkDoc_diename(cu, originType), [])

def get_origin_type(cu, die):
	if die.tag == 'DW_TAG_typedef':
		return get_origin_type(cu, get_die_type(cu, die))
	return die

# function_name: Doc
# argList: [Doc]
def mkDoc_exp_function_call(function_name, argList):
	return function_name + P.text("(") + intersperse(argList, P.comma() + P.space()) + P.text(")")

# cond = Doc of exp
# thenPart = Doc of block
# elsePart = Doc of block
def mkDoc_stmt_if(cond, thenPart, elsePart):
	return P.text("if (") + cond + P.text(") ") + thenPart + P.newline() + P.text("else ") + elsePart

# retType: Doc of string
# fname: Doc of string
# params: [Doc] of formal parameter
# body: Doc of block statement
def mkDoc_decl_function(retType, fname, params, body):
	assert body
	assert len(body) >= 2
	assert body[0] == '{'
	return retType + P.space() + fname + P.text(" (") + intersperse(params, P.comma()) + P.text(") ") + body

def mkDoc_decl_static_var(typeName, name, value):
	return P.text("static ") + mkDoc_decl_var(typeName, name, value)

def mkDoc_decl_var(typeName, name, value):
	return typeName + P.space() + name + P.text(" = ") + value + P.text(";")

# typedef statement of function pointer 
# params
# - returnType: Doc
# - params: [Doc]
# - typedefName: Doc
def mkDoc_decl_typedef_fp(returnType, params, typedefName):
	return P.text("typedef ") + returnType + P.text("(*") + typedefName + P.text(")") + P.text("(") + intersperse(params, P.text(', ')) + P.text(");")

# cv -> M doc
def mkDoc_empty((cu, die)):
	return unit(P.empty())

# cv -> M doc
def mdoc_typedef(cv):
	m_cv = unit(cv)
	doc = orElse(bind(m_cv, mdoc_typedef_fp), 
		         bind(m_cv, mdoc_typedef_normal))
	return doc

# cv -> M doc
def mdoc_typedef_normal(cv):
	return bind(mdoc_name(cv), lambda name:
		   bind(mdoc_typeref(cv), lambda srcType:
		   unit(P.text("typedef ")  + srcType + P.space() + name)))

# Abstraction LEVEL
# - doc, M doc
# - cv, M cv
#
# transfomation: cv -> M cv ->* M doc
#   phase 1. cv -> M cv			# lift function
#   phase 2. M cv -> M cv		# ?
#   phase 3. cv -> doc			# pure function
#   phase 4. M cv -> M doc		# monadic transformer
#
#   M cv -> M doc

# cv -> M doc
#	e.g) typedef void (*STUBGEN_api1_CALLBACK) ();
#	cv.type == DW_TAG_typedef
#	cv.type.type == DW_TAG_pointer_type
#	cv.type.type.type == DW_TAG_subroutine_type
def mdoc_typedef_fp(cv):
	m_cv = unit(cv)
	m_subroutine = bind(m_cv, lambda cv:
				   bind(is_pointer_type(cv), lambda pointer:
				   bind(die_type(pointer), lambda pointed:
				   bind(die_type(pointed), lambda pointed: unit(pointed)))))

	m_params = bind(m_subroutine, lambda (cu, die):
		unit(sequence([mdoc_formalparameter((cu, child)) for child in die.iter_children()]))
	)
	m_docParams = bind(m_params, lambda docs: unit(intersperse(docs, P.comma())))
	m_returnType = chain(m_subroutine, [die_type, mdoc_typeref])
	
	return bind(m_returnType, lambda ret:
		   bind(m_docParams, lambda params:
		   bind(mdoc_name(cv), lambda name:
		   unit(P.text("typedef " + ret) + P.text(" (*") + name + P.text(") ") + params))))

# cv -> M doc 
def mdoc_typeref(cv):
	genDoc = {
		'DW_TAG_structure_type': 
			lambda cv: bind(mdoc_name(cv), lambda name: unit(P.text("struct ") + name)),
		'DW_TAG_typedef': mdoc_name,
		'DW_TAG_union_type': mdoc_name,
		'DW_TAG_base_type': mdoc_name,
		'DW_TAG_const_type': 
			lambda cv: bind(die_type(cv), lambda typename: unit(P.text("const " + typename))),
		'DW_TAG_pointer_type': 
			lambda cv: mkDoc_typeref(cu, get_die_type(cu, die)) + P.text("*"),
	}

	if (cv) == (None):
		return unit("void")

	(_, die) = cv
	if die.tag in genDoc:
		return genDoc[die.tag](cv)

# cv -> M cv
def pointed_type(cv):
	return chain(cv, [is_pointer_type, die_type])

def subroutine_return_type(cv):
	return chain(cv, [is_subroutine_type, die_type])
			
# cv -> M cv
def is_pointer_type(cv):
	return is_die_tag(cv, 'DW_TAG_pointer_type')

# cv -> M cv
def is_subroutine_type(cv):
	return is_die_tag(cv, 'DW_TAG_subroutine_type')

# cv -> M cv
def die_type((cu, die)):
	if 'DW_AT_type' not in die.attributes:
		return nothing()
	offset = die.attributes['DW_AT_type'].value
	return get_die_by_offset(cu, offset)

# cv -> M doc 
def mdoc_name((cu, die)):
	if 'DW_AT_name' not in die.attributes:
		return nothing()
	return unit(P.text(die.attributes['DW_AT_name'].value))

# cu -> int -> M cv
def get_die_by_offset(cu, offset):
	target = cu.cu_offset + offset
	for die in cu.iter_DIEs():
		if die.offset == target:
			cv = (cu, die)
			return unit(cv)
	nothing()

# cv -> string -> M cv
def is_die_tag(cv, tagname):
	if value(cv).tag != tagname:
		return nothing()
	return unit(cv)

def mget_die_type(cu, die):
	if 'DW_AT_type' not in die.attributes:
		return fail()
	offset = die.attributes['DW_AT_type'].value
	return get_die_by_offset(cu, offset)

def mget_die_by_offset(cu, offset):
	target = cu.cu_offset + offset
	for die in cu.iter_DIEs():
		if die.offset == target:
			return success(die)

	return fail()

'''
def is_static_lib(path):
	_, extension = os.path.splitext(path)
	return extension == ".a"

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Stub generator')
	parser.add_argument('targets', metavar='FILE', type=str, nargs='+',
		help='list of input object file')
	parser.add_argument('-o', '--outdir', dest='outdir',
		help='specify output directory. [default is current directory]')

	args = parser.parse_args()
	outdir = args.outdir or '.'
	targets = args.targets 
	for target in targets:
		print '+ Generating stub sources for ' + target
		if is_static_lib(target):
			generate_stubs_from_staticlib(target, outdir)	
		else:
			generate_stubs_from_bin(target, outdir)

'''
