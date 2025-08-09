#include <Arduino.h>

// Stepper motor pins - remap these to the pins you actually used
const int IN1 = 25;
const int IN2 = 26;
const int IN3 = 27;
const int IN4 = 14;

// Half-step sequence for 28BYJ-48
const uint8_t seq[8][4] = {
  {1,0,0,0}, {1,1,0,0}, {0,1,0,0}, {0,1,1,0},
  {0,0,1,0}, {0,0,1,1}, {0,0,0,1}, {1,0,0,1}
};

// Stepper motor parameters
const int STEPS_PER_REVOLUTION = 4096; // 28BYJ-48 steps for 360°
const int STEPS_PER_DEGREE = STEPS_PER_REVOLUTION / 360; // ~11.38 steps per degree
const int TOTAL_DEGREES = 360;
const int WAIT_TIME_SECONDS = 46;

// Current position tracking
int currentDegree = 0;
int targetDegree = 0;

void stepMotor(int steps, bool clockwise) {
  for (int step = 0; step < abs(steps); step++) {
    int idx;
    if (clockwise) {
      idx = step & 7;
    } else {
      idx = (8 - (step & 7)) & 7;
    }
    
    digitalWrite(IN1, seq[idx][0]);
    digitalWrite(IN2, seq[idx][1]);
    digitalWrite(IN3, seq[idx][2]);
    digitalWrite(IN4, seq[idx][3]);
    delay(2); // Speed control - adjust if needed
  }
  
  // Turn off coils to save power
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

void moveToDegree(int degrees) {
  int stepsToMove = degrees * STEPS_PER_DEGREE;
  stepMotor(stepsToMove, true); // Move clockwise
  currentDegree = degrees;
}

void waitWithCountdown(int seconds) {
  Serial.print("Waiting ");
  Serial.print(seconds);
  Serial.println(" seconds for servo scan cycle...");
  
  for (int i = seconds; i > 0; i--) {
    Serial.print("Countdown: ");
    Serial.print(i);
    Serial.println(" seconds remaining");
    delay(1000);
  }
  Serial.println("Wait complete!\n");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Set GPIO pins as outputs
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  
  // Turn off all coils initially
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  
  Serial.println("=== ESP32 Stepper Motor Controller Ready ===");
  Serial.println("28BYJ-48 Stepper Motor - 360° Scanning Pattern");
  Serial.println("Pattern: Initialize to 0° → Wait 62s → Move 1° → Repeat");
  Serial.print("Steps per degree: ");
  Serial.println(STEPS_PER_DEGREE);
  
  // Initialize to 0 degrees (already at 0, but this is explicit)
  currentDegree = 0;
  targetDegree = 0;
  
  Serial.println("Stepper initialized to 0 degrees");
  Serial.println("Starting scanning pattern...\n");
}

void loop() {
  // Wait 62 seconds (synchronized with servo scan cycle)
  waitWithCountdown(WAIT_TIME_SECONDS);
  
  // Move to next degree position
  targetDegree++;
  
  Serial.print("=== Moving from ");
  Serial.print(currentDegree);
  Serial.print("° to ");
  Serial.print(targetDegree);
  Serial.println("° ===");
  
  // Move 1 degree clockwise
  stepMotor(STEPS_PER_DEGREE, true);
  currentDegree = targetDegree;
  
  Serial.print("Stepper now at ");
  Serial.print(currentDegree);
  Serial.println("°");
  
  // Check if we've completed 360 degrees
  if (currentDegree >= TOTAL_DEGREES) {
    Serial.println("\n=== 360° SCAN COMPLETE! ===");
    Serial.println("Resetting to 0° and starting new cycle...\n");
    
    // Reset for next cycle
    currentDegree = 0;
    targetDegree = 0;
    
    // Optional: Move back to 0° (uncomment if you want to physically return)
    // Serial.println("Moving back to 0°...");
    // stepMotor(TOTAL_DEGREES * STEPS_PER_DEGREE, false); // Move counter-clockwise
    
    delay(2000); // Brief pause before starting next 360° cycle
  }
}
