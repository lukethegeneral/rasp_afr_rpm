import busio
import digitalio
import board
from board import SCL, SDA
import RPi.GPIO as GPIO
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from csv import writer
from time import sleep, strftime, time
from datetime import datetime
from threading import Thread
import signal

global afr_value
global afr_voltage
afr_value = 0.00
afr_voltage = 0.00

global disp

global rpm_value
rpm_value = 0.00
GPIO_PIN_RPM = 17

class OledDisplay:
    def __init__(self):
        self._running = True

    def terminate(self):  
        self._running = False  

    def run(self):
        # Clear display.
        disp.fill(0)
        disp.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        width = disp.width
        height = disp.height
        image = Image.new('1', (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width,height), outline=0, fill=0)

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = -2
        top = padding
        bottom = height-padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 0

        # Load default font.
        font = ImageFont.load_default()

        # Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
        # Some other nice fonts to try: http://www.dafont.com/bitmap.php
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 8)

        text = "AFR"
        draw.text((0, 0), text, font=font, fill=255)

        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 48)

        while self._running:
            # Draw a black filled box to clear the image.
            draw.rectangle((5,10,width,height), outline=0, fill=0)
            # Display image.
            draw.text((x+5, top+8), str(afr_value), font=font, fill=255)
            disp.image(image)
            disp.show()
            sleep(0.01)

class WriteToFile:
    def __init__(self):
        self._running = True

    def terminate(self):  
        self._running = False  

    def run(self):
        timestamp = datetime.now()
        delay = 100000 
        with open('/home/pi/repo/mgb/data/data_' + timestamp.strftime("%Y%m%d_%H%M%S") + '.csv', 'w', newline='') as f:
            data_writer = writer(f)
            data_writer.writerow(['AFR','RPM','Timestamp'])
            while self._running:
                # Write to file
                data_list = []
                data_list.append(afr_value) 
                data_list.append(rpm_value) 
                data_list.append(datetime.now()) 
                dt = data_list[-1] - timestamp
                if dt.microseconds > delay:
                    data_writer.writerow(data_list)
                    timestamp = datetime.now()
                sleep(0.01)

class ReadRpm:
    def __init__(self, gpio, engine_cylinders, engine_strokes, interval):
        self.gpio               = gpio
        self.engine_cylinders   = engine_cylinders
        self.engine_strokes     = engine_strokes
        self.interval           = interval
        self.rpm_pulses         = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(gpio, GPIO.FALLING, callback=self._my_callback)

    def _my_callback(self, channel):
        self.rpm_pulses += 1
        print("Falling edge detected on 17. Pulses= " + str(self.rpm_pulses))

    def RPM(self):
        RPM = 0.0
        #     int RPM = int(RPMpulses * (60000.0 / float(refreshInterval)) * engineCycles / engineCylinders / 2.0 ); // calculate RPM
        RPM = self.rpm_pulses * self.engine_cylinders / self.engine_strokes / 2.0
        self.rpm_pulses = 0
        return RPM

    def __str__(self):
        return "GPIO= " + str(self.gpio) + " No cylinders= " + str(self.engine_cylinders) + " No strokes= " + str(self.engine_strokes) + " Interval= " + str(self.interval)


class GracefulKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        WriteToFile.terminate() 
        self.kill_now = True
        print('Write to file stopped')


def stop_check():
    if (afr_voltage == 0):
        WriteToFile.terminate() 
        print('Write to file stopped')

def x_afr(V):
    a = 0.12
    b = 0.70
    l = a*V + b
    afr = l * 14.7
    return afr 

# create the spi bus
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# create the cs (chip select)
cs = digitalio.DigitalInOut(board.D5)

# create the mcp object
mcp = MCP.MCP3008(spi, cs, 5.0)

# create an analog input channel on pin 0
channel = AnalogIn(mcp, MCP.P0)

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Note you can change the I2C address by passing an i2c_address parameter like:
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

#Create Class
OledDisplay = OledDisplay()
#Create Thread
OledDisplayThread = Thread(target=OledDisplay.run, daemon=True)
#StartThread
OledDisplayThread.start()

#Create Class
WriteToFile = WriteToFile()
#Create Thread
WriteToFileThread = Thread(target=WriteToFile.run, daemon=True)
#StartThread
WriteToFileThread.start()

read_rpm = ReadRpm(GPIO_PIN_RPM, 4, 4, 1000)
print(read_rpm)

killer = GracefulKiller()

try:
    while not killer.kill_now:
        # Calculate AFR
        afr_value = round(x_afr(channel.voltage), 2)
        afr_voltage = round(channel.voltage, 2)

        print('AFR: [' + str(afr_value) + '] Voltage: [' + str(afr_voltage)  + ']')

        rpm_value = round(read_rpm.RPM(), 2) 
        rpm = GPIO.input(GPIO_PIN_RPM)
        print("RPM: " + str(rpm) + " [" + str(rpm_value) + "]")

        sleep(0.002)

        #stop_check()

except KeyboardInterrupt:
    print('Finished')

finally:
    GPIO.cleanup()
