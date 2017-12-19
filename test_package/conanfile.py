from conans import ConanFile

class Ld64TestConan(ConanFile):
    generators = 'qbs'

    def build(self):
        self.run('/usr/local/bin/clang++ -c %s/test_package.cc -o test_package.o' % self.source_folder)
        self.run('bin/ld -macosx_version_min 10.10 -lc test_package.o -o test_package')

    def imports(self):
        self.copy('ld', dst='bin', src='bin')

    def test(self):
        self.run('./test_package')
        self.run('bin/ld -v')

        # Ensure we only link to system libraries.
        # libLTO.dylib is OK since it's lazy-loaded and we never use it.
        self.run('! (otool -L bin/ld | tail +3 | egrep -v "^\s*(/usr/lib/|/System/|@rpath/libLTO\.dylib)")')