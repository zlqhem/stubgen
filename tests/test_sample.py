import pytest 
import os

from src import stubgen
from src import pretty as P

class TestClass:
	def setup_method(self, method):
		self.basedir = os.path.dirname(os.path.abspath(__file__))

	def get_stub_doc(self, file):
		return stubgen.generate_doc(file)

	def test_one(self):
		assert P.intersperse([["a"],["b"]], ["_"]) == [["a"], ["_"], ["b"]]

	def test_run_shared_lib(self):
		doc = self.get_stub_doc(self.basedir + "/sample/sample-lib/libmy.so")
		print(P.pretty(80, doc))

	def test_run_single_object(self):
		doc = self.get_stub_doc(self.basedir + "/sample/sample-lib/src/api1.o")
		print(P.pretty(80, doc))

'''
# ???
DW_TAG_subrange_type
DW_TAG_enumeration_type
DW_TAG_file_type
DW_TAG_set_type
DW_TAG_imported_declaration
DW_TAG_inlined_subroutin
DW_TAG_pointer_type
DW_TAG_reference_type
DW_TAG_string_type
DW_TAG_subroutine_type

DW_TAG_access_declaration
DW_TAG_class_type
DW_TAG_enumerator
DW_TAG_friend
DW_TAG_inheritance
DW_TAG_ptr_to_member_type
DW_TAG_template_type_param
DW_TAG_thrown_type

# block scope
DW_TAG_catch_block
DW_TAG_common_inclusion
DW_TAG_lexical_block
DW_TAG_template_value_param
DW_TAG_try_block
DW_TAG_with_stmt
DW_TAG_common_block
DW_TAG_label
'''

