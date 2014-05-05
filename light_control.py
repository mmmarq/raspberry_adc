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
import Crypto
from Crypto.PublicKey import RSA
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
minLightLevel = "0x70"
#GPIO pin to control light relay
lightPin = "25"
#Control light status
lightStatus = False
#GPIO pin to open gate
gatePin = "26"

#Function to call turn_light_off by alarm signal
def handler_light_off(signum, frame):
   global manualOperation
   global lightPin
   if ( not manualOperation ):
      turn_light_off(lightPin)
   signal.alarm(0)

def gate_opener(gatePin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Gate opened!!!"
   subprocess.call(["/usr/local/bin/gpio","-g","write",gatePin,"1"])
   time.sleep(0.5)
   subprocess.call(["/usr/local/bin/gpio","-g","write",gatePin,"0"])   

def read_light_meter(device,channel):
   #Set default ADC channel
   p1 = Popen(["/usr/sbin/i2cget","-y","1",device,channel], stdout=PIPE)
   p1.stdout.close()
   #Read ADC twice to get right value
   p1 = Popen(["/usr/sbin/i2cget","-y","1",device], stdout=PIPE)
   p1.stdout.close()
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

def init_gpio(lightPin,gatePin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Seting up pin!"
   for pin in (lightPin,gatePin):
      subprocess.call(["/usr/local/bin/gpio","-g","mode",pin,"out"])
      subprocess.call(["/usr/local/bin/gpio","-g","write",pin,"0"])


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

   #Set SIGALARM response
   #signal.signal(signal.SIGALRM, handler_light_off)

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
   global lightPin
   global manualOperation
   global gatePin

   MSGLEN = 256
   BYTESIZE = 32

   print "starting server..."
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
   #Bind to the port
   s.bind((host, port))
   #s.bind(("127.0.0.1", port))

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
         msg = str(private_key.decrypt(msg))
         print "Received: " + msg
         if ( msg == "light.status" ):
            print "Light status request"
            if ( lightStatus ):
               c.send(public_key.encrypt('on', BYTESIZE)[0])
            else:
               c.send(public_key.encrypt('off', BYTESIZE)[0])
         elif ( msg == "light.on" ):
            print "Turn light on request"
            #turn_light_on(lightPin)
            lightStatus = True
            manualOperation = True
            c.send(public_key.encrypt('on', BYTESIZE)[0])
         elif ( msg == "light.off" ):
            print "Turn light off request"
            #turn_light_off(lightPin)
            lightStatus = False
            manualOperation = False
            c.send(public_key.encrypt('off', BYTESIZE)[0])
         elif ( msg == "gate.open" ):
            print "Gate Opening request"
            #gate_opener(gatePin)
            c.send(public_key.encrypt('ok', BYTESIZE)[0])
         else:
            print "Request not valid"
            c.send(public_key.encrypt('fail', BYTESIZE)[0])
      except Exception, e:
         print "Exception caught...: " + e.args
         c.close()
         continue
      #Close the connection
      c.close()

def main():
   global lightPin
   global gatePin

   #Set SIGALARM response
   signal.signal(signal.SIGALRM, handler_light_off)

   #Initialize pin
   init_gpio(lightPin,gatePin)

   #Start light control thread
   p1 = threading.Thread(target=light_control, args=[])
   p1.start()

   #start network process
   #p2 = threading.Thread(target=light_server, args=[])
   #p2.start()
   
   while True:
   	 time.sleep(5)

if __name__ == '__main__':
   main()

