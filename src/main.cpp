#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <Adafruit_VL53L1X.h>

// Servo object
Servo myServo;

// TOF sensor object
Adafruit_VL53L1X vl53 = Adafruit_VL53L1X();

// Hardware pins
const int servoPin = 17;
const int sdaPin = 21;  // I2C SDA for TOF sensor
const int sclPin = 15;  // I2C SCL for TOF sensor (updated to pin 15)

// Servo movement parameters
const int minDegree = 0;
const int maxDegree = 180;
const int stepDelay = 100; // Delay for coordinate acquisition
int currentServoPos = 0;

// TOF measurement variables
int16_t distance = 0;

void readTOFSensor() {
  if (vl53.dataReady()) {
    distance = vl53.distance();
    if (distance == -1) {
      Serial.println("TOF: Failed to get reading!");
    } else {
      Serial.print("Distance: ");
      Serial.print(distance);
      Serial.println(" mm");
    }
    vl53.clearInterrupt();
  }
}

void smoothMoveServoWithTOF(int startPos, int endPos) {
  currentServoPos = startPos;
  
  if (startPos < endPos) {
    // Moving forward
    for (int pos = startPos; pos <= endPos; pos++) {
      myServo.write(pos);
      currentServoPos = pos;
      
      Serial.print("Servo at ");
      Serial.print(pos);
      Serial.print(" degrees - ");
      
      // Read TOF sensor at this position
      delay(50); // Let servo settle
      readTOFSensor();
      
      delay(stepDelay - 50);
    }
  } else {
    // Moving backward
    for (int pos = startPos; pos >= endPos; pos--) {
      myServo.write(pos);
      currentServoPos = pos;
      
      Serial.print("Servo at ");
      Serial.print(pos);
      Serial.print(" degrees - ");
      
      // Read TOF sensor at this position
      delay(50); // Let servo settle
      readTOFSensor();
      
      delay(stepDelay - 50);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP32-S3 Servo + TOF Controller Starting...");
  
  // Initialize I2C with your pin configuration
  Wire.begin(sdaPin, sclPin);
  
  // Initialize TOF sensor
  if (!vl53.begin(VL53L1X_I2C_ADDR, &Wire)) {
    Serial.println("Error: VL53L1X sensor not found!");
    while (1) delay(10);
  }
  Serial.println("VL53L1X sensor initialized successfully!");
  
  // Configure TOF sensor
  if (!vl53.startRanging()) {
    Serial.println("Couldn't start ranging");
    while (1) delay(10);
  }
  Serial.println("TOF sensor ranging started");
  
  // Initialize servo
  myServo.attach(servoPin);
  myServo.write(0);
  delay(1000);
  
  Serial.println("=== ESP32-S3 Servo + TOF Controller Ready ===");
  Serial.println("Hardware: SDA=Pin21, SCL=Pin15, Servo=Pin17");
  Serial.println("Scanning Pattern: 0°→180° (pause 1s) → 180°→0° (pause 5s for stepper)");
}

void loop() {
  delay(1000);
  // Phase 1: Sweep from 0 to 180 degrees with TOF readings
  Serial.println("\n=== PHASE 1: Sweeping from 0° to 180° ===");
  smoothMoveServoWithTOF(minDegree, maxDegree);
  
  // Phase 2: Pause at 180 degrees for 1 second
  Serial.println("=== PHASE 2: Pausing at 180° for 1 second ===");
  delay(1000);
  
  // Phase 3: Sweep back from 180 to 0 degrees with TOF readings
  Serial.println("=== PHASE 3: Sweeping from 180° to 0° ===");
  smoothMoveServoWithTOF(maxDegree, minDegree);
  
  // Phase 4: Long pause at 0 degrees for stepper motor operation
  Serial.println("=== PHASE 4: Pausing at 0° for 5 seconds (stepper motor time) ===");
  for (int i = 5; i > 0; i--) {
    Serial.print("Stepper pause countdown: ");
    Serial.print(i);
    Serial.println(" seconds remaining...");
    delay(1000);
  }
  
  Serial.println("=== Scan cycle complete! Starting next cycle... ===\n");
}