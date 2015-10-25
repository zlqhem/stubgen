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
 * distinguish naming of mdoc from DIE and from Doc
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
	assert isMonadicValue(mval)
	(cv, err_msg) = mval
	if (cv == None):
		return error(err_msg)
	ret = mf(cv)
	if not isMonadicValue(ret):
		print 'mval '
		print mval
		print 'ret ' 
		print ret
		assert isMonadicValue(ret)
	return ret

def isMonadicValue(mval):
	return isinstance(mval, tuple) and len(mval) == 2;	

def nothing():
	return (None, '')

def error(message):
	return (None, message)

def value(mval):
	(val, _) = mval
	if (None == val):
		print ('There is no value')
		exit(0)
	return val

# M x -> M x -> M x
def orElse(mval, elseVal):
	(val, err) = mval

	if val:
		return mval
	else:
		return elseVal

# [M a] -> M [a]
# if x in xs is ([], None), then it evaluates to [[]]
def sequence(xs):
	m_r = unit([])
	for m_x in xs:
		m_r = bind(m_x, lambda x: 
			  bind(m_r, lambda r: unit(r + [x])))
	return m_r

# M a -> [(a -> M a)] -> M a
def chain(v, fs):
	m_ret = v
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

# string -> string -> [string]
def generate_stubs_from_bin(binpath, outdir='./'):
	m_files = bind(generate_docs(binpath), lambda docs:
			  unit([doc2file(doc, get_stub_path(binpath + '-' + str(idx), outdir)) for doc, idx in izip(docs, count(0))]))
	m_files = orElse(m_files, unit([]))
	return value(m_files)
		  

# .o | .so
# string -> string -> [string]
def generate_stubs_from_bin_legacy(binpath, outdir='./'):
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

# string -> M [doc]
def generate_docs(filename):
	with open(filename, 'rb') as fd:
		return generate_docs_from_stream(filename, fd)

# string -> file-handle -> M [doc]
def generate_docs_from_stream(filename, fd):
	elffile = ELFFile(fd)

	if not elffile.has_dwarf_info():
		print('    ' + filename + ' has no DWARF info')
		return []

	dwarfinfo = elffile.get_dwarf_info()

	# cu: compilation unit
	# DIE: debug information entry
	
	docs = [mdoc((cu, cu.get_top_DIE())) for cu in dwarfinfo.iter_CUs()]
	return sequence(docs)

# cv -> M doc
def mdoc(cv):
	dispatch = {
		'DW_TAG_compile_unit': mdoc_compile_unit,
		'DW_TAG_structure_type': mdoc_structure_type,
		'DW_TAG_typedef': mdoc_typedef,
		'DW_TAG_subprogram': mdoc_subprogram,
		'DW_TAG_pointer_type': mdoc_empty,
		'DW_TAG_base_type': mdoc_empty,
		'DW_TAG_variable': mdoc_variable,

		# FIXME: TBD
		'DW_TAG_union_type': mdoc_empty,

		# the following types don't need to handle in mdoc. 
		# Or mkDoc_typeref supports are enough.
		'DW_TAG_base_type': mdoc_empty,
		'DW_TAG_volatile_type': mdoc_empty,
		'DW_TAG_array_type': mdoc_empty,
		'DW_TAG_constant': mdoc_empty,
		'DW_TAG_packed_type': mdoc_empty,
		'DW_TAG_const_type': mdoc_empty
	}
	(_, die) = cv
	if die.tag in dispatch:
		(doc, err) = dispatch[die.tag](cv)
		if err != None :
			assert 0
		return dispatch[die.tag](cv)
	else:
		return mdoc_empty(cv)

# cv -> M doc
def mdoc_compile_unit((cu, die)):
	notOrdered = [child for child in die.iter_children()]

	# all subprogram which is a kind of function should be placed at bottom
	children = flatten(splitBy(isTagNotSubprogram, notOrdered))
	# [M doc]
	definitions = [mdoc((cu, child)) for child in children]
	# (a -> b) -> F  a -> F b
	return fmap(lambda xs: flatten(intersperse(xs, P.newline())), 
				sequence(definitions))
	#return flatten(intersperse(definitions, P.newline()))

def isTagNotSubprogram(die):
	return die.tag != 'DW_TAG_subprogram'

# cv -> M doc
def mdoc_variable(cv):
	return bind(mdoc_name(cv), lambda name:
		   bind(mdie_type(cv), lambda dieType:
		   bind(mdoc_typeref(dieType), lambda typeref:
		   unit(P.text(typeref) + P.space() + P.text(name) + P.text(";")))))

# cv -> M doc
def mdoc_structure_type((cu, die)):
	cv = (cu, die)
	# struct <name> " {" [<member>] " };"
	return bind(mdoc_name(cv), lambda name:
		   bind(mdoc_decl_function_struct_type_getter(cv), lambda struct_getter:
		   bind(unit(die.iter_children()), lambda members:
		   #bind(unit(P.block(intersperse([mdoc_member((cu, member)) for member in members], P.newline()))), lambda docMembers:
		   bind(sequence([mdoc_member((cu, member)) for member in members]), lambda docMembers:
		   unit(P.text("struct ") + name + P.space() + P.block(intersperse(docMembers, P.newline())) + P.text(";") + P.newline() + struct_getter)))))

# cv -> M doc
def mdoc_decl_function_struct_type_getter(cv):
	returnType = mdoc_typeref(cv)
	# FIXME: use bind
	name = P.text('default_value_') + value(mdoc_name(cv))
	params = P.empty()
	decl_temp = doc_decl_var(value(returnType), P.text('temp'), P.text('{0, }'))
	stmt_return = doc_stmt_return(P.text('temp'))
	block = P.block(decl_temp + P.newline() + stmt_return)
	return unit(P.text("static ") + doc_decl_function(value(returnType), name, params, block))

# cv -> M doc
# FIXME: check 
def mdoc_member(cv):
	return bind(mdoc_name(cv), lambda name:
		   bind(mdie_type(cv), lambda dieType:
		   bind(mdoc_typeref(dieType), lambda typeref:
		   unit(typeref + P.space() + name + P.text(";")))))

# cv -> M doc
def mdoc_formalparameter(cv):
	# may not have name
	return bind(orElse(mdoc_name(cv), unit(P.space())), lambda name:
		   bind(mdie_type(cv), lambda dieType:
		   bind(mdoc_typeref(dieType), lambda typeref:
		   unit(P.text(typeref) + P.space() + P.text(name)))))

'''

# callback type of stub function
typedef <returnType> (*STUBGEN_<name>_CALLBACK) ([<param>], int stubCallCount);

# declaration of callback pointer variable
STUBGEN_<name>_CALLBACK <name>_Callback = (STUBGEN_<name>_CALLBACK) 0;

# definition of stub function
<returnType> <name> ([<param>])
{
	if (<name>_Callback)
	{
		static int stubCallCount = 0;
		return <name>_Callback([<param-name>], stubCallCount++);
	}
	else
	{
		return default_value_<name>;
	}
}

'''
# cv -> M doc 
def mdoc_stubfunction(cv):
	return bind(mdoc_name(cv), lambda name:
		   bind(mdie_type(cv), lambda die_type:
		   bind(mdoc_typeref(die_type), lambda return_type:
		   bind(unit([mdoc_formalparameter(cu, child) for child in die.iter_children() if child.tag == 'DW_TAG_formal_parameter']),
				lambda params:
		   bind(unit(name + P.text("_Callback")), lambda var_functionpointer:
		   bind(unit(P.text("STUBGEN_") + name + P.text("_CALLBACK")), lambda var_type:
		   bind(unit(P.text("(" + var_type + P.text(") 0"))), lambda value:
		   bind(unit(), lambda paramNamesCallback:
		   bind(unit(doc_exp_function_call(var_type, sequence(paramNamesCallback))), lambda call_exp:
		   bind(unit(P.block(P.text("static int stubCallCount = 0;" + P.newline() + (P.text("return ") if die_type else P.empty()) + callExp + P.text(";")))), lambda then_block:
		   bind(unit(), lambda else_block:
		   bind(unit(), lambda if_stmt:
		   unit(doc_decl_function(return_type, name, params, P.block(if_stmt)))))))))))))))

# cv -> M doc
def mdoc_subprogram(cv):
	# TODO: refactor and fix
	return unit(P.text(''))
'''
	(cu, die) = cv
	# <return-type> <function-name> <params>	
	name = mdoc_name(cv)
	typeDie = mdie_type(cv) 
	# TODO: use Monad. if die has no DW_AT_type, return P.text("void "), otherwise typeref(die.type)
	returnType = mkDoc_typeref(cu, typeDie) if typeDie else P.text("void ")
	params = [mdoc_formalparameter(cu, child) for child in die.iter_children()
									   if child.tag == 'DW_TAG_formal_parameter']
	paramsCallback = params + P.text("int stubCallCount")

	varType = P.text("STUBGEN_") + value(name) + P.text("_CALLBACK")
	decl_typedef_callback = mkDoc_decl_typedef_fp(returnType, paramsCallback, varType)
	
	
	varFp = value(name) + P.text("_Callback")
	value = P.text("(") + varType + P.text(") 0")
	decl_var_callback_fp = doc_decl_static_var(varType, varFp, value)

	# [M doc]
	paramNamesCallback = [mdoc_name(cu, child) for child in die.iter_children()
				if child.tag == 'DW_TAG_formal_parameter'] + P.text("stubCallCount++")
	callExp = mkDoc_exp_function_call(varFp, sequence(paramNamesCallback))
	thenBlock = P.block(P.text("static int stubCallCount = 0;") + P.newline() + (P.text("return ") if typeDie else P.empty()) + callExp + P.text(";"))
	# FIXME: use monad
	elseBlock = P.block(doc_stmt_return(value(mdoc_exp_call_default_type_value(cv))))
	if_stmt = doc_stmt_if(varFp, thenBlock, elseBlock)
	# return, name, params, block
	stub_function = doc_decl_function(returnType, name, params, P.block(if_stmt))

	# decl callback setter function
	# void XXX_StubWithCallback (STUBGEN_XXX_CALLBACK cb)
	setter = name + P.text('_StubWithCallback')
	setter_param = [varType + P.text(' cb')] 
	setter_body = P.block(varFp + P.text(' = cb;'))
	setter_function = doc_decl_function(P.text('void'), setter, setter_param, setter_body)
	return intersperse([decl_typedef_callback, decl_var_callback_fp, stub_function, setter_function], P.newline()) + P.newline() 
'''


# FIXME: refactor
def mdoc_subprogram_legacy(cv):
	(cu, die) = cv
	# <return-type> <function-name> <params>	
	name = mdoc_name(cv)
	typeDie = mdie_type(cv) 
	# TODO: use Monad. if die has no DW_AT_type, return P.text("void "), otherwise typeref(die.type)
	returnType = mkDoc_typeref(cu, typeDie) if typeDie else P.text("void ")
	params = [mkDoc_formalparameter(cu, child) for child in die.iter_children()
									   if child.tag == 'DW_TAG_formal_parameter']
	paramsCallback = params + P.text("int stubCallCount")

	varType = P.text("STUBGEN_") + value(name) + P.text("_CALLBACK")
	decl_typedef_callback = mkDoc_decl_typedef_fp(returnType, paramsCallback, varType)
	
	
	varFp = value(name) + P.text("_Callback")
	value = P.text("(") + varType + P.text(") 0")
	decl_var_callback_fp = doc_decl_static_var(varType, varFp, value)

	# [M doc]
	paramNamesCallback = [mdoc_name(cu, child) for child in die.iter_children()
				if child.tag == 'DW_TAG_formal_parameter'] + P.text("stubCallCount++")
	callExp = mkDoc_exp_function_call(varFp, sequence(paramNamesCallback))
	thenBlock = P.block(P.text("static int stubCallCount = 0;") + P.newline() + (P.text("return ") if typeDie else P.empty()) + callExp + P.text(";"))
	# FIXME: use monad
	elseBlock = P.block(doc_stmt_return(value(mdoc_exp_call_default_type_value(cv))))
	if_stmt = doc_stmt_if(varFp, thenBlock, elseBlock)
	# return, name, params, block
	stub_function = doc_decl_function(returnType, name, params, P.block(if_stmt))

	# decl callback setter function
	# void XXX_StubWithCallback (STUBGEN_XXX_CALLBACK cb)
	setter = name + P.text('_StubWithCallback')
	setter_param = [varType + P.text(' cb')] 
	setter_body = P.block(varFp + P.text(' = cb;'))
	setter_function = doc_decl_function(P.text('void'), setter, setter_param, setter_body)
	return intersperse([decl_typedef_callback, decl_var_callback_fp, stub_function, setter_function], P.newline()) + P.newline() 

def doc_stmt_return(doc):
	if doc == None:
		return P.empty()
	else:
		return P.text("return ") + doc + P.text(";")

# typeDie = None | DIE of type
# FIXME: how about const type?
# cv -> M doc
def mdoc_exp_call_default_type_value(cv):
	(cu, die) = cv
	if die == None:
		return error('unexpected DIE(None)')
	originType = get_origin_type(cu, typeDie)
	if originType.tag == 'DW_TAG_base_type':
		return unit(P.text('0'))
	elif originType.tag == 'DW_TAG_pointer_type':
		return unit(P.text('0'))
	
	# composite(struct) type
	return bind(mdoc_diename((cu, originType)), lambda name:
		   unit(doc_exp_function_call(P.text('default_value_') + name, [])))

# cv -> cv
def get_origin_type(cv):
	(cu, die) = cv
	if die.tag == 'DW_TAG_typedef':
		return get_origin_type(cu, get_die_type(cu, die))
	return die

# function_name: Doc
# argList: [Doc]
def doc_exp_function_call(function_name, argList):
	return function_name + P.text("(") + intersperse(argList, P.comma() + P.space()) + P.text(")")

# cond = Doc of exp
# thenPart = Doc of block
# elsePart = Doc of block
# doc -> doc -> doc -> doc
def doc_stmt_if(cond, thenPart, elsePart):
	return P.text("if (") + cond + P.text(") ") + thenPart + P.newline() + P.text("else ") + elsePart

# retType: Doc of string
# fname: Doc of string
# params: [Doc] of formal parameter
# body: Doc of block statement
# doc -> doc -> [doc] -> doc -> doc
def doc_decl_function(retType, fname, params, body):
	assert body
	assert len(body) >= 2
	assert body[0] == '{'
	return retType + P.space() + fname + P.text(" (") + intersperse(params, P.comma()) + P.text(") ") + body

# doc -> doc -> doc -> doc
def doc_decl_static_var(typeName, name, value):
	return P.text("static ") + doc_decl_var(typeName, name, value)

# doc -> doc -> doc -> doc
def doc_decl_var(typeName, name, value):
	return typeName + P.space() + name + P.text(" = ") + value + P.text(";")

# typedef statement of function pointer 
# params
# - returnType: Doc
# - params: [Doc]
# - typedefName: Doc
def mkDoc_decl_typedef_fp(returnType, params, typedefName):
	return P.text("typedef ") + returnType + P.text("(*") + typedefName + P.text(")") + P.text("(") + intersperse(params, P.text(', ')) + P.text(");")

# cv -> M doc
def mdoc_empty(cv):
	return unit(P.empty())

# cv -> M doc
def mdoc_typedef(cv):
	typedef_functionpointer=  mdoc_typedef_fp(cv)
	typedef_normal = mdoc_typedef_normal(cv)

	doc = orElse(mdoc_typedef_fp(cv),
		         mdoc_typedef_normal(cv))
	return doc

# cv -> M doc
def mdoc_typedef_normal(cv):
	return bind(mdoc_name(cv), lambda name:
		   bind(mdoc_typeref(cv), lambda srcType:
		   unit(P.text("typedef ")  + srcType + P.space() + name + P.text(";"))))

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
	m_subroutine = chain(unit(cv), [mdie_type, mdie_type])

	m_params = bind(m_subroutine, lambda ((cu, die)):
		sequence([mdoc_formalparameter((cu, child)) for child in die.iter_children()])
	)
	m_docParams = bind(m_params, lambda docs: unit(intersperse(docs, P.comma())))
	m_returnType = chain(m_subroutine, [mdie_type, mdoc_typeref])
	
	return bind(m_returnType, lambda ret:
		   bind(m_docParams, lambda params:
		   bind(mdoc_name(cv), lambda name:
		   unit(P.text("typedef ") + ret + P.text(" (*") + name + P.text(") ") + params))))

# cv -> M doc 
# FIXME: typeref of type of cv
def mdoc_typeref(cv):
	genDoc = {
		'DW_TAG_structure_type': 
			lambda cv: bind(mdoc_name(cv), lambda name:
					   unit(P.text("struct ") + name)),
		'DW_TAG_typedef': mdoc_name,
		'DW_TAG_union_type': mdoc_name,
		'DW_TAG_base_type': mdoc_name,
		'DW_TAG_const_type': 
			lambda cv: bind(mdie_type(cv), lambda die_type: 
					   bind(mdoc_typeref(die_type), lambda typeref:
					   unit(P.text("const ") + typeref))),
		'DW_TAG_pointer_type':
			lambda cv: bind(mdie_type(cv), lambda die_type:
					   bind(mdoc_typeref(die_type), lambda typeref:
					   unit(typeref + P.text("*"))))
	}

	# FIXME: which case?
	if (cv) == (None):
		return unit(P.text("void"))

	(_, die) = cv
	if die.tag in genDoc:
		return genDoc[die.tag](cv)

# cv -> M cv
def mdie_type((cu, die)):
	if 'DW_AT_type' not in die.attributes:
		m_name = orElse(mdoc_name((cu, die)), unit(P.text("Nil")))
		name = value(m_name)[0]
		return error(name + ':' + die.tag + ' does not have DW_AT_type attribute')
	offset = die.attributes['DW_AT_type'].value
	return get_die_by_offset(cu, offset)

# cv -> M doc 
def mdoc_name((cu, die)):
	if 'DW_AT_name' not in die.attributes:
		return error(die.tag + ' does not have DW_AT_name attribute')
	return unit(P.text(die.attributes['DW_AT_name'].value))

# cu -> int -> M cv
def get_die_by_offset(cu, offset):
	target = cu.cu_offset + offset
	for die in cu.iter_DIEs():
		if die.offset == target:
			cv = (cu, die)
			return unit(cv)
	return error('cannot find the offset (' + offset + ')')

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
