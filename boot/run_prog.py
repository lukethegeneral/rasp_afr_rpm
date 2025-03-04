#!/bin/python
import RPi.GPIO as GPIO
from time import sleep
import os
import subprocess

GPIO_BUTTON = 27
GPIO_LED = 16
global counter
counter = 0

def my_callback(channel):
    global counter
    global proc
    if GPIO.input(GPIO_BUTTON) == GPIO.HIGH:
        counter += 1
        # Run process
        if (counter % 2 != 0):
            print("counter: " + str(counter))
            cmd = "/home/pi/repo/mgb/programs/prog.py"
            proc = subprocess.Popen(['python', cmd])
            GPIO.output(GPIO_LED, GPIO.HIGH)
        # Terminate process
        else:
            print("counter: " + str(counter) + " terminate")
            proc.terminate() 
            GPIO.output(GPIO_LED, GPIO.LOW)
            #proc.kill()
    sleep(1)


try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(GPIO_BUTTON, GPIO.FALLING, callback=my_callback)

    GPIO.setup(GPIO_LED, GPIO.OUT)

    while True: pass 
except:
    GPIO.cleanup()
#finally:
#    GPIO.cleanup()

