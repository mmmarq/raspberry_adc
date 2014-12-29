#!/usr/bin/python
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import time

_PIN = 25

#print GPIO.RPI_REVISION

GPIO.setmode(GPIO.BCM)
GPIO.setup(_PIN, GPIO.OUT)
GPIO.output(_PIN, True)

time.sleep(5)

GPIO.output(_PIN, False)

GPIO.cleanup()
