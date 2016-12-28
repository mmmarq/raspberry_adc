/*
https://github.com/jcw/ethercard
VCC -   3.3V
GND -    GND
SCK - Pin 52
SO  - Pin 50
SI  - Pin 51
CS  - Pin 53 # Selectable with the ether.begin() function
The default CS pin defaults to 8, so you have to set it on a mega:
ether.begin(sizeof Ethernet::buffer, mymac, 53)

Hardware Connections (I2C - Arduino Mega):
 -VCC = 3.3V
 -GND = GND
 -SDA = 20
 -SCL = 21
*/

#include <dht.h>
#include <EtherCard.h>
#include <QueueArray.h>
#include <Wire.h>
#include "SparkFunHTU21D.h"
#include <SFE_BMP180.h>

static byte myip[] = { 192,168,1,100 };                  // ethernet interface static ip address
static byte gwip[] = { 192,168,1,1 };                    // gateway static ip address
static byte mymac[] = { 0x74,0x69,0x69,0x2D,0x30,0x31 }; // ethernet mac address - must be unique on your network

byte Ethernet::buffer[500];                              // tcp/ip send and receive buffer
BufferFiller bfill;
const boolean STATICIPADDRESS = false;              // set to true to disable DHCP (adjust myip/gwip values above)

// Create temperature and humidity sensor instance of the object
HTU21D tempHumSendor;
// Create pressure sensor instance of the oject
SFE_BMP180 pressureSensor;

#define ALTITUDE 660.0 // Altitude of Itapira/SP/BRZ. in meters

const byte LIGHT1STATUSPIN = 11;                    // set light 1 status pin
const byte LIGHT2STATUSPIN = 10;                    // set light 2 status pin
const byte GATESTATUSPIN = 7;                       // set gate status pin
const byte RPISTATUSPIN = 6;                        // set RasPi status pin
const byte ALARMSTATUSPIN = 2;                      // set alarm status pin

const byte RELAY1PIN = 23;                          // set light relay 1 pin
const byte RELAY2PIN = 24;                          // set light relay 2 pin

const byte GATEPIN = 25;                            // set gate opening pin

const byte LDRPIN = A0;                             // set LDR sensor pin
const int numReadings = 100;                        // amount of readings to get light level average
int averageLightLevel = 0;                          // store light level average value
QueueArray <int> readings;                          // the readings from the analog input
unsigned int totalLightLevel = 0;                   // the running total

unsigned long currTime = 0;                         // store current time in milliseconds since board is up
unsigned long prevTime = 0;                         // store last time lapse reading
float temperature = 0;                              // global temperature var
float temp1, temp2;                                 // temporary temperature var
float humidity = 0;                                 // global humidity var
float pressure = 0;                                 // global pressure var

boolean light = false;                              // set initial light status
boolean alarm = false;                              // set initial alarm status
boolean raspi = false;                              // set initial raspi status

const boolean DEBUG = true;                        // enable or disable debug messages

void setup() {
  Serial.begin(9600);                                         // set serial communication speed
  if (DEBUG) Serial.println("Starting system setup...");

  if (ether.begin(sizeof Ethernet::buffer, mymac, 53) == 0){ 
    if (DEBUG) Serial.println( "Failed to access Ethernet controller");
  }
  // if STATIC
  if (STATICIPADDRESS){
    ether.staticSetup(myip, gwip);
  }else{
    if (!ether.dhcpSetup())
      if (DEBUG) Serial.println("DHCP failed");
  }
  if (DEBUG) ether.printIp("IP:  ", ether.myip);
  if (DEBUG) ether.printIp("GW:  ", ether.gwip);  
  if (DEBUG) ether.printIp("DNS: ", ether.dnsip);  

  pinMode(LIGHT1STATUSPIN, INPUT);
  pinMode(LIGHT2STATUSPIN, INPUT);
  pinMode(GATESTATUSPIN, INPUT);
  pinMode(RPISTATUSPIN, INPUT);
  pinMode(ALARMSTATUSPIN, INPUT);

  pinMode(RELAY1PIN, OUTPUT);
  pinMode(RELAY2PIN, OUTPUT);
  pinMode(GATEPIN, OUTPUT);
  digitalWrite(RELAY1PIN, HIGH);
  digitalWrite(RELAY2PIN, HIGH);
  digitalWrite(GATEPIN,LOW);

  tempHumSendor.begin();                                      // initialize temp and humidit values
  pressureSensor.begin();                                     // initialize pressure values
  readLightStatusPin();                                       // check light status
  readAlarmStatus();                                          // initialize alarm status
  readRaspiStatus();                                          // initialize raspi status
  readLightLevel();                                           // initialize light level value
}

void loop() {
  currTime = millis();                                        // read current time in milliseconds since system is UP
  if (currTime < prevTime) currTime = prevTime;               // check for currTime overflow (after aprox. 50 days);
  if ((currTime - prevTime) >= 1000){                         // check if passed 1 sec since last data update
    readHTU21D();                                             // read weather data from sensor

    readBMP180();                                             // read pressure data from sensor
    readLightStatusPin();                                     // update light status
    temperature = (temp1 + temp2) / 2;                        // get temperature average from two sensors

    readAlarmStatus();                                        // update alarm status
    readRaspiStatus();                                        // update raspi status
    readLightLevel();                                         // update light level value
    prevTime = currTime;                                      // update last update time
  }

  // wait for an incoming TCP packet, but ignore its contents
  if (ether.packetLoop(ether.packetReceive())) {
    //ether.httpServerReply(testPage());
    ether.httpServerReply(homePage());
  }
}

void readLightStatusPin(){                                    // check light status pin
  if ((digitalRead(LIGHT1STATUSPIN) == HIGH) || 
      (digitalRead(LIGHT2STATUSPIN) == HIGH)){                // if light status pin is HIGH
    if (DEBUG) Serial.println("Light on");
    setLightOn();                                             // turn light on
    light = true;
  }else{
    if (DEBUG) Serial.println("Light off");
    setLightOff();                                            // turn light off
    light = false;
  }
}

void readLightLevel(){                                        // read light level from LDR and store average
  int newValue = analogRead(LDRPIN) / 2;                      // read from the sensor
  int oldValue = 0;                                           // dequeue oldest value

  if (DEBUG) Serial.print("Queue lenght: ");
  if (DEBUG) Serial.print(readings.count());
  if (DEBUG) Serial.print(" - Newer: ");
  if (DEBUG) Serial.print(newValue);

  if (readings.count() < numReadings){                        // check if queue did not reach max lenght
    readings.enqueue(newValue);                               // add sensor value into queue
    totalLightLevel = totalLightLevel + newValue;             // add the reading to the total
  }else{                                                      // if queue at max lenght
    oldValue = readings.dequeue();                            // remove oldest value from queue
    if (DEBUG) Serial.print(" - Oldest: ");
    if (DEBUG) Serial.print(oldValue);    
    totalLightLevel = totalLightLevel - oldValue;             // subtract the last reading
    readings.enqueue(newValue);                               // add sensor value into queue
    totalLightLevel = totalLightLevel + newValue;             // add the reading to the total
  }
  averageLightLevel = totalLightLevel / readings.count();     // calculate the average
  if (DEBUG) Serial.print(" - Light level (average): ");
  if (DEBUG) Serial.println(averageLightLevel);
}

void setLightOff(){                                           // turn light off
  digitalWrite(RELAY1PIN, HIGH);
  digitalWrite(RELAY2PIN, HIGH);
}

void setLightOn(){                                            // turn light on
  digitalWrite(RELAY1PIN, LOW);
  digitalWrite(RELAY2PIN, LOW);
}

void readAlarmStatus(){                                       // check if home alarm is on or off
  if (digitalRead(ALARMSTATUSPIN) == LOW){
    if (DEBUG) Serial.println("Alarm on");
    alarm = true;                                             // in case ALARMPIN is LOW alarm is on
  }else{
    if (DEBUG) Serial.println("Alarm off");
    alarm = false;                                            // in case ALARMPIN is HIGH alarm is off
  }
}

void readRaspiStatus(){
  if (digitalRead(RPISTATUSPIN) == HIGH){
    if (DEBUG) Serial.println("RasPi on");
    raspi = true;                                             // in case ALARMPIN is LOW alarm is on
  }else{
    if (DEBUG) Serial.println("RasPI off");
    raspi = false;                                            // in case ALARMPIN is HIGH alarm is off
  }
}

void gateOpener(int value){                                   // gate opener
  digitalWrite(GATEPIN, value);
}

void readHTU21D()                                              // read weather data from sensors
{
  if (DEBUG) Serial.print("HTU21D, \t");
  humidity = tempHumSendor.readHumidity();
  temp1 = tempHumSendor.readTemperature();
  if (DEBUG) Serial.print("T: ");
  if (DEBUG) Serial.print(temperature);
  if (DEBUG) Serial.print("\tH: ");
  if (DEBUG) Serial.println(humidity);
}

float readBMP180()
{
  char status;
  double T,P;

  // Start a temperature measurement:
  // If request is successful, the number of ms to wait is returned.
  // If request is unsuccessful, 0 is returned.
  status = pressureSensor.startTemperature();
  if (status != 0)
  {
    bmp180Delay(status);
    status = pressureSensor.getTemperature(T);
    if (status != 0)
    {
      if (DEBUG) Serial.print("BMP180, \tT: ");
      if (DEBUG) Serial.print(T,2);
      temp2 = (float) T;

      // Start a pressure measurement:
      // The parameter is the oversampling setting, from 0 to 3 (highest res, longest wait).
      // If request is successful, the number of ms to wait is returned.
      // If request is unsuccessful, 0 is returned.
      status = pressureSensor.startPressure(3);
      if (status != 0)
      {
        // Wait for the measurement to complete:
        bmp180Delay(status);
        status = pressureSensor.getPressure(P,T);
        if (status != 0)
        {
          pressure = (float) pressureSensor.sealevel(P,ALTITUDE);
          if (DEBUG) Serial.print("\tP: ");
          if (DEBUG) Serial.print(pressure,2);
          if (DEBUG) Serial.println(" hPa");
        }
        else if (DEBUG) Serial.println("error retrieving pressure measurement\n");
      }
      else if (DEBUG) Serial.println("error starting pressure measurement\n");
    }
    else if (DEBUG) Serial.println("error retrieving temperature measurement\n");
  }
  else if (DEBUG) Serial.println("error starting temperature measurement\n");
}

void bmp180Delay(unsigned long ms)
{
  unsigned long targetMs = millis() + ms;
  while (millis() < targetMs){
    //Do nothing
  }
}

static word homePage() {
  int temp1 = 1;
  if (alarm) temp1 = 0;

  int temp2 = 1;
  if (light) temp2 = 0;

  int t1 = temperature;
  int t2 = (temperature - t1) * 10;
  int h1 = humidity;
  int h2 = (humidity - h1) * 10;
  int p1 = pressure;
  int p2 = (pressure - p1) * 10;

  if (DEBUG) Serial.print("Data to be sent: ");
  if (DEBUG) Serial.print(t1);
  if (DEBUG) Serial.print(".");
  if (DEBUG) Serial.print(t2);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(h1);
  if (DEBUG) Serial.print(".");
  if (DEBUG) Serial.print(h2);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(p1);
  if (DEBUG) Serial.print(".");
  if (DEBUG) Serial.print(p2);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(temp1);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(temp2);
  if (DEBUG) Serial.println("");

  bfill = ether.tcpOffset();
  bfill.emit_p(PSTR("$D.$D $D.$D $D.$D $D $D $D"),
    t1, t2, h1, h2, p1, p2, averageLightLevel, temp1, temp2);
  return bfill.position();
}

static word testPage() {
 long t = millis() / 1000;
 word h = t / 3600;
 byte m = (t / 60) % 60;
 byte s = t % 60;
 bfill = ether.tcpOffset();
 bfill.emit_p(PSTR(
   "HTTP/1.0 200 OK\r\n"
   "Content-Type: text/html\r\n"
   "Pragma: no-cache\r\n"
   "\r\n"
   "<meta http-equiv='refresh' content='1'/>"
   "<title>RBBB server</title>" 
   "<h1>$D$D:$D$D:$D$D</h1>"),
     h/10, h%10, m/10, m%10, s/10, s%10);
 return bfill.position();
}

