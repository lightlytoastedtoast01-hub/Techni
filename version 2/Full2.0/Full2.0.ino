#include <ArduinoBLE.h>
#include <Arduino_BMI270_BMM150.h>

#define LED_PIN 9 // Status LED
unsigned long lastBlink = 0;
const unsigned long blinkInterval = 200; // 200 ms

// BLE Service
BLEService imuService("19B10000-E8F2-537E-4F6C-D104768A1214");

// Changed from String to standard BLEFloatCharacteristic.
// Sending Strings over BLE destroys bandwidth and causes extreme lag.
BLEFloatCharacteristic accelXCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLEFloatCharacteristic accelYCharacteristic("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLEFloatCharacteristic accelZCharacteristic("19B10003-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

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

  String mac = BLE.address(); // "AA:BB:CC:DD:EE:FF"
  byte macBytes[6];
  
  // CRITICAL FIX: Use unsigned int (uint32_t) for 32-bit ARM architecture sscanf parsing
  unsigned int values[6]; 

  // Parse the MAC string safely
  if (sscanf(mac.c_str(), "%x:%x:%x:%x:%x:%x", &values[0], &values[1], &values[2], &values[3], &values[4], &values[5]) == 6) {
    for (int i = 0; i < 6; i++) {
      macBytes[i] = (byte)values[i];
    }
    // Put MAC in manufacturer data
    BLE.setManufacturerData(macBytes, 6);
  } else {
    Serial.println("Failed to parse MAC address safely!");
  }

  // Build device name with MAC suffix to make it unique
  String deviceName = "Arduino-" + mac.substring(12, 14) + mac.substring(15, 17);
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
  
  // Blink status LED when disconnected
  if (!central) {
    unsigned long now = millis();
    if (now - lastBlink >= blinkInterval) {
      lastBlink = now;
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    }
  }

  if (central) {
    Serial.print("Connected to: ");
    Serial.println(central.address());
    
    // Keep LED solid when connected
    digitalWrite(LED_PIN, HIGH); 

    while (central.connected()) {
      float x, y, z;
      
      // Process background BLE events
      BLE.poll(); 

      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(x, y, z);
        
        // Write raw floats (4 bytes) instead of heavy Strings
        accelXCharacteristic.writeValue(x);
        accelYCharacteristic.writeValue(y);
        accelZCharacteristic.writeValue(z);
        
        // Debug output
        Serial.print(x); Serial.print("\t");
        Serial.print(y); Serial.print("\t");
        Serial.println(z);
      }
    }
    
    Serial.print("Disconnected from: ");
    Serial.println(central.address());
  }
}
