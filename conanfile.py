from conans import ConanFile, tools

class Ld64Conan(ConanFile):
    name = 'ld64'

    # This version is from Xcode 6.3, which is the last version that purports to support Mac OS 10.10.0.
    # https://en.wikipedia.org/wiki/Xcode#Xcode_5.0_-_6.x_(since_arm64_support)
    # https://opensource.apple.com/release/developer-tools-63.html
    # https://b33p.net/kosada/node/4144
    ld64_version = '242'

    # ld64 needs dyld as a build-time (but not a runtime) dependency.
    # This version is from Mac OS 10.10.0.
    # https://opensource.apple.com/release/os-x-1010.html
    dyld_version = '353.2.1'

    package_version = '2'
    version = '%s-%s' % (ld64_version, package_version)

    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'https://opensource.apple.com/'
    license = 'https://opensource.apple.com/source/ld64/ld64-%s/APPLE_LICENSE.auto.html' % ld64_version
    description = 'Combines several object files and libraries, resolves references, and produces an ouput file'
    ld64_source_dir = 'ld64-%s' % ld64_version
    dyld_source_dir = 'dyld-%s' % dyld_version
    llvm_dir = '/usr/local/Cellar/llvm/3.2' # @todo Make this an actual Conan dependency.

    def source(self):
        tools.get('https://opensource.apple.com/tarballs/ld64/ld64-%s.tar.gz' % self.ld64_version,
                  sha256='bec1a5e20b599d108be0017736833c1f6212ea26c67f20d8437abc5d23433c36')
        tools.get('https://opensource.apple.com/tarballs/dyld/dyld-%s.tar.gz' % self.dyld_version,
                  sha256='051089e284c5a4d671b21b73866abd01d54e5ea1912cadf3a9b916890fb31540')

        # Remove the CrashReporter stuff, which isn't open source.
        tools.replace_in_file('%s/src/ld/Options.cpp' % self.ld64_source_dir,
                              '#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1070',
                              '#if 0')

    def build(self):
        with tools.chdir(self.ld64_source_dir):
            self.run('RC_SUPPORTED_ARCHS=x86_64 xcodebuild -target ld CLANG_X86_VECTOR_INSTRUCTIONS=no-sse4.1 HEADER_SEARCH_PATHS="../%s/include %s/include"'
                     % (self.dyld_source_dir,
                        self.llvm_dir))

    def package(self):
        self.copy('ld', src='%s/build/Release-assert' % self.ld64_source_dir, dst='bin')
