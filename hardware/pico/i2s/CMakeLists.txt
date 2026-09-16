# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(i2s C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable. Default name is the project name, version 0.1

# Helix fixed-point MP3 decoder sources (vendored under helix/)
file(GLOB HELIX_SRCS ${CMAKE_CURRENT_LIST_DIR}/helix/*.c)

add_executable(i2s main.cpp ${HELIX_SRCS})

pico_set_program_name(i2s "i2s")
pico_set_program_version(i2s "0.1")

# Generate PIO header from i2s.pio
pico_generate_pio_header(i2s ${CMAKE_CURRENT_LIST_DIR}/i2s.pio)

# Modify the below lines to enable/disable output over UART/USB
pico_enable_stdio_uart(i2s 1)
pico_enable_stdio_usb(i2s 1)

# Add the standard library to the build
target_link_libraries(i2s
        pico_stdlib)

# Add the standard include files to the build
target_include_directories(i2s PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/helix
)

# Add any user requested libraries
target_link_libraries(i2s 
        hardware_i2c
        hardware_pio
        hardware_spi
        hardware_clocks
        hardware_dma
        pico_multicore
        )

pico_add_extra_outputs(i2s)

# --- Diagnostic-only target: minimal SPI-slave test, unrelated to the real
# player firmware above. See spi_test.cpp.
add_executable(spi_test spi_test.cpp)
pico_set_program_name(spi_test "spi_test")
pico_set_program_version(spi_test "0.1")
pico_enable_stdio_uart(spi_test 1)
pico_enable_stdio_usb(spi_test 1)
target_link_libraries(spi_test pico_stdlib hardware_spi)
pico_add_extra_outputs(spi_test)

# --- Diagnostic-only target: minimal serial-only test, no SPI/I2S at all.
# See serial_test.cpp.
add_executable(serial_test serial_test.cpp)
pico_set_program_name(serial_test "serial_test")
pico_set_program_version(serial_test "0.1")
pico_enable_stdio_uart(serial_test 1)
pico_enable_stdio_usb(serial_test 1)
target_link_libraries(serial_test pico_stdlib)
pico_add_extra_outputs(serial_test)

# --- Diagnostic-only target: standalone I2S beep. No SPI/MP3 -- drives the
# PCM5102A directly to isolate the audio-output path. See beep_test.cpp.
add_executable(beep_test beep_test.cpp)
pico_set_program_name(beep_test "beep_test")
pico_set_program_version(beep_test "0.1")
pico_generate_pio_header(beep_test ${CMAKE_CURRENT_LIST_DIR}/i2s.pio)
pico_enable_stdio_uart(beep_test 1)
pico_enable_stdio_usb(beep_test 1)
target_link_libraries(beep_test pico_stdlib hardware_pio hardware_clocks)
pico_add_extra_outputs(beep_test)

# --- Diagnostic-only target: raw bus-edge logger. Reads GP16/17/18 as plain
# GPIO inputs and logs every SCK/MOSI/CS transition during a CS window, with no
# SPI peripheral involved. See spi_probe.cpp.
add_executable(spi_probe spi_probe.cpp)
pico_set_program_name(spi_probe "spi_probe")
pico_set_program_version(spi_probe "0.1")
pico_enable_stdio_uart(spi_probe 1)
pico_enable_stdio_usb(spi_probe 1)
target_link_libraries(spi_probe pico_stdlib)
pico_add_extra_outputs(spi_probe)

# --- Diagnostic-only target: raw GPIO-level test, no SPI peripheral. Reads
# GP16/18/19 as plain inputs. See gpio_level_test.cpp.
add_executable(gpio_level_test gpio_level_test.cpp)
pico_set_program_name(gpio_level_test "gpio_level_test")
pico_set_program_version(gpio_level_test "0.1")
pico_enable_stdio_uart(gpio_level_test 1)
pico_enable_stdio_usb(gpio_level_test 1)
target_link_libraries(gpio_level_test pico_stdlib)
pico_add_extra_outputs(gpio_level_test)

