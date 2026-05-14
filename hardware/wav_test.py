from wavplayer import WavPlayer
import socket
import network
from time import sleep
import shared

def test_finish():
    print("test_finish")
    


SCK_PIN = 32
WS_PIN = 25
SD_PIN = 33
I2S_ID = 0
BUFFER_LENGTH_IN_BYTES = 2000

mes = b"Hello Bitaliy"

pl = WavPlayer(id=I2S_ID, sck_pin=SCK_PIN, ws_pin=WS_PIN, sd_pin=SD_PIN, ibuf=I2S_ID, root="/", on_finish=test_finish)

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("BROBOTS", "HelloBrobo")
for _ in range(10):
    sleep(1)
    if sta_if.isconnected():
        break
            
s = socket.socket()
s.connect(('10.0.61.144', 12345))


#f = open("ring-phone-190265.wav", "rb")
pl.play(wav_opened_file=s, loop=False)
sleep(5)
pl.stop()
sleep(5)
s = socket.socket()
s.connect(('10.0.61.144', 12345))


#f = open("ring-phone-190265.wav", "rb")
pl.play(wav_opened_file=s, loop=False)
sleep(5)
pl.stop()
    