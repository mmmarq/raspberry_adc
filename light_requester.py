#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import socket
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError
from keyczar.errors import KeyNotFoundError
from time import localtime, strftime
import os
import traceback
import getopt
import logging

#Log file name
logFile = ""

_MASTER_PHRASE = "/home/pi/.keys/masterphrase"
_MASTER_PVT_KEY = "/home/pi/.keys/master_private"
_PUB_KEY = "/home/pi/.keys/public"

#Test environment
#_MASTER_PHRASE = "/Users/wmm125/.ssh/raspberry/keys/masterphrase"
#_MASTER_PVT_KEY = "/Users/wmm125/.ssh/raspberry/keys/master_private"
#_PUB_KEY = "/Users/wmm125/.ssh/raspberry/keys/public"

_MSGLEN = 690

_HOST = '127.0.0.1'        # Symbolic name meaning all available interfaces
_PORT = 4055               # Arbitrary non-privileged port

def read_master_phrase():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading master pass phrase file")
   if not os.path.isfile(_MASTER_PHRASE):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Master pass phrase file not found")
      return ""
   with open(_MASTER_PHRASE) as f:
      content = f.readline()
      return content.strip()

def server_thread(sock):
   rpic = None
   master_phrase = read_master_phrase()

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Loading Private keys")
   decrypter = keyczar.Crypter.Read(_MASTER_PVT_KEY)
   crypter = keyczar.Encrypter.Read(_PUB_KEY)

   while True:
      try:
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Waiting for connections...")
         c, addr = sock.accept()
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Got connection from " + str(addr))

         msg = ''

         #Read message from incoming connection
         while len(msg) < _MSGLEN:
            chunk = c.recv(_MSGLEN-len(msg))
            if chunk == '':
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - socket connection broken")
               raise RuntimeError("socket connection broken")
            msg = msg + chunk

         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Got message from client.")

         try:
            #Check if incoming connection is from raspi
            if decrypter.Decrypt(msg) == master_phrase:
               #If incoming connection is from raspi, save connection descriptor
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Hello from Raspi!")
               rpic = c
               continue
         except KeyNotFoundError:
            pass

         #If incoming connection is from client, check if raspi connection is available
         if rpic == None:
            #If not, send error message and close connection
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - There is no Raspi connection available")
            c.send(crypter.Encrypt("ServerNotFound"))
            c.close()
            continue

         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Sending message to server.")
         try:
            rpic.send(msg)
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Waiting for server reply")

            msg = ''
            while len(msg) < _MSGLEN:
               chunk = rpic.recv(_MSGLEN-len(msg))
               if chunk == '':
                  logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - socket connection broken")
                  raise RuntimeError("socket connection broken")
               msg = msg + chunk
         except:
            rpic = None
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Raspi connection broken")
            c.send(crypter.Encrypt("ServerNotFound"))
            c.close()
            continue

         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Send reply back to client.")
         c.send(msg)
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Closing connection.")
         c.close()
      except:
         print traceback.format_exc()
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Connection broken!")
         c.close()
         continue

def main():

   global logFile

   parser = OptionParser()
   parser.add_option("-l", "--log", dest="logFileName",
                  help="write report to log logFile", metavar="logFile")

   (options, args) = parser.parse_args()

   logging.basicConfig(filename=options.logFileName,level=logging.INFO)

   #Log start
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Requester process!")


   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Creating Light Requester Network Socket!")
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.bind((_HOST, _PORT))
   s.listen(2)
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Calling server function!")
   server_thread(s)

if __name__ == '__main__':
   main()
