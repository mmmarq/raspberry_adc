#!/usr/bin/python
# -*- coding: utf-8 -*-

# Echo client program
import socket
import time
import subprocess

_HOST = 'localhost'       # The remote host
_PORT = 1980              # The same port as used by the server
_MSG = 'Hello Pi'

cmd = ['sudo', 'kill', '-9']

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(60)

try:
   s.connect((_HOST, _PORT))

   s.sendall(_MSG)
   data = s.recv(1024)
   s.close()
except:
   data = ''

if _MSG != data:
   print "Restarting ssh service..."
   try:
      sshpid = subprocess.check_output("sudo lsof -i 4 -n | grep sshd | grep :1980 | grep -v grep", shell=True).split()[1]
   except:
      sshpid = ''

   if len(sshpid) > 0:
      cmd.append(sshpid)
      print cmd
      subprocess.call(cmd, shell=False)


