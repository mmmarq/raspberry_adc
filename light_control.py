#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import thread
import threading
import datetime
import time
import sys
import getopt
import subprocess
import signal
import socket
import traceback
import logging
import smbus
import time
import re
import os
from time import localtime, strftime
from datetime import timedelta
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError
from optparse import OptionParser

# for RPI version 1, use "bus = smbus.SMBus(0)" - i2c setup
i2c_bus = smbus.SMBus(1)
# This is the i2c address set in the Arduino Program
i2c_address = 0x04
#Log file name
logFile = ""
#Define if light is in manual operation
manualOperation = False
#Light level to trigger light_on
minLightLevel = 175
#Control light status
lightStatus = False
#Light control array
lightArray = [0,0,0,0]
#Control if light meter should sleep
mySleep = False
#Server port number
portNum = 50004
#Server IP address
ipAddr = "192.168.0.2"
#Config file folder
configFileFolder = "/media/2/log"
#Config file name
configFileName = "light_control.cfg"
#Alarm helper
setByProgram = True
#Serial communication semaphore file
lock = threading.Lock()

#Cyphering paths
PUB_KEY = "/home/pi/.keys/public"
PVT_KEY = "/home/pi/.keys/private"
SGN_KEY = "/home/pi/.keys/signkeys"
PASS_PHRASE = "/home/pi/.keys/passphrase"

#i2c communication re rules
i2c_char_pattern = re.compile('^[A-Z]$')
i2c_array_pattern = re.compile('^[0-1]{4}$')

def read_pass_phrase():
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Reading pass phrase file")
   if not os.path.isfile(PASS_PHRASE):
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Pass phrase file not found")
      return ""
   with open(PASS_PHRASE) as f:
      content = f.readline()
      return content.rstrip()

#Function to convert lightArray to bit string
def lightArray_to_int(data):
   return int(str(data)[1:-1].replace(" ","").replace(",",""),2)

#Function to call turn_light_off by alarm signal
def handler_light_off(signum, frame):
   global manualOperation
   global lightStatus
   global lightArray
   global mySleep
   global setByProgram

   if (setByProgram):
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Turning external light off!")
      lightArray[0] = 0
      send_data_to_arduino(lightArray_to_int(lightArray),True)
      setByProgram = False
      signal.alarm(1800)
   else:
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Its time to turn lights off... See you tomorrow!")
      turn_light_off()
      lightStatus = False
      manualOperation = False
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light level checking is going to sleep until next morning.")
      #Set sleep true in order to trigger light on only next night
      mySleep = True
      signal.alarm(0)

   #Save config file
   save_status()

#Function to send command to Arduino
def send_data_to_arduino(data,log):
   global lock
   global i2c_bus
   global i2c_address
   global i2c_char_pattern
   global i2c_array_pattern
   result = 0
   try:
      lock.acquire()
      if log: logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Sending data to Arduino: " + str(data))

      if ( i2c_char_pattern.match(str(data)) ):
         i2c_bus.write_byte(i2c_address, ord(data))
      elif ( i2c_array_pattern.match(str(data)) ):
         i2c_bus.write_byte(i2c_address, int(data,2))
      #Give Arduino some time to update values
      time.sleep(0.5)
      result = i2c_bus.read_byte(i2c_address)
   finally:
      lock.release()
   
   if ( data == 'S' ):
      result = "{0:b}".format(result).zfill(4)
   return result

def gate_opener():
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Opening Gate!!!")
   send_data_to_arduino("G",True)

def read_light_meter():
   return send_data_to_arduino("L",False)

def read_status():
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Reading configuration file")
   if not os.path.exists(configFileFolder):
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - " + configFileFolder + " folder does not exist, creating new one")
      os.makedirs(configFileFolder)
   if not os.path.isfile(os.path.join(configFileFolder,configFileName)):
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Creating config file with current status")
      text_file = open(os.path.join(configFileFolder,configFileName), "w")
      status = get_status()
      text_file.write("%s" % status)
      text_file.close()
      return status
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Reading config file content")
   with open(os.path.join(configFileFolder,configFileName)) as f:
      content = f.readline()
      return content

def save_status():
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Saving configuration file")
   if not os.path.exists(configFileFolder):
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - " + configFileFolder + " folder does not exist, creating new one")
      os.makedirs(configFileFolder)
   if os.path.isfile(os.path.join(configFileFolder,configFileName)):
      os.remove(os.path.join(configFileFolder,configFileName))
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Creating config file with current status")
   text_file = open(os.path.join(configFileFolder,configFileName), "w")
   status = get_status()
   text_file.write("%s" % status)
   text_file.close()

def read_sensors():
   return str(send_data_to_arduino("T",True)) + "," + str(send_data_to_arduino("H",True))

def get_status():
   global lightStatus
   global manualOperation
   global lightArray

   status = str(lightArray)[1:-1].replace(" ","") + ","
   if ( manualOperation ):
      status = status + "0,"
   else:
      status = status + "1,"
   status = status + read_sensors()
   return status

def turn_light_on():
   global lightStatus
   global lightArray
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Turning light on!")
   lightArray = [1,1,1,1]
   send_data_to_arduino(lightArray_to_int(lightArray),True)
   lightStatus = True

def turn_light_off():
   global lightStatus
   global lightArray
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Turning light off!")
   lightArray = [0,0,0,0]
   send_data_to_arduino(lightArray_to_int(lightArray),True)
   lightStatus = False

def light_control():
   global manualOperation
   global lightStatus
   global lightArray
   global mySleep
   global setByProgram

   #Variable to make this thread turn light on automatically only next day
   mySleep = False

   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Starting Light Sensor Control!")

   #Read previous status
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Reading configuration file")
   status = read_status().split(',')

   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Configuration file content: " + str(status))
   lightArray = (int(status[0]),int(status[1]),int(status[2]),int(status[3]))
   send_data_to_arduino(lightArray_to_int(lightArray),True)
   if ( lightArray_to_int(lightArray) >= 1):
      lightStatus = True
   else:
      lightStatus = False

   if (status[4] == "0"):
      manualOperation = True
   else:
      manualOperation = False

   if ( not manualOperation and lightStatus ):
      timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(29 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
      if ( int(timeFrame.total_seconds()) < 0 ):
         timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
         signal.alarm(int(timeFrame.total_seconds()))
         setByProgram = False
         logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
      else:
         signal.alarm(int(timeFrame.total_seconds()))
         setByProgram = True
         logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")

   #Keep it running forever
   while True:
      #Read ADC light meter value and test
      #only if there is no light enough outside(check minLightLevel)
      #light is not already on (lightStatus)
      #system is not in manual operation (manualOperation)
      #light meter is not in sleep mode (mySleep)
      if ( read_light_meter() <= minLightLevel and not lightStatus and not manualOperation and not mySleep ):
         #If light level lower than trigger and light off, turn light on
         turn_light_on()
         #Set alarm to turn light off
         timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(29 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
         if ( int(timeFrame.total_seconds()) < 0 ):
            timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
            signal.alarm(int(timeFrame.total_seconds()))
            setByProgram = False
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
         else:
            signal.alarm(int(timeFrame.total_seconds()))
            setByProgram = True
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
         #Save config file
         save_status()
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(600) #sleep 10 minutes

      #Check if there is light enough outside
      if ( read_light_meter() > minLightLevel ):
         #Remove any existing alarm
         signal.alarm(0)
         #Set manual operation fasle (no)
         if ( manualOperation ):
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Good morning... Set manual operation false.")
            manualOperation = False
         #Set sleep false in order to enable light turn on next night
         if ( mySleep ):
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Good morning... Wake up light level checking.")
            mySleep = False

         #If ligh is on, turn light off
         if ( lightStatus ):
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Good morning... Turns light off!")
            #If light level bigger than trigger and light on, turn light off
            turn_light_off()
            #Save config file
         save_status()

         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(300) #sleep 5 minutes

      #Just wait a while before start next loop iteration
      time.sleep(10)

def light_server():
   global lightStatus
   global manualOperation
   global mySleep
   global setByProgram

   arrayPattern = re.compile('[0-1]{5}')

   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Starting Network Server")

   MSGLEN = 690

   logging.info("Loading Private/Public keys..")
   crypter = keyczar.Encrypter.Read(PUB_KEY)
   decrypter = keyczar.Crypter.Read(PVT_KEY)
   signer = keyczar.UnversionedSigner.Read(SGN_KEY)

   #Read pass_phrase
   pass_phrase = read_pass_phrase()

   #Create a socket object
   s = socket.socket()
   #Get local machine name
   host = socket.gethostbyname(ipAddr)
   #Bind to the port
   s.bind((host, portNum))

   #Now wait for client connection.
   s.listen(2)

   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Waiting for connection...")

   while True:
      try:
         #Establish connection with client.
         c, addr = s.accept()
         logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Got connection from " + str(addr))
         msg = ''

         while len(msg) < MSGLEN:
            chunk = c.recv(MSGLEN-len(msg))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
         msg = decrypter.Decrypt(msg)
         logging.info("Received: " + msg)
         if ( msg == "status.all" ):
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Full status requested")
            status = get_status()
            logging.info("Send: " + status)
            c.send(crypter.Encrypt(status))
            logging.info("Message sent!")
         elif ( arrayPattern.match(msg) ):
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Set light status request")
            lightArray[0] = msg[0]
            lightArray[1] = msg[1]
            lightArray[2] = msg[2]
            lightArray[3] = msg[3]

            if ( msg[0] == '1' or msg[1] == '1' or msg[2] == '1' or msg[3] == '1' ):
               lightStatus = true
            else:
               lightStatus = false

            if ( msg[4] == '0' ):
               manualOperation = True
               signal.alarm(0)
            else:
               manualOperation = False
               mySleep = False
               if ( lightStatus ):
                  timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(29 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
                  if ( int(timeFrame.total_seconds()) < 0 ):
                     timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
                     signal.alarm(int(timeFrame.total_seconds()))
                     setByProgram = False
                     logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
                  else:
                     signal.alarm(int(timeFrame.total_seconds()))
                     setByProgram = True
                     logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
            send_data_to_arduino(lightArray_to_int(lightArray),True)
            save_status()
            c.send(crypter.Encrypt(get_status()))
         elif re.match('^gate.open\|.+',msg) is not None:
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Gate Opening request")
            passcode = msg.split('|')[1]
            rcvd_hash = signer.Sign(passcode)
            if (pass_phrase == rcvd_hash):
               logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Signature check is ok")
               gate_opener()
               c.send(crypter.Encrypt('ok'))
            else:
               logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Signature check fail")
               c.send(crypter.Encrypt('fail'))
         else:
            logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Request not valid")
            c.send(crypter.Encrypt('fail'))
      except:
         logging.info(traceback.format_exc())
         c.close()
         continue
      #Close the connection
      logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Connection closed!")
      c.close()

def main():

   global logFile

   parser = OptionParser()
   parser.add_option("-l", "--log", dest="logFileName",
                  help="write report to log logFile", metavar="logFile")

   (options, args) = parser.parse_args()

   logging.basicConfig(filename=options.logFileName,level=logging.INFO)

   #Log start
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Starting Light Control threads!")

   #Set SIGALARM response
   signal.signal(signal.SIGALRM, handler_light_off)

   #Start light control thread
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Starting Light Sensor Thread")
   p1 = threading.Thread(target=light_control, args=[])
   p1.start()

   #start network process
   logging.info(strftime("%d-%m-%Y %H:%M:%S", localtime()) + " - Starting Light Control Network Server")
   p2 = threading.Thread(target=light_server, args=[])
   p2.start()
   
   while True:
      time.sleep(5)

if __name__ == '__main__':
   main()

