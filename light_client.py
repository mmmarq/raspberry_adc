#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import socket
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError

def main():

   #PUB_KEY = "/home/pi/.keys/public"
   #PVT_KEY = "/home/pi/.keys/private"

   #Test environment
   PUB_KEY = "/Users/wmm125/.ssh/raspberry/keys/public"
   PVT_KEY = "/Users/wmm125/.ssh/raspberry/keys/private"


   MSGLEN = 690
   
   print "Loading Private/Public keys.."
   crypter = keyczar.Encrypter.Read(PUB_KEY)
   decrypter = keyczar.Crypter.Read(PVT_KEY)

   print "starting client..."
   #Create a socket object
   s = socket.socket()
   #Get local machine name
   #host = socket.gethostbyname("192.168.0.2")
   host = socket.gethostbyname("127.0.0.1")
   print host
   #Reserve a port for your service.
   port = 8000

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
      while len(msg) < MSGLEN:
         chunk = s.recv(MSGLEN-len(msg))
         if chunk == '':
            raise RuntimeError("socket connection broken")
         msg = msg + chunk

      print decrypter.Decrypt(msg)
      break

if __name__ == '__main__':
   main()

