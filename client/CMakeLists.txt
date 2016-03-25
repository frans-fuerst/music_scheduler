cmake_minimum_required(VERSION 3.1)

project(rrplayer)

set (CMAKE_CXX_STANDARD 11)

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
    ../Readme.md
    ../Development.md
    errors.h
    rrplayer_mainwindow.cpp
    rrplayer_mainwindow.h
    rrplayer_client.h
    rrplayer_client.cpp
    rrplayer_main.cpp
)
add_subdirectory(submodule/pal)

set(ZMQ_BUILD_TESTS OFF)
add_subdirectory(submodule/libzmq)

if(ANDROID)
    add_library(rrplayer SHARED
        ${PROJECT_FILES}
        ${RESOURCES}
    )
    target_link_libraries(rrplayer
        libzmq-static
        log
    )
    set_target_properties(rrplayer PROPERTIES
        VERSION 0.1.0
        SOVERSION 1
    )
    include(submodule/qt-android-cmake/AddQtAndroidApk.cmake)
    add_qt_android_apk(rrplayer_android rrplayer NAME rrplayer)
else()
    add_executable(rrplayer
        ${PROJECT_FILES}
        ${RESOURCES}
    )
    target_link_libraries(rrplayer
        libzmq
    )
endif()

target_include_directories(rrplayer
    SYSTEM PRIVATE
        submodule/cppzmq
        submodule/libzmq/include
)

target_link_libraries(rrplayer
    Qt5::Widgets
    Qt5::UiTools
    pal_qt5_s
)
