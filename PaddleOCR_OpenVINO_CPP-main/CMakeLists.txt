cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 17)

project(PaddleOCR_OpenVINO_CPP)

find_package(OpenCV REQUIRED)
find_package(OpenVINO REQUIRED)

set(GFLAGS_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/thirdParty/gflags" CACHE PATH "gflags include dir")
set(DIRENT_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/thirdParty/dirent" CACHE PATH "dirent include dir")

include_directories(
    ./
    ${OpenCV_INCLUDE_DIR}
    ${GFLAGS_INCLUDE_DIR}
    ${DIRENT_INCLUDE_DIR}
)

if(OpenVINO_INCLUDE_DIRS)
    message(STATUS "OpenVINO includes: ${OpenVINO_INCLUDE_DIRS}")
else()
    message(STATUS "OpenVINO include dir not set by cmake, using default")
    include_directories("C:/Program Files (x86)/Intel/openvino/runtime/include")
endif()

aux_source_directory(src SRC)
add_executable(reader main.cpp ${SRC})
target_link_libraries(reader PRIVATE openvino::runtime ${OpenCV_LIBS})
