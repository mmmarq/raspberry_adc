#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import socket
import Crypto
from Crypto.PublicKey import RSA

def main():

   MSGLEN = 256
   print "starting client..."
   print "Loading Private/Public keys.."

   #Load private and public keys
   private_key = Crypto.PublicKey.RSA.importKey(open('./id_rsa', 'r').read())
   key = Crypto.PublicKey.RSA.importKey(open('./id_rsa.pub', 'r').read())
   public_key = key.publickey()

   #Create a socket object
   s = socket.socket()
   #Get local machine name
   host = socket.gethostname()
   #Reserve a port for your service.
   port = 12345

   s.connect((host, port))

   while True:
      command = raw_input('Enter command: ')
      print "Sending: " + command
      data = public_key.encrypt(command, MSGLEN)[0]
      print "Sending: " + private_key.decrypt(data) + " [" + str(len(data)) + "]"
      s.send(data)
      print "Waiting response..."
      msg = ''
      while len(msg) < MSGLEN:
         chunk = s.recv(MSGLEN-len(msg))
         if chunk == '':
            raise RuntimeError("socket connection broken")
         msg = msg + chunk

      print private_key.decrypt(msg)
      break

if __name__ == '__main__':
   main()

