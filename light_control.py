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
from os import listdir
from os.path import isfile, join

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
portNum = 4055
#Server IP address
ipAddr = "192.168.0.2"
#Red led pin
redLed = "17"
#Green led pin
greenLed = "18"
#Blue led pin
blueLed = "27"
#Message storage folder
messageFolder = "messages"
#URL to convert file
baseUrl="http://translate.google.com/translate_tts?tl=pt&q="
#Audio file prefix
filePrefix="audio_"
#Audio file prefix
fileSufix=".mp3"

#Cyphering paths
PUB_KEY = "/home/pi/.keys/public"
PVT_KEY = "/home/pi/.keys/private"
SGN_KEY = "/home/pi/.keys/signkeys"
PASS_PHRASE = "VHXxsMvdwrwoml7r44pxzE3iUuI"

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

#Text Message parser
def parse_phrase(phrase):
   temp = phrase.split(" ")
   result = []
   out = ""
   
   for text in temp:
      if ( (len(out) + len(text)) < 99 ):
         out = out + " " + text
      else:
         result.extend([out])
         out = text
   result.extend([out])
   return result

#Convert text file to audio file
def tts(text_tokens,count):
   fileCount = count
   audioFiles = []
   for token in text_tokens:
      URL = baseUrl + remove_space(token)
      command = ["curl",URL,"--user-agent","\"Mozilla/5.0\"","-o",os.path.join(messageFolder,filePrefix+str(fileCount)+fileSufix)]
      subprocess.call(command)
      audioFiles.extend([os.path.join(messageFolder,filePrefix+str(fileCount)+fileSufix)])
      fileCount = fileCount + 1
   return audioFiles

def remove_space(text):
   return text.replace(" ", "%20")

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

def read_local_data():
   localDataFile = "/media/2/log/"+strftime("%Y-%m_local_data.log", localtime())
   with open(localDataFile, "rb") as f:
      for last in f: pass
   f.close()
   last = last.rstrip().split()
   return last[2] + " " + last[3]

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
   for pin in (lightPin,gatePin,redLed,greenLed,blueLed):
      subprocess.call([gpio,"-g","mode",pin,"out"])
      subprocess.call([gpio,"-g","write",pin,"0"])

def light_control():
   global manualOperation
   global lightStatus
   global mySleep

   #Variable to make this thread turn light on automaticaly only next day
   mySleep = False

   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Sensor Control!")

   #Keep it running forever
   while True:
      #Read ADC light meter value and test
      #only if there is no light enough outsidec(check minLightLevel)
      #light is not alread on (lightStatus)
      #system is not in manual operation (manualOperation)
      #light meter is not in sleep mode (mySleep)
      if ( int(read_light_meter(devAddr,adcPin),16) <= int(minLightLevel,16) and not lightStatus and not manualOperation and not mySleep ):
         #If light level lower than trigger and light off, turn light on
         turn_light_on(lightPin)
         #Set alarm to turn light off
         timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
         signal.alarm(int(timeFrame.total_seconds()))
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

   #Create a socket object
   s = socket.socket()
   #Get local machine name
   #host = socket.gethostbyname(ipAddr)
   host = socket.gethostbyname("localhost")
   #Bind to the port
   s.bind((host, portNum))

   #Now wait for client connection.
   s.listen(2)

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
            turn_light_on(lightPin)
            manualOperation = True
            mySleep = True
            timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
            signal.alarm(int(timeFrame.total_seconds()))
            c.send(crypter.Encrypt(get_status()))
         elif ( msg == "light.off" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Turn light off request")
            turn_light_off(lightPin)
            manualOperation = True
            mySleep = True
            signal.alarm(0)
            c.send(crypter.Encrypt(get_status()))
         elif ( msg == "set.manual" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation manual")
            manualOperation = True
            signal.alarm(0)
            c.send(crypter.Encrypt(get_status()))
         elif ( msg == "set.automatic" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Set operation automatic")
            manualOperation = False
            mySleep = False
            if ( lightStatus ):
               timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds")
               signal.alarm(int(timeFrame.total_seconds()))
            c.send(crypter.Encrypt(get_status()))
         elif re.match('^gate.open\|.+',msg) is not None:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate Opening request")
            passcode = msg.split('|')[1]
            HASH = signer.Sign(passcode) 
            if ( PASS_PHRASE == HASH):
            	logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Signature check is ok")
            	gate_opener(gatePin)
            	c.send(crypter.Encrypt('ok'))
            else:
            	logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Signature check fail")
            	c.send(crypter.Encrypt('fail'))
         elif re.match('^text.message\|.+',msg) is not None:
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Incomming message")
            message = msg.split('|')[1]
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Message: " + message)
            if not os.path.exists(messageFolder):
               logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - " + messageFolder + " folder does not exist, creating...")
               os.makedirs(messageFolder)
            fileName = strftime("%Y_%m_%d_%H_%M_%S.txt", localtime())
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Creating message file " + fileName)
            text_file = open(os.path.join(messageFolder,fileName), "w")
            text_file.write("%s" % message)
            text_file.close()
            c.send(crypter.Encrypt('ok'))
         elif ( msg == "read.message" ):
            logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Message reading request")
            message_thread = threading.Thread(target=messageReader, args=[])
            message_thread.start()
            c.send(crypter.Encrypt('ok'))
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

def message_checker():
   global redLed
   global greenLed
   global blueLed
   global messageFolder

   #Led status control
   ledStatus = 0
   
   if not os.path.exists(messageFolder):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - " + messageFolder + " folder does not exist, creating...")
      os.makedirs(messageFolder)

   while True:
      #List files inside message folder
      onlyfiles = [ f for f in listdir(messageFolder) if isfile(join(messageFolder,f)) ]
      if ( len(onlyfiles) > 0 ):
         if ( ledStatus == 0 ):
         	  ledStatus = 1
         else:
         	  ledStatus = 0
         subprocess.call([gpio,"-g","write",greenLed,str(ledStatus)])
      else:
         ledStatus = 0
         subprocess.call([gpio,"-g","write",greenLed,str(ledStatus)])
      time.sleep(1)

def messageReader():
   global messageFolder
   audioFiles = []
   fileCount = 0
   
   if not os.path.exists(messageFolder):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - " + messageFolder + " folder does not exist, creating...")
      os.makedirs(messageFolder)

   #List files inside message folder
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Checking new messages")
   onlyfiles = [ f for f in listdir(messageFolder) if isfile(join(messageFolder,f)) ]
   if ( len(onlyfiles) > 0 ):
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - " + str(len(onlyfiles)) + " new messages found")
      for files in onlyfiles:
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Reading file " + files)
         with open(os.path.join(messageFolder,files)) as f:
            content = f.readlines()
         for text in content:
            audioFiles.extend(tts(parse_phrase(text),fileCount))
            fileCount = len(audioFiles)
         fileCount = 0
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Playing audio files")
         command = ["/usr/bin/mplayer","-ao","alsa","-really-quiet","-noconsolecontrols"]
         command.extend(audioFiles)
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Command: ")
         logging.info(command)
         subprocess.call(command);
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Removing audio files") 
         for audio in audioFiles:
            os.remove(audio)
         logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Removing message file") 
         os.remove(os.path.join(messageFolder,files))
         audioFiles = []
   else:
      logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - No new message files found")
      audioFiles.extend(tts(parse_phrase("Não existem mensagens novas"),0))
      command = ["/usr/bin/mplayer","-ao","alsa","-really-quiet","-noconsolecontrols"]
      command.extend(audioFiles)
      subprocess.call(command);
      for files in audioFiles:
         os.remove(files)
      audioFiles = []
      fileCount = 0

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
   #logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Sensor Thread")
   #p1 = threading.Thread(target=light_control, args=[])
   #p1.start()

   #start network process
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Light Control Network Server")
   p2 = threading.Thread(target=light_server, args=[])
   p2.start()
   
   #start message checker process
   logging.info(strftime("%d-%m-%Y %H:%M", localtime()) + " - Starting Message Checker Thread")
   p3 = threading.Thread(target=message_checker, args=[])
   p3.start()
   
   while True:
   	 time.sleep(5)

if __name__ == '__main__':
   main()

