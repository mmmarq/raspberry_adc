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
import re
import os
from subprocess import Popen, PIPE, call
from time import localtime, strftime
from datetime import timedelta
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError
from optparse import OptionParser

#Log file name
logFile = ""
#Define if light is in manual operation
manualOperation = False
#I2C device address
devAddr = "0x48"
#I2C ADC channel
adcPin = "0x03"
#Light level to trigger light_on
minLightLevel = "0x70"
#GPIO pin to control light relay
lightPin = "25"
#Control light status
lightStatus = False
#Control if light meter should sleep
mySleep = False
#GPIO pin to open gate
gatePin = "26"
#Gate signal lenght
gateSignalLenght = 0.5
#i2cget command full path
i2cget = "/usr/sbin/i2cget"
#gpio command full path
gpio = "/usr/local/bin/gpio"
#Server port number
PORTNUM = 4055
#Server IP address
HOST = "mmmarq.dnsdynamic.net"
#Config file folder
configFileFolder = "/media/2/log"
#Config file name
configFileName = "light_control.cfg"

#Cyphering paths
PUB_KEY = "/home/pi/.keys/public"
PVT_KEY = "/home/pi/.keys/private"
SGN_KEY = "/home/pi/.keys/signkeys"
PASS_PHRASE = "/home/pi/.keys/passphrase"
MASTER_PHRASE = "/home/pi/.keys/masterphrase"
MASTER_PUB_KEY="/home/pi/.keys/master_public"

# Test Environment
#PUB_KEY = "/Users/wmm125/.ssh/raspberry/keys/public"
#PVT_KEY = "/Users/wmm125/.ssh/raspberry/keys/private"
#SGN_KEY = "/Users/wmm125/.ssh/raspberry/keys/signkeys"
#PASS_PHRASE = "/Users/wmm125/.ssh/raspberry/keys/passphrase"
#MASTER_PHRASE = "/Users/wmm125/.ssh/raspberry/keys/masterphrase"
#MASTER_PUB_KEY = "/Users/wmm125/.ssh/raspberry/keys/master_public"

#Function to call turn_light_off by alarm signal
def handler_light_off(signum, frame):
   global manualOperation
   global lightStatus
   global mySleep
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Its time to turn lights off... See you tomorrow!")
   turn_light_off(lightPin)
   lightStatus = False
   manualOperation = False   
   #Set sleep true in order to trigger light on only next night
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light level checking is going to sleep until morning.")
   mySleep = True
   signal.alarm(0)

def gate_opener(gatePin):
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate opened!!!")
   subprocess.call([gpio,"-g","write",gatePin,"1"])
   time.sleep(gateSignalLenght)
   subprocess.call([gpio,"-g","write",gatePin,"0"])   

def read_light_meter(device,channel):
   #Set default ADC channel
   p1 = Popen([i2cget,"-y","1",device,channel], stdout=PIPE)
   p1.stdout.close()
   #Read ADC twice to get right value
   p1 = Popen([i2cget,"-y","1",device], stdout=PIPE)
   p1.stdout.close()
   p1 = Popen([i2cget,"-y","1",device], stdout=PIPE)
   #Store ADC value
   output = p1.communicate()[0]
   p1.stdout.close()
   return output

def read_pass_phrase():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading pass phrase file")
   if not os.path.isfile(PASS_PHRASE):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Pass phrase file not found")
      return ""
   with open(PASS_PHRASE) as f:
      content = f.readline()
      return content.strip()

def read_master_phrase():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading master phrase file")
   if not os.path.isfile(MASTER_PHRASE):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Master phrase file not found")
      return ""
   with open(MASTER_PHRASE) as f:
      content = f.readline()
      return content.strip()

def read_status():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading configuration file")
   if not os.path.exists(configFileFolder):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - " + configFileFolder + " folder does not exist, creating new one")
      os.makedirs(configFileFolder)
   if not os.path.isfile(os.path.join(configFileFolder,configFileName)):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Creating config file with current status")
      text_file = open(os.path.join(configFileFolder,configFileName), "w")
      status = get_status()
      text_file.write("%s" % status)
      text_file.close()
      return status
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading config file content")
   with open(os.path.join(configFileFolder,configFileName)) as f:
      content = f.readline()
      return content

def save_status():
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Saving configuration file")
   if not os.path.exists(configFileFolder):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - " + configFileFolder + " folder does not exist, creating new one")
      os.makedirs(configFileFolder)
   if os.path.isfile(os.path.join(configFileFolder,configFileName)):
      os.remove(os.path.join(configFileFolder,configFileName))
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Creating config file with current status")
   text_file = open(os.path.join(configFileFolder,configFileName), "w")
   status = get_status()
   text_file.write("%s" % status)
   text_file.close()

def read_local_data():
   ldata = ()
   EXE = "sudo /media/2/code/raspberry_lcd/dht11"
   while True:
     try:
       #Read sensor data twice to refresh data
       output=subprocess.check_output(EXE, shell=True)
       output=subprocess.check_output(EXE, shell=True)
       #Parse local data
       ldata = output.split()
       #Stop loop
       break
     except:
       #If sensor reading fail, try again
       continue
   return ldata[1] + " " + ldata[0]

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

def turn_light_on(lightPin):
   global lightStatus
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light on!")
   subprocess.call([gpio,"-g","write",lightPin,"1"])
   lightStatus = True

def turn_light_off(lightPin):
   global lightStatus
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light off!")
   subprocess.call([gpio,"-g","write",lightPin,"0"])
   lightStatus = False

def init_gpio(lightPin,gatePin):
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Seting up pin!")
   for pin in (lightPin,gatePin):
      subprocess.call([gpio,"-g","mode",pin,"out"])
      subprocess.call([gpio,"-g","write",pin,"0"])

def light_control():
   global manualOperation
   global lightStatus
   global mySleep

   #Variable to make this thread turn light on automatically only next day
   mySleep = False

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Sensor Control!")
   
   #Read previous status
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading configuration file")
   status = read_status()
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Configuration file content: " + status)
   if ( status.split(' ')[0] == "on" ):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set light on")
      lightStatus = True
      turn_light_on(lightPin)
      timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
      signal.alarm(int(timeFrame.total_seconds()))
   else:
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set light off")
      lightStatus = False
      turn_light_off(lightPin)
      signal.alarm(0)
   if ( status.split(' ')[1] == "manual" ):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation manual")
      manualOperation = True
   else:
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation automatic")
      manualOperation = False

   #Keep it running forever
   while True:
      #Read ADC light meter value and test
      #only if there is no light enough outside(check minLightLevel)
      #light is not already on (lightStatus)
      #system is not in manual operation (manualOperation)
      #light meter is not in sleep mode (mySleep)
      if ( int(read_light_meter(devAddr,adcPin),16) <= int(minLightLevel,16) and not lightStatus and not manualOperation and not mySleep ):
         #If light level lower than trigger and light off, turn light on
         turn_light_on(lightPin)
         #Set alarm to turn light off
         timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
         signal.alarm(int(timeFrame.total_seconds()))
         #Save config file
         save_status()
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(600) #sleep 10 minutes
      
      #Check if there is light enough outside
      if ( int(read_light_meter(devAddr,adcPin),16) > int(minLightLevel,16) ):
         #Remove any existing alarm
         signal.alarm(0)
         #Set manual operation fasle (no)
         if ( manualOperation ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Good morning... Set manual opration false.")
            manualOperation = False
         #Set sleep false in order to enable light turn on next night
         if ( mySleep ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Good morning... Wake up light level checking.")
            mySleep = False
         
         #If ligh is on, turn light off
         if ( lightStatus ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Good morning... Turns light off!")
            #If light level bigger than trigger and light on, turn light off
            turn_light_off(lightPin)
         #Save config file
         save_status()
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(300) #sleep 10 minutes

      #Just wait a while before start next loop iteration
      time.sleep(10)

def light_server():
   global lightStatus
   global manualOperation
   global mySleep
   
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Network Server")

   MSGLEN = 690

   logging.info("Loading Private/Public keys..")
   crypter = keyczar.Encrypter.Read(PUB_KEY)
   decrypter = keyczar.Crypter.Read(PVT_KEY)
   signer = keyczar.UnversionedSigner.Read(SGN_KEY)
   master_crypter = keyczar.Encrypter.Read(MASTER_PUB_KEY)

   #Read pass_phrase
   pass_phrase = read_pass_phrase()
   master_phrase = read_master_phrase()

   #Set connection status false (not connected)
   isConnected = False

   while True:
      try:
         if isConnected == False:
            #Create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #Connect to server
            s.connect((HOST, PORTNUM))
            s.send(master_crypter.Encrypt(master_phrase))
            isConnected = True
            #Set socket timeout
            s.settimeout(2)

         #Now wait for server requests.
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Waiting for server requests...")

         msg = ''
         #Read server requests
         while len(msg) < MSGLEN:

            try:
               #chunk = s.recv(MSGLEN-len(msg))
               chunk = s.recv(2)
            #Catch socket timeout exception
            except socket.timeout:
               continue
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
         msg = decrypter.Decrypt(msg)
         logging.info("Received: " + msg)
         if ( msg == "status.all" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Full status requested")
            status = get_status()
            logging.info("Send: " + status)
            s.send(crypter.Encrypt(status))
            logging.info("Message sent!")
         elif ( msg == "light.on" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turn light on request")
            turn_light_on(lightPin)
            manualOperation = True
            mySleep = True
            timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
            signal.alarm(int(timeFrame.total_seconds()))
            save_status()
            s.send(crypter.Encrypt(get_status()))
         elif ( msg == "light.off" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turn light off request")
            turn_light_off(lightPin)
            manualOperation = True
            mySleep = True
            signal.alarm(0)
            save_status()
            s.send(crypter.Encrypt(get_status()))
         elif ( msg == "set.manual" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation manual")
            manualOperation = True
            signal.alarm(0)
            save_status()
            s.send(crypter.Encrypt(get_status()))
         elif ( msg == "set.automatic" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation automatic")
            manualOperation = False
            mySleep = False
            if ( lightStatus ):
               timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
               signal.alarm(int(timeFrame.total_seconds()))
            save_status()
            s.send(crypter.Encrypt(get_status()))
         elif re.match('^gate.open\|.+',msg) is not None:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate Opening request")
            passcode = msg.split('|')[1]
            rcvd_hash = signer.Sign(passcode)
            if (pass_phrase == rcvd_hash):
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Signature check is ok")
               gate_opener(gatePin)
               s.send(crypter.Encrypt('ok'))
            else:
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Signature check fail")
               s.send(crypter.Encrypt('fail'))
         else:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Request not valid")
            s.sendall(crypter.Encrypt('fail'))
      except:
         logging.info(traceback.format_exc())
         #Set connection false
         s.close()
         isConnected = False
         time.sleep(10)
         continue

def main():

   global logFile

   parser = OptionParser()
   parser.add_option("-l", "--log", dest="logFileName",
                  help="write report to log logFile", metavar="logFile")

   (options, args) = parser.parse_args()

   logging.basicConfig(filename=options.logFileName,level=logging.INFO)

   #Log start
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Control threads!")

   #Set SIGALARM response
   signal.signal(signal.SIGALRM, handler_light_off)

   #Initialize pin
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Setup GPIO Pins")
   init_gpio(lightPin,gatePin)

   #Start light control thread
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Sensor Thread")
   p1 = threading.Thread(target=light_control, args=[])
   p1.start()

   #start network process
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Control Network Server")
   p2 = threading.Thread(target=light_server, args=[])
   p2.start()
   
   while True:
      time.sleep(5)

if __name__ == '__main__':
   main()

