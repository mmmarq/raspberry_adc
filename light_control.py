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
import struct
import traceback
import logging
import urllib
import urllib2
import re
import os
import ephem
from subprocess import Popen, PIPE, call
from time import localtime, strftime
from datetime import timedelta
from datetime import datetime
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError
from optparse import OptionParser
import RPi.GPIO as GPIO

#Set Ephemerides location
location = ephem.Observer()
location.lat = '-22:41:94'
location.lon = '-46:84:02'
sun = ephem.Sun()

#Log file name
logFile = ""
#Define if light is in manual operation
manualOperation = False
#GPIO pin to control light relay
lightPins = (16,20)
#Control light status
lightStatus = False
#GPIO pin to open gate
gatePin = 26
#Gate signal lenght
gateSignalLenght = 0.5
#Server port number
portNum = 50004
#Server IP address
ipAddr = "192.168.1.2"
#Config file folder
configFileFolder = "/mnt/code/log"
#Camera URL
cameraURL = []
#Camera CFG file
cameraCfgFile = "/home/pi/.keys/camera.cfg"
#Arduino CFG file
arduinoCfgFile = "/home/pi/.keys/arduino.cfg"
#Arduino Address
arduinoIP = ""

#Cyphering paths
PUB_KEY = "/home/pi/.keys/public"
PVT_KEY = "/home/pi/.keys/private"
SGN_KEY = "/home/pi/.keys/signkeys"
PASS_PHRASE = "/home/pi/.keys/passphrase"

def load_camera_url():
   global cameraURL
   if os.path.isfile(cameraCfgFile):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading camera config file content")
      with open(cameraCfgFile) as f:
         cameraURL = f.readlines()
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Found " + str(len(cameraURL)) + " camera URLs")

def load_arduino_ip():
   global arduinoIP
   if os.path.isfile(arduinoCfgFile):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading arduino config file content")
      with open(arduinoCfgFile) as f:
         arduinoIP = f.readline().rstrip()
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Found " + arduinoIP + " arduino IP")

def gate_opener(gatePin):
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate opened!!!")
   GPIO.output(gatePin, True)
   time.sleep(gateSignalLenght)
   GPIO.output(gatePin, False)

def read_pass_phrase():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading pass phrase file")
   if not os.path.isfile(PASS_PHRASE):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Pass phrase file not found")
      return ""
   with open(PASS_PHRASE) as f:
      content = f.readline()
      return content.rstrip()

def read_local_data():
   global arduinoIP
   lTemp = "0.00"
   lHumid = "0.00"
   lPres = "0.00"

   # Read data from Arduino
   try:
      response = urllib2.urlopen(arduinoIP, timeout=2)
      html = response.read()
      temp,humid,pres,alarm,light,rasp = html.split()
      lTemp = "{0:0.1f}".format(float(temp))
      lHumid =  "{0:0.1f}".format(float(humid))
      lPres =  "{0:0.1f}".format(float(pres))
   except socket.timeout, e:
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Timeout error reading data from Arduino")
   except:
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Error reading data from Arduino")
   finally:
      return lTemp + " " + lHumid

def get_status():
   global lightStatus
   global manualOperation
   status = ""
   if ( lightStatus ):
      status = status + "on "
   else:
      status = status + "off "
   if ( manualOperation ):
      status = status + "manual "
   else:
      status = status + "automatic "
   status = status + read_local_data()
   return status

def turn_light_on(lightPins):
   global lightStatus
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light on!")
   for pin in lightPins:
      GPIO.output(pin, True)
   lightStatus = True

def turn_light_off(lightPins):
   global lightStatus
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light off!")
   for pin in lightPins:
      GPIO.output(pin, False)
   lightStatus = False

def init_gpio(pinList):
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Seting up pin!")
   GPIO.setwarnings(False)
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(pinList, GPIO.OUT)
   GPIO.output(pinList, False)

def get_image(data):
   if ( int(data) < len(cameraURL) ):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Loading snapshot from camera " + data)
      resource = urllib.urlopen(cameraURL[int(data)-1])
      image = resource.read()
   else:
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Camera URL not available (" + data + ")")
      image = ""
   return image

def light_control():
   global manualOperation
   global lightStatus
   global arduinoIP
   global location
   global sun

   #Load Arduino IP address
   load_arduino_ip()

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Sensor Control!")
   
   #Keep it running forever
   while True:
      #Get next Sunset time
      location.date = datetime.utcnow()
      sun.compute(location)
      
      #If next sunset is going to happens in next day it means that it is night
      if ( datetime.now().date() < ephem.localtime(location.next_setting(sun)).date() ):
         if ( not manualOperation ):
            if (not lightStatus):
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Good night... Turns light on!")
               turn_light_on(lightPins)

      #If next sun rising is going to happens in current dayit meand that is is time to turn light off
      elif ( datetime.now().date() == ephem.localtime(location.next_rising(sun)).date() ):
         if ( not manualOperation ):
            if (lightStatus):
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Sleep time... Turns light off!")
               turn_light_off(lightPins)

      #If code reach this elif it means that it is day light, so turn light off anyway
      else:
         if (lightStatus):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Day light... Turns light off anyway!")
            turn_light_off(lightPins)
         manualOperation = False

      #Just wait a while before start next loop iteration
      time.sleep(10)

def light_server():
   global lightStatus
   global manualOperation
   
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Network Server")

   MSGLEN = 178

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

   #Load CCTV cameras URL
   load_camera_url()

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Waiting for connection...")

   while True:
      try:
         #Establish connection with client.
         c, addr = s.accept()
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Got connection from " + str(addr))
         msg = ''
      
         while len(msg) < MSGLEN:
            chunk = c.recv(MSGLEN-len(msg))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
         msg = decrypter.Decrypt(msg)
         logging.info("Received: " + msg)
         if ( msg == "status.all" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Full status requested")
            status = get_status()
            logging.info("Send: " + status)
            c.send(crypter.Encrypt(status))
            logging.info("Message sent!")
         elif ( msg == "light.on" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turn light on request")
            turn_light_on(lightPins)
            manualOperation = True
            timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
            c.send(crypter.Encrypt(get_status()))
         elif ( msg == "light.off" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turn light off request")
            turn_light_off(lightPins)
            manualOperation = True
            c.send(crypter.Encrypt(get_status()))
         elif ( msg == "set.manual" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation manual")
            manualOperation = True
            c.send(crypter.Encrypt(get_status()))
         elif ( msg == "set.automatic" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation automatic")
            manualOperation = False
            c.send(crypter.Encrypt(get_status()))
         elif re.match('^gate.open\|.+',msg) is not None:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate Opening request")
            passcode = msg.split('|')[1]
            rcvd_hash = signer.Sign(passcode)
            if (pass_phrase == rcvd_hash):
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Signature check is ok")
               gate_opener(gatePin)
               c.send(crypter.Encrypt('ok'))
            else:
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Signature check fail")
               c.send(crypter.Encrypt('fail'))
         elif re.match('^imageRequest.+',msg) is not None:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Camera image request")
            image = get_image(msg[-1])
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Image size = " + str(len(image)))
            c.send(struct.pack("!i",len(image))+image)
            time.sleep(1)
         else:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Request not valid")
            c.send(crypter.Encrypt('fail'))
      except:
         logging.info(traceback.format_exc())
         c.close()
         continue
      #Close the connection
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Connection closed!")
      c.close()

def main():

   global logFile

   parser = OptionParser()
   parser.add_option("-l", "--log", dest="logFileName",
                  help="write report to log logFile", metavar="logFile")

   (options, args) = parser.parse_args()

   logging.basicConfig(filename=options.logFileName,level=logging.INFO)

   #Log start
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Control threads!")

   #Initialize pin
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Setup GPIO Pins")
   init_gpio(lightPins)
   init_gpio((gatePin))

   #Start light control thread
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Sensor Thread")
   p1 = threading.Thread(target=light_control, args=[])
   p1.start()

   #start network process
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Control Network Server")
   p2 = threading.Thread(target=light_server, args=[])
   p2.start()
   
   while True:
      time.sleep(1000)

   GPIO.cleanup()

if __name__ == '__main__':
   main()

