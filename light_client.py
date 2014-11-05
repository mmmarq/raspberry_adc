#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import socket
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError

def main():

   _PUB_KEY = "/home/pi/.keys/public"
   _PVT_KEY = "/home/pi/.keys/private"

   #Test environment
   #_PUB_KEY = "/Users/wmm125/.ssh/raspberry/keys/public"
   #_PVT_KEY = "/Users/wmm125/.ssh/raspberry/keys/private"

   _MSGLEN = 690

   _HOST = '192.168.0.2'        # Symbolic name meaning all available interfaces
   _PORT = 4055                 # Arbitrary non-privileged port


   print "Loading Private/Public keys.."
   crypter = keyczar.Encrypter.Read(_PUB_KEY)
   decrypter = keyczar.Crypter.Read(_PVT_KEY)

   print "starting client..."
   #Create a socket object
   s = socket.socket()
   #Get local machine name
   host = socket.gethostbyname(_HOST)
   print host
   #Reserve a port for your service.
   port = _PORT

   s.connect((host, port))

   while True:
      command = raw_input('Enter command: ')
      if ( command == 'gate.open' ):
         PASS_PHRASE = raw_input('Enter pass code: ')
         command = command + '|' + PASS_PHRASE
      data = crypter.Encrypt(command)
      print "Sending: " + decrypter.Decrypt(data) + " [" + str(len(data)) + "]"
      s.send(data)
      print "Waiting response..."
      msg = ''
      while len(msg) < _MSGLEN:
         chunk = s.recv(_MSGLEN-len(msg))
         if chunk == '':
            raise RuntimeError("socket connection broken")
         msg = msg + chunk

      print decrypter.Decrypt(msg)
      break

if __name__ == '__main__':
   main()

