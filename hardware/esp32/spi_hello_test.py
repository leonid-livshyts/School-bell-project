"""Minimal SPI test: sends one fixed long text message to the Pico and
prints every step. No MP3, no file, no back-pressure loop beyond a single
wait -- just proves raw bytes can travel ESP32 -> Pico over the wiring.

Run this together with spi_test.cpp flashed onto the Pico (a diagnostic-only
firmware, separate from the real player firmware).
"""
import time
from machine import Pin, SPI

# Long on purpose: at 1 MHz this is a ~32ms-long SPI transaction, easy to
# find and trigger on an oscilloscope. Must match MSG_LEN in spi_test.cpp.
MSG_LEN = 4096
# All-0xFF on purpose: MSB-first SPI means every bit of every byte is 1, so
# MOSI is driven continuously HIGH for the whole transaction -- a clean,
# non-toggling level to compare against SCK's amplitude, no ASCII-text bias
# (printable ASCII bytes are all < 0x80, so their top bit is always 0).
msg = b'\xa8' * MSG_LEN

# TEST: mode 3 AND 10x slower clock (100 kHz) to check whether the Pico slave
# catches more bytes at a slower rate -- a rate/timing-margin test, not a phase
# test. If received climbs at 100kHz, the 1MHz clock was too fast/marginal for
# the slave to sample; if it stays at 1, rate is not the variable.
spi = SPI(2, baudrate=100_000, polarity=1, phase=1,
          sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT, value=1)  # ESP32-side CS output pin
ready = Pin(35, Pin.IN)

# print("ready.value() right now:", ready.value())

# print("waiting for ready to go high...")
waited_ms = 0
while not ready.value():
    time.sleep_ms(1)
    waited_ms += 1
    if waited_ms % 1000 == 0:
        print("... still waiting, %dms so far" % waited_ms)
    if waited_ms > 5000:
        print("gave up after 5s: ready never went high")
        raise SystemExit

# print("ready seen high after %dms, sending..." % waited_ms)

cs.value(0)
spi.write(msg)
cs.value(1)

# print("sent:", msg)
print("done")
