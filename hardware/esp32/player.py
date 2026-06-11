import socket
import time
import gc
import _thread
from machine import Pin, SPI


# Always use this manual quote() implementation.
# We do NOT import urllib.parse.quote: on some MicroPython builds that module
# IS importable, but its quote() calls str.isalnum(), which MicroPython's str
# does not implement -> AttributeError. This version avoids isalnum entirely.
def quote(s, safe=''):
    """Simple URL encoding for MicroPython.
    Supports str and bytes; avoids using isalnum which may be missing.
    """
    if isinstance(s, bytes):
        try:
            s = s.decode('utf-8')
        except Exception:
            s = s.decode('latin1')
    result = []
    for char in s:
        # Manual alphanumeric check
        if ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or (char in safe):
            result.append(char)
        else:
            result.append('%{:02X}'.format(ord(char)))
    return ''.join(result)


class PlayerException(Exception):
    pass


# Socket timeouts (in seconds) for talking to the MP3 streaming server.
CONNECT_TIMEOUT = 10  # TCP connect step
HEADER_TIMEOUT = 15   # waiting for the server to find the file and start sending
STREAM_TIMEOUT = 8    # ongoing streaming after the first bytes arrived

# recv() timeouts surface as OSError. The errno depends on the MicroPython port:
#   11  = EAGAIN
#   110 = ETIMEDOUT on CPython / Linux builds
#   116 = ETIMEDOUT on the ESP32 (lwIP) build  <-- our hardware
TIMEOUT_ERRNOS = (11, 110, 116)

# Bytes per SPI transfer. Must match the Pico's spi_read_blocking() chunk size.
CHUNK = 512


class PlayerSession:
    """One playback. Streams MP3 bytes from the server straight to the Pico
    over SPI; the Pico decodes and drives the I2S DAC.

    Playback runs in a background thread so the caller (the main loop) keeps
    running and can stop()/interrupt it at any time.
    """

    def __init__(self, player, socket_host, socket_port, logger=None):
        self.player = player
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.logger = logger
        self.sock = None
        self._first = None
        # Idle to begin with: _running False so stop() is a safe no-op.
        self._stop = True
        self._running = False

    def _log(self, msg):
        if self.logger:
            self.logger(msg)

    def _send_chunk(self, chunk):
        """Send exactly CHUNK bytes to the Pico, gated by its READY line."""
        if len(chunk) < CHUNK:
            # Pad the final short chunk. Trailing zeros are not a valid MP3
            # frame sync, so the Pico just ignores them.
            chunk = bytes(chunk) + b'\x00' * (CHUNK - len(chunk))

        ready = self.player.ready
        # Wait for back-pressure to clear (Pico ring buffer has room).
        while not ready.value():
            if self._stop:
                return
            time.sleep_ms(1)

        self.player.cs.value(0)
        self.player.spi.write(chunk)
        self.player.cs.value(1)

    def _pump(self):
        """Background loop: read MP3 bytes from the socket, forward to Pico."""
        try:
            if self._first:
                self._send_chunk(self._first)
                self._first = None

            while not self._stop:
                try:
                    chunk = self.sock.recv(CHUNK)
                except OSError as e:
                    errno = e.args[0] if e.args else None
                    if errno in TIMEOUT_ERRNOS:
                        continue  # re-check _stop and retry
                    raise
                if not chunk:
                    break  # server closed the connection -> end of file
                self._send_chunk(chunk)
        except Exception as e:
            self._log("ERROR: playback pump failed: %s" % e)
        finally:
            try:
                self.sock.close()
            except Exception:
                pass
            self._running = False

    def play(self, sound):
        """Request a sound from the server and start streaming it to the Pico.

        Returns immediately; playback continues in the background until the
        file ends or stop() is called.
        """
        # Never run two playbacks at once (the ESP32 has a single worker core).
        self.stop()

        gc.collect()
        sock = None
        try:
            sock = socket.socket()
            sock.settimeout(CONNECT_TIMEOUT)
            sock.connect((self.socket_host, self.socket_port))

            if hasattr(socket, "IPPROTO_TCP") and hasattr(socket, "TCP_NODELAY"):
                try:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except Exception:
                    pass

            # Request protocol: 1 byte length + URL-encoded "<type><name>".
            encoded = quote(sound, safe='_-.')
            req = encoded.encode()
            if len(req) > 255:
                raise PlayerException("Sound name too long: %d bytes (max 255)" % len(req))

            sock.settimeout(HEADER_TIMEOUT)
            sock.sendall(bytes([len(req)]) + req)

            # Read the first bytes synchronously so file-not-found / no-data
            # errors are surfaced to the caller instead of dying in the thread.
            first = sock.recv(CHUNK)
            if not first:
                raise PlayerException("No data from server for '%s' (missing file?)" % sound)

            sock.settimeout(STREAM_TIMEOUT)
            self.sock = sock
            self._first = first
            self._stop = False
            self._running = True
            _thread.start_new_thread(self._pump, ())
            self._log("DEBUG: streaming '%s' to Pico" % sound)

        except PlayerException:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            raise
        except Exception as e:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            raise PlayerException("Cannot play '%s': %s: %s" % (sound, type(e).__name__, e))

    def stop(self):
        """Stop playback: signal the worker, flush the Pico, close the socket."""
        if not self._running:
            return
        self._stop = True

        # Unblock a recv() that may be waiting for data.
        try:
            self.sock.close()
        except Exception:
            pass

        # Pulse the STOP line so the Pico drops audio already buffered on its
        # side and goes silent immediately.
        self.player.stop_pin.value(1)
        time.sleep_ms(10)
        self.player.stop_pin.value(0)

        # Give the worker a moment to exit before the next playback starts.
        deadline = time.ticks_add(time.ticks_ms(), 300)
        while self._running and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            time.sleep_ms(2)


class PlayerController:
    @staticmethod
    def play_stop():
        print("stopped")

    def __init__(self, socket_host, socket_port,
                 spi_id=1, sck_pin=32, mosi_pin=33, miso_pin=25,
                 cs_pin=26, ready_pin=35, stop_pin=27,
                 baudrate=4_000_000, on_finish=play_stop, logger=None):
        # SPI master to the Pico. miso is unused (one-way) but required by the
        # constructor on the ESP32.
        self.spi = SPI(spi_id, baudrate=baudrate, polarity=0, phase=0,
                       sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))
        self.cs = Pin(cs_pin, Pin.OUT, value=1)          # active low
        self.ready = Pin(ready_pin, Pin.IN)              # high = Pico has room
        self.stop_pin = Pin(stop_pin, Pin.OUT, value=0)  # high = stop playback

        self.socket_host = socket_host
        self.socket_port = socket_port
        self.logger = logger

    def get_session(self):
        return PlayerSession(self, self.socket_host, self.socket_port, self.logger)
