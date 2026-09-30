# Embench on a Pico, with pico-turbo owning the clock.
#
# One benchmark per build, chosen at configure time:
#
#   cmake -S . -B build -DPICO_BOARD=weact_rp2350a \
#         -DEMBENCH_BENCHMARK=statemate -DPICO_TURBO_DIR=<pico-turbo>
#   cmake --build build -j
#
# The clock, the core voltage and the flash divider are pico-turbo's, exactly as in
# the coremark repository: this port's job is to run one Embench benchmark and report
# what the chip was actually doing while it ran.

cmake_minimum_required(VERSION 3.13)

# A board name of our own, so that a board whose ceiling has been measured does not
# share `pico2` with clones that have different flash parts and supplies.  The SDK
# looks for <PICO_BOARD>.h in PICO_BOARD_HEADER_DIRS first and appends its own
# boards/include afterwards, so a name it has never heard of resolves here while
# pico, pico_w and pico2 are untouched.  Set before project(), because the board is
# resolved during it.
set(_EMBENCH_BOARDS "${CMAKE_CURRENT_LIST_DIR}/boards")
if (DEFINED ENV{PICO_BOARD_HEADER_DIRS})
    set(_EMBENCH_BOARDS "${_EMBENCH_BOARDS};$ENV{PICO_BOARD_HEADER_DIRS}")
endif()
set(ENV{PICO_BOARD_HEADER_DIRS} "${_EMBENCH_BOARDS}")

include(pico_sdk_import.cmake)

project(embench-pico C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if (PICO_SDK_VERSION_STRING VERSION_LESS "2.0.0")
    message(FATAL_ERROR "Raspberry Pi Pico SDK version 2.0.0 (or later) required. Your version is ${PICO_SDK_VERSION_STRING}")
endif()

# The SDK drops every character written while no host has the port open, and a run
# whose reader is a second late prints nothing at all.  This makes each boot wait for
# the port instead; the wait is before the timed region, so it does not enter a
# result.  (Same reason and same value as the coremark port.)
if (NOT DEFINED PICO_STDIO_USB_CONNECT_WAIT_TIMEOUT_MS)
    set(PICO_STDIO_USB_CONNECT_WAIT_TIMEOUT_MS 20000)
endif()

pico_sdk_init()

# --- the clock: pico-turbo ---------------------------------------------------
if(NOT DEFINED PICO_TURBO_DIR)
    set(PICO_TURBO_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../pico-turbo" CACHE PATH
        "where the pico-turbo checkout lives")
endif()
if(NOT EXISTS "${PICO_TURBO_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "pico-turbo not found at ${PICO_TURBO_DIR}: pass -DPICO_TURBO_DIR=<path>")
endif()
add_subdirectory(${PICO_TURBO_DIR} ${CMAKE_BINARY_DIR}/pico_turbo)

# --- which benchmark ---------------------------------------------------------
set(EMBENCH_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../..")
if(NOT DEFINED EMBENCH_BENCHMARK)
    file(GLOB _benches RELATIVE "${EMBENCH_ROOT}/src" "${EMBENCH_ROOT}/src/*")
    message(FATAL_ERROR "pass -DEMBENCH_BENCHMARK=<name>.  Available: ${_benches}")
endif()
if(NOT IS_DIRECTORY "${EMBENCH_ROOT}/src/${EMBENCH_BENCHMARK}")
    message(FATAL_ERROR "no such benchmark: ${EMBENCH_BENCHMARK}")
endif()

# WARMUP_HEAT and GLOBAL_SCALE_FACTOR are the scons build's variables of the same
# names; their defaults are the ones sconstruct.py declares.
if(NOT DEFINED WARMUP_HEAT)
    set(WARMUP_HEAT 1)
endif()
if(NOT DEFINED GLOBAL_SCALE_FACTOR)
    set(GLOBAL_SCALE_FACTOR 1)
endif()

file(GLOB BENCH_SOURCES "${EMBENCH_ROOT}/src/${EMBENCH_BENCHMARK}/*.c")

add_executable(${PROJECT_NAME}
    ${EMBENCH_ROOT}/support/main.c
    ${EMBENCH_ROOT}/support/beebsc.c
    ${BENCH_SOURCES}
    ${CMAKE_CURRENT_LIST_DIR}/boardsupport.c
)

# The harness's own main() calls verify_benchmark() and returns its result as the
# exit code, which the reference runner reads over GDB.  This bench does not use a
# debugger during a run -- a halt costs the round its timing (see the coremark
# repository's AGENTS.md) -- so the port wraps the call and prints the verdict
# instead.  Wrapping rather than copying support/main.c keeps that file the single
# source of the harness sequence, which is what makes a number here comparable with
# Embench's published ones.
target_link_options(${PROJECT_NAME} PRIVATE "-Wl,--wrap=verify_benchmark")

target_include_directories(${PROJECT_NAME} PRIVATE
    ${EMBENCH_ROOT}/support
    ${CMAKE_CURRENT_LIST_DIR}
    ${EMBENCH_ROOT}/src/${EMBENCH_BENCHMARK}
)
target_compile_definitions(${PROJECT_NAME} PRIVATE
    WARMUP_HEAT=${WARMUP_HEAT}
    GLOBAL_SCALE_FACTOR=${GLOBAL_SCALE_FACTOR}
    EMBENCH_BENCHMARK_NAME="${EMBENCH_BENCHMARK}"
)

target_link_libraries(${PROJECT_NAME}
    pico_turbo
    pico_stdlib
)

if(NOT DEFINED PICO_TURBO_BINARY_TYPE)
    set(PICO_TURBO_BINARY_TYPE default)
endif()
pico_set_binary_type(${PROJECT_NAME} ${PICO_TURBO_BINARY_TYPE})
pico_enable_stdio_usb(${PROJECT_NAME} 1)
pico_enable_stdio_uart(${PROJECT_NAME} 1)
pico_add_extra_outputs(${PROJECT_NAME})
