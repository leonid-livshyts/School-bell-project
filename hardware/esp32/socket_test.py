import socket
import network
from time import sleep

mes = b"Hello Bitaliy"

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("BROBOTS", "HelloBrobo")
for _ in range(10):
    sleep(1)
    if sta_if.isconnected():
        break


            
s = socket.socket()
s.connect(('10.0.61.143', 12345))
for _ in range(10):
    s.send(f"{len(mes)}|".encode()+mes)
    resp = s.recv(len(mes)+2)
    sleep(2)