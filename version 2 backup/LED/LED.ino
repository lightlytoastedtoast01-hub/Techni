#include <ArduinoBLE.h>
#include <Arduino_BMI270_BMM150.h>

// BLE Service
BLEService imuService("19B10000-E8F2-537E-4F6C-D104768A1214");

// Characteristics for X, Y, Z acceleration
BLEFloatCharacteristic accelXCharacteristic(
  "19B10001-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLENotify
);

BLEFloatCharacteristic accelYCharacteristic(
  "19B10002-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLENotify
);

BLEFloatCharacteristic accelZCharacteristic(
  "19B10003-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLENotify
);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("BLE failed to start!");
    while (1);
  }

  if (!IMU.begin()) {
    Serial.println("IMU failed to start!");
    while (1);
  }

  BLE.setLocalName("IMU");
  BLE.setAdvertisedService(imuService);

  imuService.addCharacteristic(accelXCharacteristic);
  imuService.addCharacteristic(accelYCharacteristic);
  imuService.addCharacteristic(accelZCharacteristic);

  BLE.addService(imuService);

  BLE.advertise();

  Serial.println("BLE IMU Peripheral started");
  Serial.print("Accelerometer sample rate = ");
  Serial.print(IMU.accelerationSampleRate());
  Serial.println(" Hz");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to: ");
    Serial.println(central.address());

    while (central.connected()) {
      float x, y, z;

      BLE.poll();

      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(x, y, z);

        accelXCharacteristic.writeValue(x);
        accelYCharacteristic.writeValue(y);
        accelZCharacteristic.writeValue(z);

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