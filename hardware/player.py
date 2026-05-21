from wavplayer import WavPlayer
import socket
import time
import gc
from time import sleep

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


# Socket timeouts (in seconds) for talking to the WAV streaming server.
CONNECT_TIMEOUT = 10  # TCP connect step
HEADER_TIMEOUT = 15   # waiting for the server to find the file and send the WAV header
STREAM_TIMEOUT = 8    # ongoing audio streaming after the header arrived

# recv() timeouts surface as OSError. The errno depends on the MicroPython port:
#   11  = EAGAIN
#   110 = ETIMEDOUT on CPython / Linux builds
#   116 = ETIMEDOUT on the ESP32 (lwIP) build  <-- our hardware
TIMEOUT_ERRNOS = (11, 110, 116)


class SocketStreamWrapper:
    """Wrapper to make a socket behave like a file object for WAV streaming.
    
    Implements buffered reading to ensure read(n) returns exactly n bytes
    or raises an error, matching file object behavior.
    """
    def __init__(self, sock, logger=None):
        self.sock = sock
        self.buf = b""
        self.closed = False
        self.logger = logger
        self.position = 0
        self.bytes_received = 0
        
    def read(self, n):
        """Read exactly n bytes from socket, buffering as needed."""
        if self.closed:
            raise OSError("Socket is closed")
        
        # Use existing buffer first
        while len(self.buf) < n:
            try:
                # Use larger recv buffer (16KB) to reduce socket call overhead
                chunk = self.sock.recv(16384)
                if not chunk:
                    # Connection closed or no more data
                    if len(self.buf) == 0:
                        if self.bytes_received == 0 and self.logger:
                            self.logger("ERROR: Server sent no data - file may not exist on server")
                        return b""
                    # Return what we have
                    result = self.buf[:n]
                    self.buf = self.buf[n:]
                    self.position += len(result)
                    self.bytes_received += len(result)
                    if self.logger:
                        self.logger(f"DEBUG: EOF reached at {self.bytes_received} bytes total, returning {len(result)} bytes")
                    return result
                self.bytes_received += len(chunk)
                self.buf += chunk
                if self.logger and self.bytes_received % 65536 == 0:
                    self.logger(f"DEBUG: Socket read progress: {self.bytes_received} bytes")
            except OSError as e:
                # MicroPython has no socket.timeout class; recv() timeouts surface
                # as OSError. See TIMEOUT_ERRNOS above. Anything else is a real
                # socket failure and should propagate.
                errno = e.args[0] if e.args else None
                if errno not in TIMEOUT_ERRNOS:
                    if self.logger:
                        self.logger(f"ERROR: Fatal socket error (errno {errno}): {e}")
                    raise
                if self.logger:
                    self.logger(f"DEBUG: recv() timed out (errno {errno}), buffered={len(self.buf)}, total received={self.bytes_received}")
                # On timeout, return what we have buffered
                # This is important during I2S playback to avoid blocking the callback
                if len(self.buf) > 0:
                    result = self.buf[:n]
                    self.buf = self.buf[n:]
                    self.position += len(result)
                    self.bytes_received += len(result)
                    if self.logger:
                        self.logger(f"DEBUG: Socket timeout, returning {len(result)} bytes from buffer")
                    return result
                # No buffered data and timeout - this is only an error on first read
                if self.bytes_received == 0:
                    if self.logger:
                        self.logger(f"ERROR: Socket timeout on first read - no data received from server")
                    raise
                # Otherwise return empty (will signal EOF to WAV player)
                if self.logger:
                    self.logger(f"DEBUG: Socket timeout at {self.bytes_received} bytes, returning empty (EOF)")
                return b""
        
        # We have enough buffered
        result = self.buf[:n]
        self.buf = self.buf[n:]
        self.position += len(result)
        self.bytes_received += len(result)
        return result
    
    def readinto(self, b):
        """Read bytes directly into the provided buffer."""
        data = self.read(len(b))
        if not data:
            return 0
        b[:len(data)] = data
        return len(data)
    
    def seek(self, pos, whence=0):
        """Forward-only seek support for socket streams."""
        if whence != 0:
            raise OSError("seek only supports absolute positions")
        if pos < self.position:
            raise OSError("cannot seek backwards on socket stream")
        if pos == self.position:
            return self.position
        to_skip = pos - self.position
        while to_skip > 0:
            chunk = self.read(min(to_skip, 4096))
            if not chunk:
                raise OSError("cannot seek past end of socket stream")
            to_skip -= len(chunk)
        return self.position
    
    def close(self):
        """Close the socket."""
        if not self.closed:
            try:
                self.sock.close()
            except:
                pass
            self.closed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class PlayerSession:
    def __init__(self, player, socket_host, socket_port, logger=None):
        self.player = player
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.logger = logger
        self.stream = None
        
    def play(self, sound):
        """Play a sound by requesting it from the socket server.
        
        Args:
            sound: Sound identifier string (e.g., "R1234_my_ringtone", "S alarm_start")
                   If the sound name includes .wav extension, it will be stripped.
                   Special characters will be URL-encoded.
            
        Raises:
            PlayerException: If socket connection fails or sound cannot be played
        """
        sock = None
        self.stream = None
        # Free heap before allocating socket buffers and the I2S DMA buffer.
        # A low/fragmented heap makes the I2S init fail with ENOMEM.
        gc.collect()
        if self.logger:
            self.logger(f"DEBUG: Free heap before playback: {gc.mem_free()} bytes")
        try:
            if self.logger:
                self.logger(f"DEBUG: Connecting to streamer {self.socket_host}:{self.socket_port}")
            sock = socket.socket()
            # Timeout for the TCP connect step.
            sock.settimeout(CONNECT_TIMEOUT)
            sock.connect((self.socket_host, self.socket_port))
            if self.logger:
                self.logger("DEBUG: Connected to streamer")
            
            # Disable Nagle's algorithm to reduce TCP buffering delays if supported
            if hasattr(socket, "IPPROTO_TCP") and hasattr(socket, "TCP_NODELAY"):
                try:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except Exception as e:
                    if self.logger:
                        self.logger(f"DEBUG: Could not set TCP_NODELAY: {e}")
            # Increase receive buffer size to handle streaming data better if supported
            if hasattr(socket, "SOL_SOCKET") and hasattr(socket, "SO_RCVBUF"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16384)
                except Exception as e:
                    if self.logger:
                        self.logger(f"DEBUG: Could not set SO_RCVBUF: {e}")

            
            # The streamer server needs time to locate the file on disk and
            # start sending. 2s was far too short and made ringtones fail with
            # ETIMEDOUT, so give the header read a generous timeout.
            sock.settimeout(HEADER_TIMEOUT)
            
            # Remove .wav extension if present (streamer server adds it)
            sound_name = sound
            
            # URL-encode the sound name to handle special characters safely
            # Keep alphanumerics, underscore, hyphen, and dot unencoded
            encoded_sound_name = quote(sound_name, safe='_-.')
            
            # Send sound request: 1 byte length + sound name
            sound_bytes = encoded_sound_name.encode()
            if len(sound_bytes) > 255:
                raise PlayerException(f"Sound name too long: {len(sound_bytes)} bytes (max 255)")
            
            if self.logger:
                self.logger(f"DEBUG: Requesting sound: '{encoded_sound_name}' ({len(sound_bytes)} bytes)")
            
            sock.sendall(len(sound_bytes).to_bytes(1, "big") + sound_bytes)

            # Synchronous buffered socket wrapper — simpler than a background
            # fetch thread, and avoids ring-buffer race conditions / zombie
            # threads that exhaust ESP32 heap on repeated failures.
            self.stream = SocketStreamWrapper(sock, logger=self.logger)

            # Peek at first bytes to verify we got valid WAV data.
            first_bytes = self.stream.read(4)

            if first_bytes == b"":
                raise PlayerException(f"No data from server for '{sound}' - check if server is running and file exists")
            if first_bytes != b"RIFF":
                raise PlayerException(f"Invalid WAV file from server for '{sound}' - expected RIFF, got {first_bytes!r}")

            if self.logger:
                self.logger(f"DEBUG: Got valid WAV header for '{sound}', streaming audio...")

            # Header arrived; use a shorter timeout for the streaming phase so a
            # stalled connection does not block the I2S callback indefinitely.
            sock.settimeout(STREAM_TIMEOUT)

            # Prepend the peeked bytes so the WAV player sees the full header.
            # Plain concat (not assignment) is required: read(4) already consumed
            # bytes from self.buf, and any leftover from that recv() must be kept.
            self.stream.buf = first_bytes + self.stream.buf
            
            # Reclaim the transient buffers used to read the header so the I2S
            # DMA allocation inside the WAV player has the most heap available.
            gc.collect()
            if self.logger:
                self.logger(f"DEBUG: Free heap before I2S init: {gc.mem_free()} bytes")

            # Pass wrapped socket to WAV player
            self.player.play(wav_opened_file=self.stream, loop=False)
            
            if self.logger:
                self.logger(f"DEBUG: Successfully played sound: '{sound}'")
            
        except PlayerException:
            if self.stream is not None:
                self.stream.close()
            elif sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            raise
        except OSError as e:
            if self.stream is not None:
                self.stream.close()
            elif sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            errno = e.args[0] if e.args else None
            if self.logger:
                self.logger(f"ERROR: Socket error (errno {errno}) while playing '{sound}': {e}")
            raise PlayerException(f"Socket error while playing '{sound}' (errno {errno}): {e}")
        except ValueError as e:
            if self.stream is not None:
                self.stream.close()
            elif sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            raise PlayerException(f"WAV format error while playing '{sound}': {e}")
        except Exception as e:
            if self.stream is not None:
                self.stream.close()
            elif sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            # Provide more context in the error message to help debug "Error code: 82"
            error_msg = f"Cannot play this sound. Error: {type(e).__name__}: {e}"
            if self.logger:
                self.logger(f"ERROR: {error_msg}")
            raise PlayerException(error_msg)

    def stop(self):
        self.player.stop()
        if self.stream is not None:
            self.stream.close()
            self.stream = None

class PlayerController:
    @staticmethod
    def play_stop():
        print("stopped")
    
    def __init__(self, socket_host, socket_port, sck_pin=32, ws_pin=25, sd_pin=33, on_finish=play_stop, logger=None):
        self.player = WavPlayer(id=0, sck_pin=sck_pin, ws_pin=ws_pin, sd_pin=sd_pin, ibuf=2048, on_finish=on_finish)
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.logger = logger
        
    def get_session(self):
        return PlayerSession(self.player, self.socket_host, self.socket_port, self.logger)