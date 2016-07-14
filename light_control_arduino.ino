// https://github.com/jcw/ethercard
//VCC -   3.3V
//GND -    GND
//SCK - Pin 52
//SO  - Pin 50
//SI  - Pin 51
//CS  - Pin 53 # Selectable with the ether.begin() function
//The default CS pin defaults to 8, so you have to set it on a mega:
//ether.begin(sizeof Ethernet::buffer, mymac, 53)
#include <dht.h>
#include <EtherCard.h>

static byte myip[] = { 192,168,1,100 };                  // ethernet interface static ip address
static byte gwip[] = { 192,168,1,1 };                    // gateway static ip address

static byte mymac[] = { 0x74,0x69,0x69,0x2D,0x30,0x31 }; // ethernet mac address - must be unique on your network

byte Ethernet::buffer[500];                              // tcp/ip send and receive buffer
BufferFiller bfill;

dht DHT;                                            // weather sensor data global var
const byte DHTPIN = 22;                             // set DHT22 sensor pin
const byte LIGHT1STATUSPIN = 11;                    // set light 1 status pin
const byte LIGHT2STATUSPIN = 10;                    // set light 2 status pin
const byte GATESTATUSPIN = 7;                       // set gate status pin
const byte RPISTATUSPIN = 6;                        // set RasPi status pin
const byte ALARMSTATUSPIN = 2;                      // set alarm status pin

const byte RELAY1PIN = 23;                          // set light relay 1 pin
const byte RELAY2PIN = 24;                          // set light relay 2 pin
const byte GATEPIN = 25;                            // set gate opening pin

unsigned long currTime = 0;                         // store current time in milliseconds since board is up
unsigned long prevTime = 0;                         // store last time lapse reading
float temperature = 0;                              // global temperature var
float humidity = 0;                                 // global humidity var
boolean light = false;                              // set initial light status
boolean alarm = false;                              // set initial alarm status
boolean raspi = false;                              // set initial raspi status
const byte LDRPIN = A0;                             // set LDR sensor pin
const boolean STATICIPADDRESS = false;              // set to true to disable DHCP (adjust myip/gwip values above)
const boolean DEBUG = false;                        // enable or disable debug messages

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

  readDHT22();                                                // initialize temp and humidit values
  readLightStatusPin();                                       // check light status
  readAlarmStatus();                                          // initialize alarm status
  readRaspiStatus();                                          // initialize raspi status
}

void loop() {
  currTime = millis();                                        // read current time in milliseconds since system is UP
  if (currTime < prevTime) currTime = prevTime;               // check for currTime overflow (after aprox. 50 days);
  if ((currTime - prevTime) >= 15000){                        // check if passed 15 sec since last data update
    readDHT22();                                              // read weather data from sensor
    readLightStatusPin();                                     // update light status
    readAlarmStatus();                                        // update alarm status
    readRaspiStatus();                                        // update raspi status
    prevTime = currTime;                                      // update last update time
  }

  // wait for an incoming TCP packet, but ignore its contents
  if (ether.packetLoop(ether.packetReceive())) {
    //ether.httpServerReply(testPage());
    ether.httpServerReply(homePage());
  }
}

void readLightStatusPin(){                                 // check light status pin
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

int readLightLevel(){                                         // read light level from LDR
  return analogRead(LDRPIN) / 2;
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

void readDHT22()                                              // read weather data from sensors
{
  if (DEBUG) Serial.print("DHT22, \t");
  int chk = DHT.read22(DHTPIN);                               // readdata from sensor
  //int chk = DHT.read11(DHTPIN);
  switch (chk)                                                // check if read result was ok
  {
    case DHTLIB_OK:  
      if (DEBUG) Serial.print("OK,\t"); 
      break;
    case DHTLIB_ERROR_CHECKSUM: 
      if (DEBUG) Serial.print("Checksum error,\t"); 
      break;
    case DHTLIB_ERROR_TIMEOUT: 
      if (DEBUG) Serial.print("Time out error,\t"); 
      break;
    default: 
      if (DEBUG) Serial.print("Unknown error,\t"); 
      break;
  }
  if (DEBUG) Serial.print("T: ");
  if (DEBUG) Serial.print(DHT.temperature, 1);
  temperature = DHT.temperature;                              // update temperature global var
  if (DEBUG) Serial.print(",\tH: ");
  if (DEBUG) Serial.println(DHT.humidity, 1);
  humidity = DHT.humidity;                                    // update humidity global var
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

  if (DEBUG) Serial.print("Data to be sent: ");
  if (DEBUG) Serial.print(t1);
  if (DEBUG) Serial.print(".");
  if (DEBUG) Serial.print(t2);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(h1);
  if (DEBUG) Serial.print(".");
  if (DEBUG) Serial.print(h2);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(temp1);
  if (DEBUG) Serial.print(" ");
  if (DEBUG) Serial.print(temp2);
  if (DEBUG) Serial.println("");

  bfill = ether.tcpOffset();
  bfill.emit_p(PSTR("$D.$D $D.$D $D $D $D"),
    t1, t2, h1, h2, readLightLevel(), temp1, temp2);
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
