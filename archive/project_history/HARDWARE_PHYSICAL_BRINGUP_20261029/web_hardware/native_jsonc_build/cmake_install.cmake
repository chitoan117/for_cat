# Install script for directory: D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_INSTALL_DEFAULT_DIRECTORY_PERMISSIONS)
  set(CMAKE_INSTALL_DEFAULT_DIRECTORY_PERMISSIONS "OWNER_READ;OWNER_WRITE;OWNER_EXECUTE;GROUP_READ;GROUP_EXECUTE;WORLD_READ;WORLD_EXECUTE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "CMAKE_OBJDUMP-NOTFOUND")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/libjson-c.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c/json-c-targets.cmake")
    file(DIFFERENT _cmake_export_file_changed FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c/json-c-targets.cmake"
         "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/CMakeFiles/Export/c72427da9e5c73ebf6c111c2977a0759/json-c-targets.cmake")
    if(_cmake_export_file_changed)
      file(GLOB _cmake_old_config_files "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c/json-c-targets-*.cmake")
      if(_cmake_old_config_files)
        string(REPLACE ";" ", " _cmake_old_config_files_text "${_cmake_old_config_files}")
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c/json-c-targets.cmake\" will be replaced.  Removing files [${_cmake_old_config_files_text}].")
        unset(_cmake_old_config_files_text)
        file(REMOVE ${_cmake_old_config_files})
      endif()
      unset(_cmake_old_config_files)
    endif()
    unset(_cmake_export_file_changed)
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c" TYPE FILE FILES "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/CMakeFiles/Export/c72427da9e5c73ebf6c111c2977a0759/json-c-targets.cmake")
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c" TYPE FILE FILES "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/CMakeFiles/Export/c72427da9e5c73ebf6c111c2977a0759/json-c-targets-release.cmake")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/json-c" TYPE FILE FILES "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/json-c-config.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/json-c.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_config.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/arraylist.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/debug.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_c_version.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_inttypes.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_object.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_object_iterator.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_tokener.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_types.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_util.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_visit.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/linkhash.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/printbuf.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_pointer.h;D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c/json_patch.h")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install/include/json-c" TYPE FILE FILES
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/json_config.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/json.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/arraylist.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/debug.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_c_version.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_inttypes.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_object.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_object_iterator.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_tokener.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_types.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_util.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_visit.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/linkhash.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/printbuf.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_pointer.h"
    "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/json_c_source/json_patch.h"
    )
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/doc/cmake_install.cmake")

endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "D:/for_cat/HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_build/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
