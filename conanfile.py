from conans import ConanFile, CMake, tools
import os

class Ld64Conan(ConanFile):
    name = 'ld64'

    # ld64 version 530 is from Xcode 11.3.1.
    # https://en.wikipedia.org/wiki/Xcode#Xcode_7.0_-_10.x_(since_Free_On-Device_Development)
    # https://opensource.apple.com/release/developer-tools-1131.html
    # https://b33p.net/kosada/vuo/vuo/-/issues/4144
    # https://b33p.net/kosada/vuo/vuo/-/issues/17561
    # https://b33p.net/kosada/vuo/vuo/-/issues/17836
    ld64_version = '530'

    # dyld version 750.6 is from macOS 10.15.6.
    # https://opensource.apple.com/release/macos-10156.html
    dyld_version = '750.6'

    # Not from Xcode 11, but from the latest version that Apple provides:
    tapi_version = '1100.0.11'

    # Apple stopped publishing their LLVM/Clang source code after Xcode 8.2.1.
    # This is the earliest version that supports tapi-1100.0.11.
    llvm_version = '11.0.0'

    package_version = '5'
    version = '%s-%s' % (ld64_version, package_version)

    requires = 'llvm/5.0.2-3@vuo/stable'
    build_requires = 'macos-sdk/11.0-0@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'https://opensource.apple.com/'
    license = 'https://opensource.apple.com/source/ld64/ld64-%s/APPLE_LICENSE.auto.html' % ld64_version
    description = 'Combines several object files and libraries, resolves references, and produces an ouput file'
    ld64_source_dir = 'ld64-%s' % ld64_version
    dyld_source_dir = 'dyld-%s' % dyld_version
    llvm_source_dir = 'llvm-%s.src' % llvm_version
    tapi_source_dir = '%s/projects/tapi-%s' % (llvm_source_dir, tapi_version)

    build_llvm_x86_dir = '_build_llvm_x86'
    build_llvm_arm_dir = '_build_llvm_arm'
    install_universal_dir = '_install_universal'

    exports_sources = '*.patch'

    def source(self):
        tools.get('https://opensource.apple.com/tarballs/ld64/ld64-%s.tar.gz' % self.ld64_version,
                  sha256='ee37f0487601c08c7d133bc91cad2e9084d00d02aa4709d228a9a065960aa187')
        tools.get('https://opensource.apple.com/tarballs/dyld/dyld-%s.tar.gz' % self.dyld_version,
                  sha256='4fd378cf30718e0746c91b145b90ddfcaaa4c0bf01158d0461a4e092d7219222')

        tools.get('https://github.com/llvm/llvm-project/releases/download/llvmorg-%s/llvm-%s.src.tar.xz' % (self.llvm_version, self.llvm_version),
                  sha256='913f68c898dfb4a03b397c5e11c6a2f39d0f22ed7665c9cefa87a34423a72469')
        with tools.chdir('%s/projects' % self.llvm_source_dir):
            tools.get('https://github.com/llvm/llvm-project/releases/download/llvmorg-%s/clang-%s.src.tar.xz' % (self.llvm_version, self.llvm_version),
                      sha256='0f96acace1e8326b39f220ba19e055ba99b0ab21c2475042dbc6a482649c5209')
            tools.get('https://opensource.apple.com/tarballs/tapi/tapi-%s.tar.gz' % self.tapi_version,
                      sha256='1c1d7079e65c615cb12d58c1de5c49031e56774e1f17e55a57faa5d4253b9126')
            with tools.chdir('tapi-%s' % self.tapi_version):
                tools.replace_in_file('CMakeLists.txt', 'check_linker_flag("-Wl,-no_inits" LINKER_SUPPORTS_NO_INITS)', '')
                tools.replace_in_file('CMakeLists.txt', 'check_linker_flag("-Wl,-iosmac_version_min,12.0" LINKER_SUPPORTS_IOSMAC)', '')
                tools.patch(patch_file='../../../tapi.patch')

        # Remove the CrashReporter stuff, which isn't open source.
        tools.replace_in_file('%s/src/ld/Options.cpp' % self.ld64_source_dir,
                              '#if __MAC_OS_X_VERSION_MIN_REQUIRED >= 1070',
                              '#if 0')

        with tools.chdir(self.dyld_source_dir):
            tools.replace_in_file('include/mach-o/dyld.h',      '__API_UNAVAILABLE(bridgeos)', '')
            tools.replace_in_file('include/mach-o/dyld_priv.h', ', bridgeos(3.0)',             '')

        with tools.chdir(self.ld64_source_dir):
            # Don't include Swift demangling since we don't use it.
            tools.replace_in_file('src/create_configure',
                                  'if [ -f "${DT_TOOLCHAIN_DIR}/usr/lib/libswiftDemangle.dylib" ]; then',
                                  'if false; then')

            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '				SDKROOT = macosx.internal;',
                                  '				SDKROOT = macosx;')
            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '				VALID_ARCHS = "x86_64 i386 ppc";',
                                  '				VALID_ARCHS = "x86_64 arm64";')
            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '				MACOSX_DEPLOYMENT_TARGET = 10.14;',
                                  '				MACOSX_DEPLOYMENT_TARGET = 10.11;')

        self.run('mv %s/APPLE_LICENSE %s/%s.txt' % (self.ld64_source_dir, self.ld64_source_dir, self.name))

    def build(self):
        cmake = CMake(self)
        cmake.definitions['CMAKE_OSX_SYSROOT'] = self.deps_cpp_info['macos-sdk'].rootpath
        cmake.definitions['CMAKE_CXX_FLAGS']  = ' -I%s/%s/projects/clang-%s.src/include' % (os.getcwd(), self.llvm_source_dir, self.llvm_version)
        cmake.definitions['CMAKE_CXX_FLAGS'] += ' -I%s/%s/projects/clang-%s.src/include' % (os.getcwd(), self.build_llvm_x86_dir, self.llvm_version)
        cmake.definitions['CMAKE_OSX_DEPLOYMENT_TARGET'] = '10.11'
        cmake.definitions['LLVM_INCLUDE_TESTS'] = 'OFF'
        cmake.definitions['LLVM_TARGETS_TO_BUILD'] = 'X86;AArch64'
        cmake.definitions['CLANG_TABLEGEN_EXE'] = 'clang-tblgen'


        self.output.info("=== Build libtapi for x86_64 ===")
        cmake.definitions['CMAKE_OSX_ARCHITECTURES'] = 'x86_64'
        cmake.definitions['LLVM_DEFAULT_TARGET_TRIPLE'] = 'x86_64-apple-macos10.11.0'
        tools.mkdir(self.build_llvm_x86_dir)
        with tools.chdir(self.build_llvm_x86_dir):
            cmake.configure(source_dir='../%s' % self.llvm_source_dir, build_dir='.')
            cmake.build(target='libtapi')


        self.output.info("=== Build libtapi for arm64 ===")
        cmake.definitions['CMAKE_CROSSCOMPILING'] = 'ON'
        cmake.definitions['CMAKE_OSX_ARCHITECTURES'] = 'arm64'
        cmake.definitions['LLVM_DEFAULT_TARGET_TRIPLE'] = 'arm64-apple-macos10.11.0'
        cmake.definitions['LLVM_TARGET_ARCH'] = 'AArch64'
        # tblgen needs to run on the host, so it should be x86 even when cross-compiling for arm.
        cmake.definitions['LLVM_TABLEGEN'] = '%s/%s/bin/llvm-tblgen' % (os.getcwd(), self.build_llvm_x86_dir)
        cmake.definitions['CLANG_TABLEGEN'] = '%s/%s/bin/clang-tblgen' % (os.getcwd(), self.build_llvm_x86_dir)
        cmake.definitions['CLANG_TABLEGEN_EXE'] = cmake.definitions['CLANG_TABLEGEN']
        flags = ' -target arm64-apple-macos10.11.0'
        cmake.definitions['CMAKE_C_FLAGS'] = flags
        cmake.definitions['CMAKE_CXX_FLAGS'] += flags
        tools.mkdir(self.build_llvm_arm_dir)
        with tools.chdir(self.build_llvm_arm_dir):
            cmake.configure(source_dir='../%s' % self.llvm_source_dir, build_dir='.')
            cmake.build(target='libtapi')


        self.output.info("=== Merge x86_64 + arm64 libtapi ===")
        tools.mkdir(self.install_universal_dir)
        with tools.chdir(self.install_universal_dir):
            tools.mkdir('lib')
            with tools.chdir('lib'):
                self.run('lipo -create ../../%s/lib/libtapi.dylib ../../%s/lib/libtapi.dylib -output libtapi.dylib' % (self.build_llvm_x86_dir, self.build_llvm_arm_dir))
                self.run('codesign --sign - libtapi.dylib')


        self.output.info("=== Build ld for both x86_64 + arm64 ===")
        with tools.chdir(self.ld64_source_dir):
            tools.replace_in_file('ld64.xcodeproj/project.pbxproj',
                                  '"-ltapi",',
                                  '"%s/../%s/lib/libtapi.dylib",' % (os.getcwd(), self.install_universal_dir))
            self.run('RC_SUPPORTED_ARCHS="x86_64 arm64" xcodebuild ARCHS="x86_64 arm64" -target ld HEADER_SEARCH_PATHS="../%s/include ../%s/include ../%s/include ../%s/projects/tapi-%s/include src/ld"' % (self.dyld_source_dir, self.llvm_source_dir, self.tapi_source_dir, self.build_llvm_x86_dir, self.tapi_version))


    def package(self):
        self.copy('ld', src='%s/build/Release-assert' % self.ld64_source_dir, dst='bin')
        self.copy('libtapi.dylib', src='%s/lib' % self.install_universal_dir, dst='lib')
        self.copy('%s.txt' % self.name, src=self.ld64_source_dir, dst='license')
