"""Ground-truth electrical test, ESP32 side. NO SPI -- drives the data (MOSI)
and clock (SCK) wires high/low with plain GPIO on a slow 2s cycle so the
level can be read with a meter/scope and by gpio_level_test.cpp on the Pico.

Wiring for this test (same physical wires as the SPI link):
  ESP32 GP23 (MOSI wire) -> Pico GP16
  ESP32 GP18 (SCK wire)  -> Pico GP18
Watch the Pico's serial output and measure the wire voltage at the same time.
"""
import time
from machine import Pin

mosi = Pin(23, Pin.OUT)
sck = Pin(18, Pin.OUT)

level = 1
while True:
    mosi.value(level)
    sck.value(level)
    print("driving MOSI(GP23) and SCK(GP18) =", level)
    level ^= 1
    time.sleep(2)
