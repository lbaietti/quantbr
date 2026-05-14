cmake_minimum_required(VERSION 3.20)
project(quantbr_feed VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type")

# Optimization flags for HFT
add_compile_options(-O3 -march=native -mtune=native -funroll-loops -ffast-math)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

add_executable(quantbr_feed
    src/main.cpp
    src/umdf_parser.cpp
    src/order_book.cpp
    src/step_client.cpp
    src/zmq_publisher.cpp
    src/session_manager.cpp
)

target_include_directories(quantbr_feed PRIVATE include ${ZMQ_INCLUDE_DIRS})
target_link_libraries(quantbr_feed PRIVATE ${ZMQ_LIBRARIES} pthread)
target_compile_options(quantbr_feed PRIVATE ${ZMQ_CFLAGS_OTHER})
