cmake_minimum_required(VERSION 3.12)

project(PerfectSelect VERSION 1.1)

option(BUILD_BACKEND "Skip building C++ backend" ON)
set(BLENDER_TAGS "" CACHE STRING "Blender release tags")
set(BLENDER_SOURCES_DIR "../blender_sources" CACHE FILEPATH "Blender sources container")

set(PerfectSelect_PACKAGE_DIR ${CMAKE_BINARY_DIR}/perfect_select)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PerfectSelect_PACKAGE_DIR}/backend)

if(BUILD_BACKEND AND NOT BLENDER_TAGS)
  message(FATAL_ERROR "BLENDER_TAGS is not set! Please enter branch tag(s) to checkout (semicolon separated)")
endif()

if (BUILD_BACKEND)
  if(APPLE)
    set(PLATFORM_NAME "darwin")
    set(PLATFORM_LIB "darwin")
  elseif(UNIX AND NOT APPLE)
    set(PLATFORM_NAME "linux")
    set(PLATFORM_LIB "linux_centos7_x86_64")
  else()
    set(PLATFORM_NAME "win32")
    set(PLATFORM_LIB "win64_vc15")
  endif()

  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fpermissive")

  foreach(BLENDER_TAG ${BLENDER_TAGS})
    message(STATUS "Creating target for Blender ${BLENDER_TAG}")
    string(REPLACE "." "_" CURRENT_TARGET_NAME backend_module_${BLENDER_TAG}_${PLATFORM_NAME})

    add_library(${CURRENT_TARGET_NAME} SHARED backend/module.cpp backend/select.cpp)
    set_target_properties(${CURRENT_TARGET_NAME} PROPERTIES PREFIX "")
    target_compile_definitions(${CURRENT_TARGET_NAME} PUBLIC PERFECT_SELECT_MODULE_NAME=${CURRENT_TARGET_NAME} )

    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/blenkernel)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/blenlib)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/makesdna)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/makesrna)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/bmesh)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/python)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/depsgraph)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/windowmanager)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/source/blender/editors/include)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/intern)
    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/blender/intern/guardedalloc)

    target_include_directories(${CURRENT_TARGET_NAME} PUBLIC ${BLENDER_SOURCES_DIR}/${BLENDER_TAG}/lib/${PLATFORM_LIB}/python/include/python3.7m)
  endforeach()
endif()
add_custom_target(scripts_and_datafiles ALL)
add_custom_command(TARGET scripts_and_datafiles POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/__init__.py ${PerfectSelect_PACKAGE_DIR}/__init__.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/operators.py ${PerfectSelect_PACKAGE_DIR}/operators.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/previews.py ${PerfectSelect_PACKAGE_DIR}/previews.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/properties.py ${PerfectSelect_PACKAGE_DIR}/properties.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/user_interface.py ${PerfectSelect_PACKAGE_DIR}/user_interface.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/backend/__init__.py ${PerfectSelect_PACKAGE_DIR}/backend/__init__.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/backend/select.py ${PerfectSelect_PACKAGE_DIR}/backend/select.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/scripts/backend/utils.py ${PerfectSelect_PACKAGE_DIR}/backend/utils.py
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/datafiles/ops.perfect_select.perfect_select.dat ${PerfectSelect_PACKAGE_DIR}/datafiles/ops.perfect_select.perfect_select.dat
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/shaders/preview.frag ${PerfectSelect_PACKAGE_DIR}/shaders/preview.frag
        COMMAND ${CMAKE_COMMAND} -E copy ${PerfectSelect_SOURCE_DIR}/shaders/preview.vert ${PerfectSelect_PACKAGE_DIR}/shaders/preview.vert
        )
