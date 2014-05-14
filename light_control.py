#!/usr/bin/python
# -*- coding: utf-8 -*-

#Import needed libs
import thread
import threading
import datetime
import time
import sys
import subprocess
import signal
import socket
import traceback
import re
from subprocess import Popen, PIPE, call
from time import localtime, strftime
from datetime import timedelta
from keyczar import keyczar
from keyczar import keyczart
from keyczar.errors import KeyczarError

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
#GPIO pin to open gate
gatePin = "26"
#Gate signal lenght
gateSignalLenght = 0.5
#Local data output file
localDataFile = "/media/2/log/local_data.log"
#i2cget command full path
i2cget = "/usr/sbin/i2cget"
#gpio command full path
gpio = "/usr/local/bin/gpio"
#Server port number
portNum = 4055
#Server IP address
ipAddr = "192.168.0.2"

#Cyphering paths
PUB_KEY = "/home/pi/.keys/public"
PVT_KEY = "/home/pi/.keys/private"
SGN_KEY = "/home/pi/.keys/signkeys"
PASS_PHRASE = "VHXxsMvdwrwoml7r44pxzE3iUuI"

#Function to call turn_light_off by alarm signal
def handler_light_off(signum, frame):
   global manualOperation
   if ( not manualOperation ):
      turn_light_off(lightPin)
   signal.alarm(0)

def gate_opener(gatePin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate opened!!!"
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
   with open(localDataFile, "rb") as f:
      for last in f: pass
   f.close()
   last = last.rstrip().split()
   return last[2] + " " + last[3]

def turn_light_on(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light on!"
   subprocess.call([gpio,"-g","write",lightPin,"1"])

def turn_light_off(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light off!"
   subprocess.call([gpio,"-g","write",lightPin,"0"])

def init_gpio(lightPin,gatePin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Seting up pin!"
   for pin in (lightPin,gatePin):
      subprocess.call([gpio,"-g","mode",pin,"out"])
      subprocess.call([gpio,"-g","write",pin,"0"])

def light_control():
   global manualOperation
   global lightStatus

   #Keep it running forever
   while True:
      #Read ADC light meter value and test
      if ( int(read_light_meter(devAddr,adcPin),16) <= int(minLightLevel,16) and not lightStatus ):
         #If light level lower than trigger and light off, turn light on
         turn_light_on(lightPin)
         #Set alarm to turn light off
         timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
         print strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds"
         signal.alarm(int(timeFrame.total_seconds()))
         #Set light status true (on)
         lightStatus = True
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(600) #sleep 10 minutes

      if ( int(read_light_meter(devAddr,adcPin),16) > int(minLightLevel,16) ):
         #If light level bigger than trigger and light on, turn light off
         turn_light_off(lightPin)
         #Set light status false (off)
         lightStatus = False
         #Set manual operation fasle (no)
         manualOperation = False
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(600) #sleep 10 minutes

      #Just wait a while before start next loop iteration
      time.sleep(10)

def light_server():
   global lightStatus
   global manualOperation
   
   MSGLEN = 690

   print "Loading Private/Public keys.."
   crypter = keyczar.Encrypter.Read(PUB_KEY)
   decrypter = keyczar.Crypter.Read(PVT_KEY)
   signer = keyczar.UnversionedSigner.Read(SGN_KEY)

   print "starting server..."
   #Create a socket object
   s = socket.socket()
   #Get local machine name
   #host = socket.gethostname()
   host = socket.gethostbyname(ipAddr)
   #Bind to the port
   s.bind((host, portNum))

   #Now wait for client connection.
   s.listen(2)

   print "Waiting for connection..."

   while True:
      try:
         #Establish connection with client.
         c, addr = s.accept()
         print strftime("%d-%m-%Y %H:%M", localtime()) , 'Got connection from', addr
         msg = ''
      
         while len(msg) < MSGLEN:
            chunk = c.recv(MSGLEN-len(msg))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
         msg = decrypter.Decrypt(msg)
         print "Received: " + msg
         if ( msg == "status.all" ):
            print "Full status requested"
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
            print "Send: " + status
            c.send(crypter.Encrypt(status))
            print "Message sent!"
         elif ( msg == "light.status" ):
            print "Light status request"
            if ( lightStatus ):
               status = "on "
            else:
               status = "off "
            if ( manualOperation ):
            	status = status + "manual"
            else:
            	status = status + "automatic"
            c.send(crypter.Encrypt(status))
         elif ( msg == "light.on" ):
            print "Turn light on request"
            turn_light_on(lightPin)
            lightStatus = True
            manualOperation = True
            c.send(crypter.Encrypt('on'))
         elif ( msg == "light.off" ):
            print "Turn light off request"
            turn_light_off(lightPin)
            lightStatus = False
            manualOperation = False
            c.send(crypter.Encrypt('off'))
         elif ( msg == "set.manual" ):
            print "Set operation manual"
            manualOperation = True
            signal.alarm(0)
            c.send(crypter.Encrypt('ok'))
         elif ( msg == "set.automatic" ):
            print "Set operation automatic"
            manualOperation = False
            timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
            print strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + str(int(timeFrame.total_seconds())) + " seconds"
            signal.alarm(int(timeFrame.total_seconds()))
            c.send(crypter.Encrypt('ok'))
         elif re.match('^gate.open\|.+',msg) is not None:
            print "Gate Opening request"
            passcode = msg.split('|')[1]
            HASH = signer.Sign(passcode) 
            if ( PASS_PHRASE == HASH):
            	print "Signature check is ok"
            	gate_opener(gatePin)
            	c.send(crypter.Encrypt('ok'))
            else:
            	print "Signature check fail"
            	c.send(crypter.Encrypt('fail'))
         else:
            print "Request not valid"
            c.send(crypter.Encrypt('fail'))
      except:
         print traceback.format_exc()
         c.close()
         continue
      #Close the connection
      print "Connection closed!"
      c.close()

def main():
   #Set SIGALARM response
   signal.signal(signal.SIGALRM, handler_light_off)

   #Initialize pin
   init_gpio(lightPin,gatePin)

   #Start light control thread
   p1 = threading.Thread(target=light_control, args=[])
   p1.start()

   #start network process
   p2 = threading.Thread(target=light_server, args=[])
   p2.start()
   
   while True:
   	 time.sleep(5)

if __name__ == '__main__':
   main()

