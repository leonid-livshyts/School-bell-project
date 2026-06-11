import asyncio
import json
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


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    address = writer.get_extra_info("peername")
    print(f"[+] Connection accepted from {address}")
    try:
        length_data = await reader.read(1)
        if not length_data:
            return
        name_len = length_data[0]
        if name_len == 0:
            return

        name_bytes = await reader.readexactly(name_len)
        full_string = name_bytes.decode("utf-8")
        media_type = full_string[0]
        media_name = unquote(full_string[1:]).strip()
        if media_name.lower().endswith('.mp3'):
            media_name = media_name[:-4]

        print(f"[*] Media type: {media_type}, Requested name: {full_string[1:]}, Normalized name: {media_name}")
        search_path = misc_path
        if media_type.startswith("V"):
            search_path = voices_path
        elif media_type.startswith("R"):
            search_path = ringtones_path
        elif media_type.startswith("S"):
            search_path = sounds_path

        if isinstance(search_path, Path):
            filename = (search_path / (media_name + ".mp3")).resolve()
            if filename.is_relative_to(search_path) and filename.is_file():
                # Offload blocking file I/O to a thread pool
                loop = asyncio.get_running_loop()
                file_data = await loop.run_in_executor(None, filename.read_bytes)
                writer.write(file_data)
                await writer.drain()
                print(f"[-] Sent {filename.name} to {address}")
            else:
                print(f"[!] Invalid or missing file requested by {address}")
    except asyncio.IncompleteReadError:
        print(f"[!] Client {address} disconnected before sending full data")
    except Exception as e:
        print(f"[!] Error handling client {address}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    host = "0.0.0.0"
    port = 8088

    server = await asyncio.start_server(handle_client, host, port)
    print(f"[*] Async Server listening on {host}:{port}")

    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Server shutting down.")


if __name__ == "__main__":
    asyncio.run(main())