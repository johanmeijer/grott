import socket
import time

localhost = '127.0.0.1'
port = 5279
delay = 1.0
packet = bytearray(TODO)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((localhost, port))

    while 1:
        time.sleep(delay)
        print(".")
        sock.sendall(packet)
