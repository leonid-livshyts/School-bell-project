import asyncio
import json
import socket
from pathlib import Path
try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

root = Path(__file__).resolve().parent
config_path = root / "config.json"
voices_path = ringtones_path = sounds_path = misc_path = None

if not config_path.is_file():
    raise FileNotFoundError("There is no config.json")
else:
    try:
        with config_path.open(encoding="utf-8") as config_f:
            config_json = json.load(config_f)
        voices_path = Path(config_json["voices_path"]).resolve()
        ringtones_path = Path(config_json["ringtones_path"]).resolve()
        sounds_path = Path(config_json["sounds_path"]).resolve()
        misc_path = Path(config_json["misc_path"]).resolve()
    except Exception as e:
        raise Exception(f"Failed to load config: {e}") from e

MAX_REQUEST_NAME_BYTES = 255


def normalize_media_request(full_string):
    if not full_string:
        raise ValueError("Empty request string")

    media_type = full_string[0]
    raw_name = full_string[1:]
    media_name = unquote(raw_name).strip()
    if media_name.lower().endswith('.wav'):
        media_name = media_name[:-4]
    if not media_name:
        raise ValueError("Empty media name after decoding")

    return media_type, media_name


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    address = writer.get_extra_info('peername')
    print(f"[+] Connection accepted from {address}")

    # Disable Nagle's algorithm and increase send buffer for better streaming
    sock = writer.get_extra_info('socket')
    if sock:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16384)

    try:
        length_data = await reader.readexactly(1)
        name_len = length_data[0]

        if name_len == 0:
            print(f"[!] Empty name length received from {address}")
            return
        if name_len > MAX_REQUEST_NAME_BYTES:
            print(f"[!] Request length {name_len} exceeds maximum from {address}")
            return

        name_bytes = await reader.readexactly(name_len)
        full_string = name_bytes.decode('utf-8')
        media_type, media_name = normalize_media_request(full_string)

        print(f"[*] Media type: {media_type}, Requested name: {full_string[1:]}, Normalized name: {media_name}")

        search_path = misc_path
        if media_type.startswith('V'):
            search_path = voices_path
        elif media_type.startswith('R'):
            search_path = ringtones_path
        elif media_type.startswith('S'):
            search_path = sounds_path

        filename = (search_path / (media_name + '.wav')).resolve()

        if not filename.is_relative_to(search_path):
            print(f"[!] Security violation: requested file outside search path: {filename}")
            return
        if not filename.is_file():
            print(f"[!] File not found: {filename}")
            return

        file_size = filename.stat().st_size
        bytes_sent = 0
        CHUNK_SIZE = 4096

        try:
            with filename.open('rb') as f:
                while True:
                    chunk = await asyncio.get_running_loop().run_in_executor(None, f.read, CHUNK_SIZE)
                    if not chunk:
                        break
                    writer.write(chunk)
                    await writer.drain()
                    bytes_sent += len(chunk)

            if bytes_sent == file_size:
                print(f"[-] Sent {filename.name} ({bytes_sent} bytes) to {address}")
            else:
                print(f"[!] Incomplete send to {address}: {bytes_sent}/{file_size} bytes")
        except (ConnectionResetError, BrokenPipeError):
            print(f"[!] Client {address} closed connection before file send completed ({bytes_sent}/{file_size} bytes)")
            return

    except asyncio.IncompleteReadError:
        print(f"[!] Client {address} disconnected before sending full data")
    except UnicodeDecodeError:
        print(f"[!] Invalid UTF-8 request from {address}")
    except ValueError as e:
        print(f"[!] Invalid request from {address}: {e}")
    except Exception as e:
        print(f"[!] Error handling client {address}: {e}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    host = '0.0.0.0'
    port = 8088

    server = await asyncio.start_server(handle_client, host, port)
    print(f"[*] Async Server listening on {host}:{port}")

    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Server shutting down.")


if __name__ == '__main__':
    asyncio.run(main())
