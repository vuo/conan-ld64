from conans import ConanFile, tools

class Ld64Conan(ConanFile):
    name = 'ld64'

    # ld64 version 253.3 is from Xcode 7.0, which purports to support macOS 10.11+,
    # and is the earliest version to support TBD files.
    # https://en.wikipedia.org/wiki/Xcode#Xcode_7.0_-_10.x_(since_Free_On-Device_Development)
    # https://opensource.apple.com/release/developer-tools-70.html
    # https://b33p.net/kosada/node/4144
    # https://b33p.net/kosada/node/17561
    ld64_version = '253.3'

    # ld64 needs dyld as a build-time (but not a runtime) dependency.
    # This version is from Mac OS 10.10.0.
    # https://opensource.apple.com/release/os-x-1010.html
    dyld_version = '353.2.1'

    # ld64 needs clang as a build-time (but not a runtime) dependency.
    # clang version 700.0.72 is from Xcode 7.0.
    # https://opensource.apple.com/release/developer-tools-70.html
    clang_version = '700.0.72'

    package_version = '0'
    version = '%s-%s' % (ld64_version, package_version)

    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'https://opensource.apple.com/'
    license = 'https://opensource.apple.com/source/ld64/ld64-%s/APPLE_LICENSE.auto.html' % ld64_version
    description = 'Combines several object files and libraries, resolves references, and produces an ouput file'
    ld64_source_dir = 'ld64-%s' % ld64_version
    dyld_source_dir = 'dyld-%s' % dyld_version
    clang_source_dir = 'clang-%s' % clang_version
    exports_sources = '*.patch'

    def source(self):
        tools.get('https://opensource.apple.com/tarballs/ld64/ld64-%s.tar.gz' % self.ld64_version,
                  sha256='76c02f6f297c251b66504e1115946bda6e1618640bc6cf03d0ad99b17bd8a5d6')
        tools.get('https://opensource.apple.com/tarballs/dyld/dyld-%s.tar.gz' % self.dyld_version,
                  sha256='051089e284c5a4d671b21b73866abd01d54e5ea1912cadf3a9b916890fb31540')
        tools.get('https://opensource.apple.com/tarballs/clang/clang-%s.tar.gz' % self.clang_version,
                  sha256='9b76776eed9e0e18064581a26fabce85f5699c5e93c8f797e9c3a8fbcd5d53d8')

        # Remove the CrashReporter stuff, which isn't open source.
        tools.replace_in_file('%s/src/ld/Options.cpp' % self.ld64_source_dir,
                              '#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1070',
                              '#if 0')

        with tools.chdir(self.ld64_source_dir):
            self.run('patch -p1 < ../libunwind_cfi.patch')

        self.run('mv %s/APPLE_LICENSE %s/%s.txt' % (self.ld64_source_dir, self.ld64_source_dir, self.name))

    def build(self):
        with tools.chdir(self.ld64_source_dir):
            self.run('RC_SUPPORTED_ARCHS=x86_64 xcodebuild -target ld CLANG_X86_VECTOR_INSTRUCTIONS=no-sse4.1 HEADER_SEARCH_PATHS="../%s/include ../%s/src/include src/ld"' % (self.dyld_source_dir, self.clang_source_dir))

    def package(self):
        self.copy('ld', src='%s/build/Release-assert' % self.ld64_source_dir, dst='bin')
        self.copy('%s.txt' % self.name, src=self.ld64_source_dir, dst='license')
