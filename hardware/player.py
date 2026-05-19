from wavplayer import WavPlayer
import socket
import time
from time import sleep
try:
    import _thread
    THREADING_AVAILABLE = True
except ImportError:
    THREADING_AVAILABLE = False

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


class RollingBufferWrapper:
    """Rolling buffer for socket streaming with background fetching.
    
    Maintains a rolling window of 3 chunks:
    - Chunk being read (audio callback)
    - Chunk waiting to be read
    - Chunk being filled from socket
    
    This decouples socket I/O from audio playback timing.
    """
    def __init__(self, sock, chunk_size=4096, num_chunks=3, logger=None):
        self.sock = sock
        self.chunk_size = chunk_size
        self.num_chunks = num_chunks
        self.logger = logger
        self.closed = False
        self.position = 0
        self.bytes_received = 0
        self.eof = False
        
        # Circular buffer: list of chunks
        self.chunks = [b"" for _ in range(num_chunks)]
        self.current_chunk_idx = 0  # Which chunk we're currently reading from
        self.fill_idx = 0  # Which chunk we're currently filling from socket
        self.chunk_offsets = [0] * num_chunks  # Position within each chunk
        self.fetch_thread = None
        self.fetch_done = False
        self.peek_buf = b""  # Buffer for peeked data (e.g., RIFF header check)
        
        if THREADING_AVAILABLE:
            # Start background fetch thread
            try:
                self.fetch_thread = _thread.start_new_thread(self._fetch_loop, ())
            except Exception as e:
                if logger:
                    logger(f"ERROR: Failed to start fetch thread: {e}")
    
    def _fetch_loop(self):
        """Background thread that continuously fetches data from socket."""
        try:
            while not self.closed and not self.eof:
                try:
                    chunk = self.sock.recv(self.chunk_size)
                    if not chunk:
                        self.eof = True
                        break
                    self.bytes_received += len(chunk)
                    self.chunks[self.fill_idx] = chunk
                    self.chunk_offsets[self.fill_idx] = 0
                    # Move to next chunk slot
                    self.fill_idx = (self.fill_idx + 1) % self.num_chunks
                except OSError as e:
                    # MicroPython has no socket.timeout class; recv() timeouts
                    # surface as OSError with errno 11 (EAGAIN) or 110 (ETIMEDOUT)
                    errno = e.args[0] if e.args else None
                    if errno in (11, 110):
                        if self.logger:
                            self.logger("DEBUG: Socket timeout in fetch thread - retrying...")
                        continue
                    if self.logger:
                        self.logger(f"ERROR in fetch thread: {e}")
                    self.eof = True
                except Exception as e:
                    if self.logger:
                        self.logger(f"ERROR in fetch thread: {e}")
                    self.eof = True
        finally:
            self.fetch_done = True
    
    def read(self, n):
        """Read exactly n bytes from rolling buffer."""
        if self.closed:
            raise OSError("Buffer is closed")
        
        result = b""
        bytes_needed = n
        
        # First, consume any peeked data
        if len(self.peek_buf) > 0:
            to_take = min(len(self.peek_buf), bytes_needed)
            result += self.peek_buf[:to_take]
            self.peek_buf = self.peek_buf[to_take:]
            bytes_needed -= to_take
            self.position += to_take
            self.bytes_received += to_take
            if bytes_needed == 0:
                return result
        
        while bytes_needed > 0 and not self.eof:
            # Get current chunk
            chunk = self.chunks[self.current_chunk_idx]
            offset = self.chunk_offsets[self.current_chunk_idx]
            
            if offset >= len(chunk):
                # Current chunk exhausted, move to next
                if self.fetch_done and self.current_chunk_idx == self.fill_idx:
                    # No more chunks available
                    break
                
                # If we've caught up to the fill thread but it's not done,
                # we need to wait a bit for more data.
                next_idx = (self.current_chunk_idx + 1) % self.num_chunks
                if next_idx == self.fill_idx and not self.fetch_done:
                    # No new data yet, wait a tiny bit to avoid busy-wait
                    sleep(0.01)
                    continue
                    
                self.current_chunk_idx = next_idx
                self.chunks[self.current_chunk_idx] = b""
                self.chunk_offsets[self.current_chunk_idx] = 0
                continue
            
            # Read from current chunk
            available = len(chunk) - offset
            to_read = min(available, bytes_needed)
            result += chunk[offset:offset + to_read]
            self.chunk_offsets[self.current_chunk_idx] += to_read
            self.position += to_read
            self.bytes_received += to_read
            bytes_needed -= to_read
        
        if not result and self.bytes_received == 0 and self.logger:
            self.logger("ERROR: Server sent no data - file may not exist on server")
        
        return result
    
    @property
    def buf(self):
        """Compatibility property for peeked data buffer."""
        return self.peek_buf
    
    @buf.setter
    def buf(self, value):
        """Compatibility setter for prepending peeked data."""
        self.peek_buf = value
    
    def readinto(self, b):
        """Read bytes directly into the provided buffer."""
        data = self.read(len(b))
        if not data:
            return 0
        b[:len(data)] = data
        return len(data)
    
    def seek(self, pos, whence=0):
        """Forward-only seek support."""
        if whence != 0:
            raise OSError("seek only supports absolute positions")
        if pos < self.position:
            raise OSError("cannot seek backwards")
        if pos == self.position:
            return self.position
        to_skip = pos - self.position
        while to_skip > 0:
            chunk = self.read(min(to_skip, 4096))
            if not chunk:
                raise OSError("cannot seek past end")
            to_skip -= len(chunk)
        return self.position
    
    def close(self):
        """Close the buffer and socket."""
        if not self.closed:
            self.closed = True
            try:
                self.sock.close()
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


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
            except socket.timeout:
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
        try:
            sock = socket.socket()
            # Set a short timeout for the connect and initial handshake only.
            sock.settimeout(10)
            sock.connect((self.socket_host, self.socket_port))
            
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

            
            # Set a more reasonable timeout for the initial data fetch (RIFF header)
            sock.settimeout(2.0)
            
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
            
            # Use RollingBufferWrapper which fetches data in a background thread
            # This prevents network jitter from blocking or timing out the I2S callback
            self.stream = RollingBufferWrapper(sock, chunk_size=4096, num_chunks=4, logger=self.logger)
            if self.logger:
                self.logger("DEBUG: Using rolling buffer wrapper for background streaming")
            
            # Peek at first bytes to verify we got valid WAV data
            # Use a loop with a timeout since the background thread might be slow to start
            first_bytes = b""
            # Wait up to 5 seconds for the header
            wait_limit = time.time() + 5
            while len(first_bytes) < 4 and time.time() < wait_limit:
                chunk = self.stream.read(4 - len(first_bytes))
                if chunk:
                    first_bytes += chunk
                else:
                    time.sleep(0.1)
            
            if first_bytes == b"":
                raise PlayerException(f"No data from server for '{sound}' - check if server is running and file exists")
            if first_bytes != b"RIFF":
                raise PlayerException(f"Invalid WAV file from server for '{sound}' - expected RIFF, got {first_bytes!r}")
            
            # Put the peeked bytes back into the buffer
            self.stream.buf = first_bytes
            
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
            raise PlayerException(f"Socket error while playing '{sound}': {e}")
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