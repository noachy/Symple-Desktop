import math
import socket
import os

filename = './test-send/symple_logo.png'

HOST = '127.0.0.1'
PORT = 17701
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        s.sendall(b'S')
        ack = s.recv(1024)

        print('Received Ack 1')

        filesize = os.path.getsize(filename)
        s.sendall(f"{filename.split('/')[-1]}:{filesize}".encode())
        ack = s.recv(1024)

        print('Received Ack 2')

        with open(filename, 'rb') as f:
            while read_bytes := f.read(1024):
                s.sendall(read_bytes)
        input()
