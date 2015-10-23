import pytest 
import os

from src import stubgen

class TestClass:
	def setup_method(self, method):
		self.basedir = os.path.dirname(os.path.abspath(__file__))

	def test_shared_lib(self):
		target = self.basedir + "/sample-lib/libmyapi.so"
		self.areStubsFromBinBuildable(target)

	def test_static_lib(self):
		target = self.basedir + '/sample-lib/libmyapi.a'
		self.areStubsFromStaticLibBuildable(target)

	def test_single_object(self):
		target = self.basedir + "/sample-lib/src/api1.o"
		self.areStubsFromBinBuildable(target)

	def test_object_compiled_from_generated_stub(self):
		target = self.basedir + "/sample-lib/src/api1.o"
		stubs = stubgen.generate_stubs_from_bin(target)
		assert stubs
		stub_obj = './api1-stub.o'
		#assert 0 == os.system("gcc -c -g -o " + stub_obj + ' ' + stubs[0])
		#os.system("readelf -w " + stub_obj + "  > " + stub_obj + ".dwarf")
		#self.areStubsFromBinBuildable(stub_obj)
		
	def areStubsFromStaticLibBuildable(self, staticlib):
		self.areGeneratedStubsBuildable(staticlib, stubgen.generate_stubs_from_staticlib)

	def areStubsFromBinBuildable(self, binary):
		self.areGeneratedStubsBuildable(binary, stubgen.generate_stubs_from_bin)
		
	def areGeneratedStubsBuildable(self, target, stubgen):
		stubs = stubgen(target)
		[self.isBuildable(stub) for stub in stubs]
		
	def isBuildable(self, src):
		assert 0 == os.system("gcc -c " + src)
		return True

