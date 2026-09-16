"""Standalone hardware self-test.

Streams the local sos_test.mp3 straight to the Pico over SPI, bypassing
wifi/network/backend entirely. Useful to check whether the ESP32 -> Pico ->
DAC audio path itself works when normal ringing does not.

The file plays the Morse "SOS" pattern three times, once each at 300Hz,
1000Hz and 7000Hz.

Run manually over the REPL. Requires sos_test.mp3 uploaded next to this file
on the ESP32's filesystem.
"""
import time
from player import PlayerController

CHUNK = 512  # must match the Pico's spi_read_blocking() chunk size

# 100 kHz (mode 3) -- the proven-clean decode config (frames climb, nosync=0). At
# 1 MHz the inter-write gaps desync the byte stream (err spikes); revisit later.
controller = PlayerController(socket_host=None, socket_port=None, baudrate=100000)

# --- TEMPORARY DIAGNOSTIC INSTRUMENTATION ---
# Counts whether the READY line is ever actually seen low (i.e. whether the
# back-pressure handshake ever really blocks us), and times the transfer.
total_chunks = 0
waited_chunks = 0
wait_ticks = 0
t0 = time.ticks_ms()

# Hold CS LOW for the ENTIRE stream -- do NOT toggle it per chunk. Per-chunk CS
# framing is fatally fragile: each 512B window is only ~4ms wide, so any ms-scale
# stall (GC, USB flow control) on either side lands inside a window and corrupts
# or drops it. With CS held low continuously, those stalls become harmless
# idle-clock gaps on byte boundaries; the Pico drains a byte stream into its ring
# buffer and the READY line paces us so the ring never overflows.
controller.cs.value(0)
try:
    with open("sos_test.mp3", "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            if len(chunk) < CHUNK:
                # Pad the final short chunk; trailing zeros are not a valid MP3
                # frame sync, so the Pico just ignores them.
                chunk = chunk + b'\x00' * (CHUNK - len(chunk))

            if not controller.ready.value():
                waited_chunks += 1
            while not controller.ready.value():
                wait_ticks += 1
                time.sleep_ms(1)

            # CS stays low across the whole stream -- only write() clocks data.
            controller.spi.write(chunk)
            total_chunks += 1

            # NOTE: do NOT print inside this loop -- a blocking print to USB-CDC
            # (and the GC it can trigger) stalls the stream. Print only at the end.
finally:
    controller.cs.value(1)  # release CS once the whole stream is sent

print("sos_test: done. total_chunks=%d waited_chunks=%d wait_ticks=%d elapsed_ms=%d" % (
    total_chunks, waited_chunks, wait_ticks, time.ticks_diff(time.ticks_ms(), t0)))
