#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import socket
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError
from keyczar.errors import KeyNotFoundError
from time import localtime, strftime
from optparse import OptionParser
import time
import os
import traceback
import getopt
import logging

#Log file name
logFile = ""

#Socket
sock = Socket

_PUB_KEY = "/home/pi/.keys/public"

#Test environment
#_MASTER_PHRASE = "/Users/wmm125/.ssh/raspberry/keys/masterphrase"
#_MASTER_PVT_KEY = "/Users/wmm125/.ssh/raspberry/keys/master_private"
#_PUB_KEY = "/Users/wmm125/.ssh/raspberry/keys/public"

_MSGLEN = 690

#_HOST = '162.243.151.23'
#_RPHOST = '177.53.107.160'

_HOST = 'mmmarq.dnsdynamic.net'     # Symbolic name meaning all available interfaces
_PORT = 4055                        # Arbitrary non-privileged port
_RPHOST = 'mmmarqpi.dnsdynamic.net' # Raspiberry Pi address

def read_master_phrase():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading master pass phrase file")
   if not os.path.isfile(_MASTER_PHRASE):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Master pass phrase file not found")
      return ""
   with open(_MASTER_PHRASE) as f:
      content = f.readline()
      return content.strip()

def server_start():

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Loading keys")
   crypter = keyczar.Encrypter.Read(_PUB_KEY)

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Waiting for connections...")

   while True:
      try:
         c, addr = sock.accept()
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Got connection from " + str(addr))

         msg = ''

         #Read message from incoming connection
         while len(msg) < _MSGLEN:
            chunk = c.recv(_MSGLEN-len(msg))
            if chunk == '':
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Client socket connection broken")
               raise socket.error
            msg = msg + chunk

         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Connecting to server")
         rpic = socket.socket()
         rpic.connect((_RPHOST, _PORT))
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Sending message to server")
         rpic.send(msg)
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading message from server")
         msg = ''
         while len(msg) < _MSGLEN:
            chunk = rpic.recv(_MSGLEN-len(msg))
            if chunk == '':
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Server socket connection broken")
               raise socket.error
            msg = msg + chunk
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Closing server connection")
         rpic.close()

         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Send reply back to client.")
         c.send(msg)
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Closing connection.")
         c.close()
      except socket.error:
         print traceback.format_exc()
         c.send(crypter.Encrypt('ServerNotFound'))
         c.close()
         rpic.close()
         continue

def main():
   global logFile
   global sock

   parser = OptionParser()
   parser.add_option("-l", "--log", dest="logFileName",
                  help="write report to log logFile", metavar="logFile")

   (options, args) = parser.parse_args()
   logging.basicConfig(filename=options.logFileName,level=logging.INFO)

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Creating Light Requester Network Socket!")
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   while True:
      try:
         sock.bind((_HOST, _PORT))
         break
      except socket.error:
         time.sleep(2)
         continue
   sock.listen(2)

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Calling server function!")
   server_start()

if __name__ == '__main__':
   main()

