from conans import ConanFile, CMake, tools

class Ld64Conan(ConanFile):
    name = 'ld64'

    # ld64 version 274.1 is from Xcode 8.0, which purports to support macOS 10.11+,
    # and is the earliest version to support TBD + TAPI.
    # https://en.wikipedia.org/wiki/Xcode#Xcode_7.0_-_10.x_(since_Free_On-Device_Development)
    # https://opensource.apple.com/release/developer-tools-80.html
    # https://b33p.net/kosada/vuo/vuo/-/issues/4144
    # https://b33p.net/kosada/vuo/vuo/-/issues/17561
    # https://b33p.net/kosada/vuo/vuo/-/issues/17836
    ld64_version = '274.1'

    # Also from Xcode 8.0:
    dyld_version = '353.2.1'
    clang_version = '800.0.38'
    tapi_version = '1.30'

    package_version = '0'
    version = '%s-%s' % (ld64_version, package_version)

    requires = 'llvm/5.0.2-0@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'https://opensource.apple.com/'
    license = 'https://opensource.apple.com/source/ld64/ld64-%s/APPLE_LICENSE.auto.html' % ld64_version
    description = 'Combines several object files and libraries, resolves references, and produces an ouput file'
    ld64_source_dir = 'ld64-%s' % ld64_version
    dyld_source_dir = 'dyld-%s' % dyld_version
    clang_source_dir = 'clang-%s' % clang_version
    tapi_source_dir = '%s/src/projects/libtapi-%s' % (clang_source_dir, tapi_version)
    clang_build_dir = '_build_clang'
    exports_sources = '*.patch'

    def source(self):
        tools.get('https://opensource.apple.com/tarballs/ld64/ld64-%s.tar.gz' % self.ld64_version,
                  sha256='6cbe886717de833789fa562ec4889ebf9136ae5f7573d17d39836d3f5755b7ab')
        tools.get('https://opensource.apple.com/tarballs/dyld/dyld-%s.tar.gz' % self.dyld_version,
                  sha256='051089e284c5a4d671b21b73866abd01d54e5ea1912cadf3a9b916890fb31540')
        tools.get('https://opensource.apple.com/tarballs/clang/clang-%s.tar.gz' % self.clang_version,
                  sha256='2d4838fccb3f75537f0ed353229b6f520f9d6dbbf77244637302c20287c9e56c')
        with tools.chdir('%s/src/projects' % self.clang_source_dir):
            tools.get('https://opensource.apple.com/tarballs/tapi/tapi-%s.tar.gz' % self.tapi_version,
                      sha256='be2f3732c4ba7e9d78696fe43f0b31fa4963925ee6e4e5e11cc45603a83ff9a1')

        # Remove the CrashReporter stuff, which isn't open source.
        tools.replace_in_file('%s/src/ld/Options.cpp' % self.ld64_source_dir,
                              '#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1070',
                              '#if 0')

        with tools.chdir(self.ld64_source_dir):
            self.run('patch -p1 < ../libunwind_cfi.patch')

            # Don't include Swift demangling since we don't use it.
            tools.replace_in_file('src/create_configure',
                                  'if [ -f "${DT_TOOLCHAIN_DIR}/usr/lib/libswiftDemangle.dylib" ]; then',
                                  'if false; then')

            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '				SDKROOT = macosx.internal;',
                                  '				SDKROOT = macosx;')

        self.run('mv %s/APPLE_LICENSE %s/%s.txt' % (self.ld64_source_dir, self.ld64_source_dir, self.name))

    def build(self):
        tools.mkdir(self.clang_build_dir)
        with tools.chdir(self.clang_build_dir):
            cmake = CMake(self)
            cmake.definitions['LLVM_INCLUDE_TESTS'] = 'OFF'
            cmake.configure(source_dir='../%s/src' % self.clang_source_dir, build_dir='.')
            cmake.build(target='libtapi')

        with tools.chdir(self.ld64_source_dir):
            self.run('RC_SUPPORTED_ARCHS=x86_64 xcodebuild -target ld CLANG_X86_VECTOR_INSTRUCTIONS=no-sse4.1 HEADER_SEARCH_PATHS="../%s/include ../%s/src/include ../%s/include ../%s/projects/libtapi-%s/include src/ld"' % (self.dyld_source_dir, self.clang_source_dir, self.tapi_source_dir, self.clang_build_dir, self.tapi_version))

    def package(self):
        self.copy('ld', src='%s/build/Release-assert' % self.ld64_source_dir, dst='bin')
        self.copy('libtapi.dylib', src='%s/lib' % self.clang_build_dir, dst='lib')
        self.copy('%s.txt' % self.name, src=self.ld64_source_dir, dst='license')
