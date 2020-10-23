from conans import ConanFile

class Ld64TestConan(ConanFile):
    def build(self):
        self.run('clang++ -mmacosx-version-min=10.11 -c %s/test_package.cc -o test_package.o' % self.source_folder)
        self.run('bin/ld -macosx_version_min 10.11 -lc test_package.o -o test_package')

    def imports(self):
        self.copy('*', src='bin', dst='bin')
        self.copy('*', src='lib', dst='lib')

    def test(self):
        self.run('./test_package')
        self.run('bin/ld -v')

        # Ensure we only link to system libraries and our libtapi.
        # libLTO.dylib is OK since it's lazy-loaded and we never use it.
        self.run('! (otool -L bin/ld | tail +3 | egrep -v "^\s*(/usr/lib/|/System/|@rpath/libLTO\.dylib|@rpath/libtapi\.dylib)")')
        self.run('! (otool -L bin/ld | fgrep "libstdc++")')
        self.run('! (otool -l bin/ld | grep -A2 LC_RPATH | cut -d"(" -f1 | grep "\s*path" | egrep -v "^\s*path @(executable|loader)_path")')
