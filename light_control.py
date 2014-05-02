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
from subprocess import Popen, PIPE, call
from time import localtime, strftime
from datetime import timedelta

#Define if light is in manual operation
manualOperation = False
#I2C device address
devAddr = "0x48"
#I2C ADC channel
adcPin = "0x03"
#Light level to trigger light_on
minLightLevel = "0x0A"
#GPIO pint to control light relay
lightPin = "25"
#Control light status
lightStatus = False

#Function to call turn_light_off by alarm signal
def handler_light_off(signum, frame):
   global manualOperation
   global lightPin
   if ( not manualOperation ):
      turn_light_off(lightPin)
   signal.alarm(0)

def read_light_meter(device,channel):
   #Set default ADC channel
   subprocess.call(["/usr/sbin/i2cget","-y","1",device,channel])
   #Read ADC twice to get right value
   subprocess.call(["/usr/sbin/i2cget","-y","1",device])
   p1 = Popen(["/usr/sbin/i2cget","-y","1",device], stdout=PIPE)
   #Store ADC value
   output = p1.communicate()[0]
   p1.stdout.close()
   return output

def turn_light_on(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light on!"
   subprocess.call(["/usr/local/bin/gpio","-g","write",lightPin,"1"])

def turn_light_off(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light off!"
   subprocess.call(["/usr/local/bin/gpio","-g","write",lightPin,"0"])

def init_gpio(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Seting up pin!"
   subprocess.call(["/usr/local/bin/gpio","-g","mode",lightPin,"out"])
   subprocess.call(["/usr/local/bin/gpio","-g","write",lightPin,"0"])

def light_control():
   #Define if light is in manual operation
   global manualOperation
   #I2C device address
   global devAddr
   #I2C ADC channel
   global adcPin
   #Light level to trigger light_on
   global minLightLevel
   #GPIO pint to control light relay
   global lightPin
   #Control light status
   global lightStatus

   #Initialize pin
   init_gpio(lightPin)
   
   #Set SIGALARM response
   signal.signal(signal.SIGALRM, handler_light_off)

   #Keep it running forever
   while True:
      #Read ADC light meter value and test
      if ( int(read_light_meter(devAddr,adcPin),16) <= int(minLightLevel,16) and not lightStatus ):
         #If light level lower than trigger and light off, turn light on
         turn_light_on(lightPin)
         #Set alarm to turn light off
         timeFrame = timedelta(hours=(23 - int(strftime("%H", localtime()))),minutes=(59 - int(strftime("%M", localtime()))), seconds=(59 - int(strftime("%S", localtime()))))
         signal.alarm(timeFrame.total_seconds())
         print strftime("%d-%m-%Y %H:%M", localtime()) + " - Light is going to off in " + timeFrame.total_seconds() + " seconds"
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
      time.sleep(5)

def light_server():
   MSGLEN = 1
   print "starting server..."
   #Create a socket object
   s = socket.socket()
   #Get local machine name
   host = socket.gethostname()
   print host
   #Reserve a port for your service.
   port = 12345
   #Bind to the port
   #s.bind((host, port))
   s.bind(("127.0.0.1", port))

   #Now wait for client connection.
   s.listen(2)
   
   while True:
   	 try:
         #Establish connection with client.
         c, addr = s.accept()
         print strftime("%d-%m-%Y %H:%M", localtime()) , 'Got connection from', addr
         #c.send('Thank you for connecting')
         msg = ''
      
         while len(msg) < MSGLEN:
               chunk = c.recv(MSGLEN-len(msg))
               if chunk == '':
                   raise RuntimeError("socket connection broken")
               msg = msg + chunk
         print "Receive: " + msg
         if ( msg == "A" ):
            c.send('Light Status = off')
         else:
            c.send('Commando desconhecido')
      except:
         c.close()
      #Close the connection
      c.close()

def main():
   #Start light control thread
   #p1 = threading.Thread(target=light_control, args=())
   #p1.start()
   #start network process
   p2 = threading.Thread(target=light_server, args=[])
   p2.start()
   
   while True:
   	 time.sleep(5)

if __name__ == '__main__':
   main()

