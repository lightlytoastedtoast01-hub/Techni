#include <ArduinoBLE.h>
#include <Arduino_BMI270_BMM150.h>

#define LED_PIN 9 // Status LED
unsigned long lastBlink = 0;
const unsigned long blinkInterval = 200; // 200 ms


// BLE Service
BLEService imuService("19B10000-E8F2-537E-4F6C-D104768A1214");

// Characteristics for X, Y, Z acceleration
BLEStringCharacteristic accelXCharacteristic(
  "19B10001-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLENotify,
  60
);

BLEStringCharacteristic accelYCharacteristic(
  "19B10002-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLENotify,
  60
);

BLEStringCharacteristic accelZCharacteristic(
  "19B10003-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLENotify,
  60
);

void setup() {
  delay(3000);
  Serial.begin(9600);

  pinMode(LED_PIN, OUTPUT);

  if (!BLE.begin()) {
    Serial.println("BLE failed to start!");
    while (1);
  }

  if (!IMU.begin()) {
    Serial.println("IMU failed to start!");
    while (1);
  }

  String mac = BLE.address();  // "AA:BB:CC:DD:EE:FF"

  byte macBytes[6];
  int values[6];

  // Parse the MAC string
  sscanf(mac.c_str(), "%x:%x:%x:%x:%x:%x",
        &values[0], &values[1], &values[2],
        &values[3], &values[4], &values[5]);

  for (int i = 0; i < 6; i++) {
    macBytes[i] = (byte)values[i];
  }

  // Put MAC in manufacturer data
  BLE.setManufacturerData(macBytes, 6);

  // Build device name with MAC
  String deviceName = "Arduino";

  BLE.setLocalName(deviceName.c_str());
  BLE.setAdvertisedService(imuService);

  imuService.addCharacteristic(accelXCharacteristic);
  imuService.addCharacteristic(accelYCharacteristic);
  imuService.addCharacteristic(accelZCharacteristic);
  

  BLE.addService(imuService);

  BLE.advertise();

  Serial.print("BLE IMU Peripheral started as: ");
  Serial.println(deviceName);
  Serial.print("MAC Address: ");
  Serial.println(mac);

  Serial.print("Accelerometer sample rate = ");
  Serial.print(IMU.accelerationSampleRate());
  Serial.println(" Hz");
}

void loop() {
  BLEDevice central = BLE.central();

  unsigned long now = millis();
  if (now - lastBlink >= blinkInterval) {
    lastBlink = now;
    digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // LED flashes on and off to indicate no BLE connection
  }

  if (central) {
    Serial.print("Connected to: ");
    Serial.println(central.address());

    while (central.connected()) {
      digitalWrite(LED_PIN, HIGH);
      float x, y, z;

      BLE.poll();

      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(x, y, z);

        accelXCharacteristic.writeValue(String(x));
        accelYCharacteristic.writeValue(String(y));
        accelZCharacteristic.writeValue(String(z));

        Serial.print(x);
        Serial.print("\t");
        Serial.print(y);
        Serial.print("\t");
        Serial.println(z);
      }
    }

    Serial.print("Disconnected from: ");
    Serial.println(central.address());
  }
}