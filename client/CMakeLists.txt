cmake_minimum_required(VERSION 3.1)

project(pmp_client)

set (CMAKE_CXX_STANDARD 11)

if( NOT CMAKE_CONFIGURATION_TYPES )
    # Build Debug by default
    if( NOT CMAKE_BUILD_TYPE )
        if(MULE_TARGET_BUILD)
            set(DEFAULT_BUILD_TYPE "Release")
        else()
            set(DEFAULT_BUILD_TYPE "Debug")
        endif()
        message(STATUS "CMAKE_BUILD_TYPE not set - default to ${DEFAULT_BUILD_TYPE}")
        set(CMAKE_BUILD_TYPE ${DEFAULT_BUILD_TYPE} CACHE
            STRING "Choose the type of build, options are: Debug Release RelWithDebInfo MinSizeRel."
            FORCE)
    endif()
else()
    # Using a multi-configuration generator eg MSVC or Xcode
    # that uses CMAKE_CONFIGURATION_TYPES and not CMAKE_BUILD_TYPE
endif()

set (CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/CMakeModules")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Weffc++ -Wall")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fstack-protector-strong ")

find_package(Qt5Widgets REQUIRED)
find_package(Qt5UiTools REQUIRED)

set(CMAKE_INCLUDE_CURRENT_DIR ON)
set(CMAKE_AUTOMOC ON)

qt5_add_resources(
    RESOURCES resources.qrc
)

file(GLOB PROJECT_FILES
    ../readme.md
    ../todo.md
    errors.h
    configuration.h
    pmpc_mainwindow.cpp
    pmpc_mainwindow.h
    pmpc_client.h
    pmpc_client.cpp
    pmpc_main.cpp
)
add_subdirectory(submodule/pal)

set(ZMQ_BUILD_TESTS OFF)
add_subdirectory(submodule/libzmq)

if(ANDROID)
    add_library(pmp_client SHARED
        ${PROJECT_FILES}
        ${RESOURCES}
    )
    target_link_libraries(pmp_client
        libzmq-static
        log
    )
    set_target_properties(pmp_client PROPERTIES
        VERSION 0.1.0
        SOVERSION 1
    )
    include(submodule/qt-android-cmake/AddQtAndroidApk.cmake)
    add_qt_android_apk(pmp_client_android pmp_client NAME "party music player")
else()
    add_executable(pmp_client
        ${PROJECT_FILES}
        ${RESOURCES}
    )
    target_link_libraries(pmp_client
        libzmq
    )
endif()

target_include_directories(pmp_client
    SYSTEM PRIVATE
        submodule/cppzmq
        submodule/libzmq/include
)

target_link_libraries(pmp_client
    Qt5::Widgets
    Qt5::UiTools
    pal_qt5_s
)
