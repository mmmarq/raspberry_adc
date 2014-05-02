#!/usr/bin/python
# -*- coding: utf-8 -*-

manualOperation = False

#Import needed libs
import thread
import threading
import datetime
import time
import sys
import subprocess
from subprocess import Popen, PIPE
from time import localtime, strftime

def read_light_meter(device,channel):
   #Set default ADC channel
   p1 = Popen(["/usr/sbin/i2cget","-y","1",device,channel], stdout=PIPE)
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
   p1 = Popen(["/usr/local/bin/gpio","-g","write",lightPin,"1"], stdout=PIPE)
   p1.stdout.close()

def turn_light_off(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Turning light off!"
   p1 = Popen(["/usr/local/bin/gpio","-g","write",lightPin,"0"], stdout=PIPE)
   p1.stdout.close()

def init_gpio(lightPin):
   print strftime("%d-%m-%Y %H:%M", localtime()) + " - Seting up pin!"
   p1 = Popen(["/usr/local/bin/gpio","-g","mode",lightPin,"out"], stdout=PIPE)
   p1.stdout.close()
   p1 = Popen(["/usr/local/bin/gpio","-g","write",lightPin,"0"], stdout=PIPE)
   p1.stdout.close()

def main():
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

   #Keep it running forever
   while True:
      #Read ADC light meter value and test
      if ( int(read_light_meter(devAddr,adcPin),16) <= int(minLightLevel,16) and not lightStatus ):
         #If light level lower than trigger and light off, turn light on
         turn_light_on(lightPin)
         #Set light status true
         lightStatus = True
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(900) #sleep 15 minutes

      if ( int(read_light_meter(devAddr,adcPin),16) > int(minLightLevel,16) and lightStatus ):
         #If light level bigger than trigger and light on, turn light off
         turn_light_off(lightPin)
         #Set light status true
         lightStatus = False
         #Since adc return value can vary easily, wait little more time to next loop
         time.sleep(900) #sleep 15 minutes

      #Just wait a while before start next loop iteration
      time.sleep(5)


if __name__ == '__main__':
   main()

