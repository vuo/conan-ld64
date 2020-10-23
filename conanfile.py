from conans import ConanFile, CMake, tools
import os

class Ld64Conan(ConanFile):
    name = 'ld64'

    # ld64 version 450.3 is from Xcode 10.2.
    # https://en.wikipedia.org/wiki/Xcode#Xcode_7.0_-_10.x_(since_Free_On-Device_Development)
    # https://opensource.apple.com/release/developer-tools-102.html
    # https://b33p.net/kosada/vuo/vuo/-/issues/4144
    # https://b33p.net/kosada/vuo/vuo/-/issues/17561
    # https://b33p.net/kosada/vuo/vuo/-/issues/17836
    ld64_version = '450.3'

    # dyld version 655.1.1 is from macOS 10.14.6.
    # https://opensource.apple.com/release/macos-10146.html
    dyld_version = '655.1.1'

    # Not from Xcode 10, but from the latest version that Apple provides:
    tapi_version = '1000.10.8'

    # Apple stopped publishing their LLVM/Clang source code after Xcode 8.2.1.
    # This is the earliest version that supports `add_llvm_install_targets`, required by tapi-1000.10.8.
    llvm_version = '6.0.1'

    package_version = '0'
    version = '%s-%s' % (ld64_version, package_version)

    requires = 'llvm/5.0.2-0@vuo/stable'
    build_requires = 'macos-sdk/10.11-0@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'https://opensource.apple.com/'
    license = 'https://opensource.apple.com/source/ld64/ld64-%s/APPLE_LICENSE.auto.html' % ld64_version
    description = 'Combines several object files and libraries, resolves references, and produces an ouput file'
    ld64_source_dir = 'ld64-%s' % ld64_version
    dyld_source_dir = 'dyld-%s' % dyld_version
    llvm_source_dir = 'llvm-%s.src' % llvm_version
    tapi_source_dir = '%s/projects/tapi-%s' % (llvm_source_dir, tapi_version)
    llvm_build_dir = '_build_llvm'
    exports_sources = '*.patch'

    def source(self):
        tools.get('https://opensource.apple.com/tarballs/ld64/ld64-%s.tar.gz' % self.ld64_version,
                  sha256='140619e676e099581771dbad98277850ff731cd23938bed95b4d7171616acca1')
        tools.get('https://opensource.apple.com/tarballs/dyld/dyld-%s.tar.gz' % self.dyld_version,
                  sha256='8ca6e3cf0263d3f69dfa65e0846e2bed051b0cff92e796352ad178e7e4c92f1d')

        tools.get('https://releases.llvm.org/%s/llvm-%s.src.tar.xz' % (self.llvm_version, self.llvm_version),
                  sha256='b6d6c324f9c71494c0ccaf3dac1f16236d970002b42bb24a6c9e1634f7d0f4e2')
        with tools.chdir('%s/projects' % self.llvm_source_dir):
            tools.get('https://releases.llvm.org/%s/cfe-%s.src.tar.xz' % (self.llvm_version, self.llvm_version),
                      sha256='7c243f1485bddfdfedada3cd402ff4792ea82362ff91fbdac2dae67c6026b667')
            tools.get('https://opensource.apple.com/tarballs/tapi/tapi-%s.tar.gz' % self.tapi_version,
                      sha256='827e996529974305ef7933f3fa790f7ed068caa29db8f8c30b8a83c6826503f7')

        # Remove the CrashReporter stuff, which isn't open source.
        tools.replace_in_file('%s/src/ld/Options.cpp' % self.ld64_source_dir,
                              '#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1070',
                              '#if 0')

        with tools.chdir(self.dyld_source_dir):
            tools.replace_in_file('include/mach-o/dyld.h',      '__API_UNAVAILABLE(bridgeos)', '')
            tools.replace_in_file('include/mach-o/dyld_priv.h', ', bridgeos(3.0)',             '')

        tools.patch(patch_file='ld64-arm64e.patch', base_path=self.ld64_source_dir)
        tools.patch(patch_file='ld64-tbd.patch',    base_path=self.ld64_source_dir)
        tools.patch(patch_file='tapi-vector.patch', base_path=self.tapi_source_dir)

        with tools.chdir(self.ld64_source_dir):
            # Don't include Swift demangling since we don't use it.
            tools.replace_in_file('src/create_configure',
                                  'if [ -f "${DT_TOOLCHAIN_DIR}/usr/lib/libswiftDemangle.dylib" ]; then',
                                  'if false; then')

            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '				SDKROOT = macosx.internal;',
                                  '				SDKROOT = macosx;')
            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '"-Wl,-lazy_library,$(DT_TOOLCHAIN_DIR)/usr/lib/libLTO.dylib"',
                                  '"-Wl,-lazy_library,%s/lib/libLTO.dylib"' % self.deps_cpp_info['llvm'].rootpath)

        self.run('mv %s/APPLE_LICENSE %s/%s.txt' % (self.ld64_source_dir, self.ld64_source_dir, self.name))

    def build(self):
        tools.mkdir(self.llvm_build_dir)
        with tools.chdir(self.llvm_build_dir):
            cmake = CMake(self)
            cmake.definitions['CMAKE_OSX_SYSROOT'] = self.deps_cpp_info['macos-sdk'].rootpath
            cmake.definitions['CMAKE_CXX_FLAGS']  = ' -I%s/../%s/projects/cfe-%s.src/include' % (os.getcwd(), self.llvm_source_dir, self.llvm_version)
            cmake.definitions['CMAKE_CXX_FLAGS'] += ' -I%s/projects/cfe-%s.src/include' % (os.getcwd(), self.llvm_version)
            cmake.definitions['LLVM_INCLUDE_TESTS'] = 'OFF'
            cmake.definitions['CLANG_TABLEGEN_EXE'] = 'clang-tblgen'
            cmake.configure(source_dir='../%s' % self.llvm_source_dir, build_dir='.')
            cmake.build(target='libtapi')

        with tools.chdir(self.ld64_source_dir):
            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '"-ltapi",',
                                  '"%s/../%s/lib/libtapi.dylib",' % (os.getcwd(), self.llvm_build_dir))
            self.run('RC_SUPPORTED_ARCHS=x86_64 xcodebuild -target ld HEADER_SEARCH_PATHS="../%s/include ../%s/include ../%s/include ../%s/projects/tapi-%s/include src/ld"' % (self.dyld_source_dir, self.llvm_source_dir, self.tapi_source_dir, self.llvm_build_dir, self.tapi_version))

    def package(self):
        self.copy('ld', src='%s/build/Release-assert' % self.ld64_source_dir, dst='bin')
        self.copy('libtapi.dylib', src='%s/lib' % self.llvm_build_dir, dst='lib')
        self.copy('%s.txt' % self.name, src=self.ld64_source_dir, dst='license')
