#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket

HOST = '192.168.0.2'      # Symbolic name meaning all available interfaces
PORT = 1980               # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
while 1:
    conn, addr = s.accept()
    data = conn.recv(1024)
    if not data: break
    conn.sendall(data)
    conn.close()
