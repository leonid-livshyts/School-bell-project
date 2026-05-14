import socket
from time import sleep

HOST = "127.0.0.1"
PORT = 8088
msg = b"Hello, world"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    for _ in range(10):
        s.sendall(msg)
        data = s.recv(len(msg))
        print(f"Received {data!r}")
        sleep(1)
