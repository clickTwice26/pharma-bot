#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <LiquidCrystal_I2C.h>

const char* WIFI_SSID = "5hagat0-Private";
const char* WIFI_PASSWORD = "1292?5hagat0";
const char* SERVER_URL = "http://156.67.110.215:7878";
const char* USERNAME = "shagatoc";
const char* DEVICE_ID = "ESP32_001";
const char* DEVICE_NAME = "Pharma Bot";

const long UTC_OFFSET = 6 * 3600;
const int NUM_COMPARTMENTS = 3;
const int SERVO_OPEN_ANGLE = 180;
const int SERVO_CLOSE_ANGLE = 0;
const int DISPENSE_DURATION = 3000;

const int SERVO_PINS[NUM_COMPARTMENTS] = {13, 12, 14};
const int BUZZER_PIN = 23;
const int LED_PIN = 2;

const int ULTRASONIC_TRIG = 32;
const int ULTRASONIC_ECHO = 33;
const float MEDICINE_LOADED_DISTANCE = 5.0;

Servo servos[NUM_COMPARTMENTS];
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", UTC_OFFSET, 60000);
LiquidCrystal_I2C lcd(0x27, 16, 2);  // I2C address 0x27, 16 columns, 2 rows

int currentServoAngles[NUM_COMPARTMENTS] = {0, 0, 0};
float currentDistance = 0.0;
bool currentLedState = false;
bool currentBuzzerState = false;
String currentOperation = "idle";
unsigned long lastStateUpdate = 0;
const unsigned long STATE_UPDATE_INTERVAL = 2000;

struct MedicationSchedule {
  int scheduleId;
  int medicineId;
  String medicineName;
  int compartmentNumber;
  unsigned long scheduledTime;
  bool dispensed;
};

const int MAX_SCHEDULES = 50;
MedicationSchedule schedules[MAX_SCHEDULES];
int scheduleCount = 0;

unsigned long lastSyncTime = 0;
unsigned long lastCheckTime = 0;
unsigned long lastHeartbeat = 0;
const unsigned long SYNC_INTERVAL = 300000;
const unsigned long CHECK_INTERVAL = 30000;
const unsigned long HEARTBEAT_INTERVAL = 60000;

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=================================");
  Serial.println("PharmaBot Medication Dispenser");
  Serial.println("=================================\n");
  
  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("PharmaBot v1.0");
  lcd.setCursor(0, 1);
  lcd.print("Starting...");
  
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);
  
  initializeServos();
  connectWiFi();
  
  timeClient.begin();
  updateTime();
  registerDevice();
  syncSchedules();
  
  Serial.println("\n✓ Setup complete! Device is ready.\n");
  Serial.println("=================================");
  Serial.println("Device Configuration:");
  Serial.println("=================================");
  Serial.printf("Server URL: %s\n", SERVER_URL);
  Serial.printf("Device ID: %s\n", DEVICE_ID);
  Serial.printf("Username: %s\n", USERNAME);
  Serial.printf("WiFi IP: %s\n", WiFi.localIP().toString().c_str());
  Serial.println("=================================\n");
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ready! Schedules:");
  lcd.setCursor(0, 1);
  lcd.print(String(scheduleCount) + " loaded");
  
  playStartupSound();
}

void loop() {
  unsigned long currentMillis = millis();
  
  timeClient.update();
  
  if (currentMillis - lastSyncTime >= SYNC_INTERVAL) {
    lastSyncTime = currentMillis;
    syncSchedules();
  }
  
  if (currentMillis - lastCheckTime >= CHECK_INTERVAL) {
    lastCheckTime = currentMillis;
    checkMedicationTimes();
  }
  
  if (currentMillis - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    lastHeartbeat = currentMillis;
    sendHeartbeat();
  }
  
  if (currentMillis - lastStateUpdate >= STATE_UPDATE_INTERVAL) {
    lastStateUpdate = currentMillis;
    currentDistance = getDistance();
    sendHardwareState();
    checkForCommands();
    updateLCDDisplay();
  }
  
  blinkLED();
  delay(100);
}

void initializeServos() {
  Serial.println("Initializing servos...");
  
  // Set all servos to closed position, one at a time
  for (int i = 0; i < NUM_COMPARTMENTS; i++) {
    Serial.printf("Setting servo %d to closed position...\n", i + 1);
    servos[i].attach(SERVO_PINS[i]);
    delay(100);
    servos[i].write(SERVO_CLOSE_ANGLE);
    currentServoAngles[i] = SERVO_CLOSE_ANGLE;
    delay(300);
    servos[i].detach();  // Immediately detach to prevent interference
    delay(100);
  }
  
  Serial.println("✓ All servos initialized and closed\n");
}

float getDistance() {
  digitalWrite(ULTRASONIC_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);
  
  long duration = pulseIn(ULTRASONIC_ECHO, HIGH);
  float distance = duration * 0.034 / 2;
  
  currentDistance = distance;
  return distance;
}

bool isMedicineLoaded() {
  float distance = getDistance();
  Serial.printf("Distance measured: %.2f cm\n", distance);
  
  if (distance <= MEDICINE_LOADED_DISTANCE) {
    Serial.println("✓ Medicine detected!");
    return true;
  } else {
    Serial.println("✗ No medicine detected");
    return false;
  }
}

void dispenseFromCompartment(int compartmentNumber) {
  if (compartmentNumber < 1 || compartmentNumber > NUM_COMPARTMENTS) {
    Serial.println("✗ Invalid compartment number");
    return;
  }
  
  int index = compartmentNumber - 1;
  Serial.printf("Dispensing from compartment %d...\n", compartmentNumber);
  
  if (compartmentNumber == 1) {
    Serial.println("Checking if medicine is loaded...");
    if (!isMedicineLoaded()) {
      Serial.println("✗ ERROR: No medicine in compartment 1!");
      playErrorSound();
      return;
    }
  }
  
  currentOperation = "dispensing_compartment_" + String(compartmentNumber);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Dispensing Slot");
  lcd.setCursor(0, 1);
  lcd.print(String(compartmentNumber) + " - Please wait");
  
  playAlertSound();
  
  // Attach servo for dispense operation
  servos[index].attach(SERVO_PINS[index]);
  delay(200);
  
  currentLedState = true;
  digitalWrite(LED_PIN, HIGH);
  servos[index].write(SERVO_OPEN_ANGLE);
  currentServoAngles[index] = SERVO_OPEN_ANGLE;
  Serial.println("✓ Compartment opened");
  sendHardwareState();
  
  delay(DISPENSE_DURATION);
  
  servos[index].write(SERVO_CLOSE_ANGLE);
  currentServoAngles[index] = SERVO_CLOSE_ANGLE;
  currentLedState = false;
  digitalWrite(LED_PIN, LOW);
  Serial.println("✓ Compartment closed");
  sendHardwareState();
  
  delay(500);
  
  // Detach servo after operation to prevent jitter
  servos[index].detach();
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Dispensed!");
  lcd.setCursor(0, 1);
  lcd.print("Take medicine");
  
  playSuccessSound();
  delay(3000);  // Show success message for 3 seconds
  currentOperation = "idle";
  sendHardwareState();
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");
  lcd.setCursor(0, 1);
  lcd.print("Please wait...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_PIN, LOW);
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected!");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP().toString());
    delay(2000);
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed!");
    lcd.setCursor(0, 1);
    lcd.print("Check Settings");
    playErrorSound();
    delay(3000);
  }
}

void updateTime() {
  timeClient.update();
  Serial.print("Current time: ");
  Serial.println(timeClient.getFormattedTime());
}

unsigned long getCurrentEpochTime() {
  return timeClient.getEpochTime();
}

void registerDevice() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi not connected. Cannot register device.");
    return;
  }
  
  Serial.println("Registering device with server...");
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/register";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<200> doc;
  doc["device_id"] = DEVICE_ID;
  doc["device_name"] = DEVICE_NAME;
  doc["ip_address"] = WiFi.localIP().toString();
  doc["username"] = USERNAME;
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.printf("✓ Device registered (HTTP %d)\n", httpCode);
    Serial.println(response);
  } else {
    Serial.printf("✗ Registration failed: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}

void syncSchedules() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi not connected. Cannot sync schedules.");
    return;
  }
  
  Serial.println("\nSyncing schedules from server...");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Syncing...");
  lcd.setCursor(0, 1);
  lcd.print("Checking server");
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/schedules?username=" + String(USERNAME);
  Serial.println("📡 Requesting: " + url);
  http.begin(url);
  
  int httpCode = http.GET();
  Serial.printf("📊 HTTP Response Code: %d\n", httpCode);
  
  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("📥 Schedule Response:");
    Serial.println(response);
    parseSchedules(response);
  } else if (httpCode > 0) {
    String response = http.getString();
    Serial.printf("✗ Failed to sync schedules (HTTP %d)\n", httpCode);
    Serial.println("Error response: " + response);
  } else {
    Serial.printf("✗ Connection failed: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}

void parseSchedules(String jsonResponse) {
  DynamicJsonDocument doc(8192);
  DeserializationError error = deserializeJson(doc, jsonResponse);
  
  if (error) {
    Serial.print("✗ JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  JsonArray schedulesArray = doc["schedules"].as<JsonArray>();
  scheduleCount = 0;
  
  for (JsonObject schedule : schedulesArray) {
    if (scheduleCount >= MAX_SCHEDULES) break;
    
    schedules[scheduleCount].scheduleId = schedule["schedule_id"];
    schedules[scheduleCount].medicineId = schedule["medicine_id"];
    schedules[scheduleCount].medicineName = schedule["medicine_name"].as<String>();
    schedules[scheduleCount].compartmentNumber = schedule["compartment_number"];
    schedules[scheduleCount].scheduledTime = schedule["scheduled_time"];
    schedules[scheduleCount].dispensed = false;
    
    scheduleCount++;
  }
  
  Serial.printf("✓ Loaded %d schedules\n", scheduleCount);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Schedules: " + String(scheduleCount));
  lcd.setCursor(0, 1);
  if (scheduleCount > 0) {
    lcd.print("Next: " + schedules[0].medicineName.substring(0, 10));
  } else {
    lcd.print("None scheduled");
  }
  delay(2000);
  
  if (scheduleCount > 0) {
    Serial.println("\nUpcoming schedules:");
    for (int i = 0; i < min(5, scheduleCount); i++) {
      Serial.printf("  %d. %s (Compartment %d) at %lu\n", 
        i + 1,
        schedules[i].medicineName.c_str(),
        schedules[i].compartmentNumber,
        schedules[i].scheduledTime
      );
    }
  }
}

void markScheduleAsTaken(int scheduleId) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi not connected. Cannot mark schedule.");
    return;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/dispense";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<200> doc;
  doc["schedule_id"] = scheduleId;
  doc["device_id"] = DEVICE_ID;
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode == 200) {
    Serial.printf("✓ Schedule %d marked as dispensed\n", scheduleId);
  } else {
    Serial.printf("✗ Failed to mark schedule (HTTP %d)\n", httpCode);
  }
  
  http.end();
}

void checkMedicationTimes() {
  unsigned long currentTime = getCurrentEpochTime();
  
  for (int i = 0; i < scheduleCount; i++) {
    if (!schedules[i].dispensed && schedules[i].scheduledTime <= currentTime) {
      Serial.println("\n⏰ MEDICATION TIME!");
      Serial.printf("Medicine: %s\n", schedules[i].medicineName.c_str());
      Serial.printf("Compartment: %d\n", schedules[i].compartmentNumber);
      
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Time for:");
      lcd.setCursor(0, 1);
      String medName = schedules[i].medicineName;
      if (medName.length() > 16) medName = medName.substring(0, 16);
      lcd.print(medName);
      delay(2000);
      
      dispenseFromCompartment(schedules[i].compartmentNumber);
      schedules[i].dispensed = true;
      markScheduleAsTaken(schedules[i].scheduleId);
    }
  }
}

void playAlertSound() {
  for (int i = 0; i < 3; i++) {
    tone(BUZZER_PIN, 1000, 200);
    delay(300);
  }
  noTone(BUZZER_PIN);
}

void playSuccessSound() {
  tone(BUZZER_PIN, 1500, 100);
  delay(150);
  tone(BUZZER_PIN, 2000, 100);
  delay(150);
  noTone(BUZZER_PIN);
}

void playErrorSound() {
  for (int i = 0; i < 2; i++) {
    tone(BUZZER_PIN, 500, 300);
    delay(400);
  }
  noTone(BUZZER_PIN);
}

void playStartupSound() {
  tone(BUZZER_PIN, 1000, 100);
  delay(150);
  tone(BUZZER_PIN, 1500, 100);
  delay(150);
  tone(BUZZER_PIN, 2000, 100);
  delay(150);
  noTone(BUZZER_PIN);
}

void sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/heartbeat";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<200> doc;
  doc["device_id"] = DEVICE_ID;
  doc["username"] = USERNAME;
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode == 200) {
    Serial.println("✓ Heartbeat sent");
  }
  
  http.end();
}

void sendHardwareState() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/state";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["username"] = USERNAME;
  
  JsonArray angles = doc.createNestedArray("servo_angles");
  for (int i = 0; i < NUM_COMPARTMENTS; i++) {
    angles.add(currentServoAngles[i]);
  }
  
  doc["ultrasonic_distance"] = currentDistance;
  doc["medicine_detected"] = (currentDistance > 0 && currentDistance <= MEDICINE_LOADED_DISTANCE);
  doc["led_state"] = currentLedState;
  doc["buzzer_state"] = currentBuzzerState;
  doc["current_operation"] = currentOperation;
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  int httpCode = http.POST(jsonPayload);
  
  if (httpCode == 200) {
    Serial.println("✓ Hardware state sent");
  }
  
  http.end();
}

void checkForCommands() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/commands?device_id=" + String(DEVICE_ID) + "&username=" + String(USERNAME);
  Serial.println("\n🔍 Checking for commands: " + url);
  http.begin(url);
  
  int httpCode = http.GET();
  Serial.printf("📊 Commands HTTP Code: %d\n", httpCode);
  
  if (httpCode == 200) {
    String response = http.getString();
    
    // Log the raw response
    Serial.println("\n📥 Raw command response from server:");
    Serial.println(response);
    
    DynamicJsonDocument doc(2048);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      JsonArray commands = doc["commands"].as<JsonArray>();
      
      if (commands.size() > 0) {
        Serial.printf("\n📋 Found %d command(s) to execute:\n", commands.size());
      }
      
      for (JsonObject cmd : commands) {
        String command = cmd["command"].as<String>();
        JsonObject params = cmd["params"];
        
        Serial.println("\n⚡ Received command: " + command);
        
        // Log all parameters
        Serial.println("📦 Parameters:");
        for (JsonPair kv : params) {
          Serial.printf("  - %s: ", kv.key().c_str());
          if (kv.value().is<int>()) {
            Serial.println(kv.value().as<int>());
          } else if (kv.value().is<String>()) {
            Serial.println(kv.value().as<String>());
          } else {
            Serial.println("(other type)");
          }
        }
        
        executeCommand(command, params);
      }
    } else {
      Serial.println("✗ JSON parsing error: " + String(error.c_str()));
    }
  } else if (httpCode > 0) {
    Serial.printf("✗ Failed to get commands (HTTP %d)\n", httpCode);
  }
  
  http.end();
}

void executeCommand(String command, JsonObject params) {
  if (command == "test_servo") {
    int slot = params["slot"] | 1;
    if (slot >= 1 && slot <= NUM_COMPARTMENTS) {
      currentOperation = "manual_test_servo_" + String(slot);
      Serial.printf("Testing servo %d...\n", slot);
      
      int index = slot - 1;
      
      // Attach only this servo
      servos[index].attach(SERVO_PINS[index]);
      delay(200);
      
      servos[index].write(0);
      currentServoAngles[index] = 0;
      sendHardwareState();
      delay(500);
      
      servos[index].write(90);
      currentServoAngles[index] = 90;
      sendHardwareState();
      delay(500);
      
      servos[index].write(180);
      currentServoAngles[index] = 180;
      sendHardwareState();
      delay(500);
      
      servos[index].write(0);
      currentServoAngles[index] = 0;
      sendHardwareState();
      delay(500);
      
      // Detach after test
      servos[index].detach();
      
      Serial.printf("✓ Servo %d test complete\n", slot);
      currentOperation = "idle";
      sendHardwareState();
    }
  }
  else if (command == "read_ultrasonic") {
    currentOperation = "reading_ultrasonic";
    Serial.println("Reading ultrasonic sensor...");
    
    float distance = getDistance();
    Serial.printf("Distance: %.2f cm\n", distance);
    
    if (distance <= MEDICINE_LOADED_DISTANCE) {
      Serial.println("✓ Medicine detected!");
    } else {
      Serial.println("✗ No medicine detected");
    }
    
    sendHardwareState();
    currentOperation = "idle";
    sendHardwareState();
  }
  else if (command == "test_buzzer") {
    currentOperation = "testing_buzzer";
    Serial.println("Testing buzzer...");
    currentBuzzerState = true;
    sendHardwareState();
    
    playAlertSound();
    
    currentBuzzerState = false;
    Serial.println("✓ Buzzer test complete");
    currentOperation = "idle";
    sendHardwareState();
  }
  else if (command == "test_led") {
    currentOperation = "testing_led";
    Serial.println("Testing LED...");
    
    currentLedState = true;
    digitalWrite(LED_PIN, HIGH);
    sendHardwareState();
    delay(1000);
    
    currentLedState = false;
    digitalWrite(LED_PIN, LOW);
    sendHardwareState();
    
    Serial.println("✓ LED test complete");
    currentOperation = "idle";
    sendHardwareState();
  }
  else if (command == "manual_dispense") {
    int compartment = params["compartment"] | 0;
    String medicineName = params["medicine_name"] | "Medicine";
    String timeOfDay = params["time_of_day"] | "unknown";
    int dispenseCount = params["dispense_count"] | 1;  // Default to 1 if not specified
    
    // Check if dispense count is 0
    if (dispenseCount == 0) {
      Serial.println("✗ Dispense count is 0 - no medication scheduled for this time");
      playErrorSound();
      return;
    }
    
    if (compartment >= 1 && compartment <= NUM_COMPARTMENTS) {
      currentOperation = "manual_dispense_" + timeOfDay;
      Serial.printf("Manual dispense triggered for %s (%s)\n", medicineName.c_str(), timeOfDay.c_str());
      Serial.printf("Dispensing from compartment %d, count: %d\n", compartment, dispenseCount);
      
      int index = compartment - 1;
      
      // Play alert sound first
      playAlertSound();
      
      // Turn on LED
      currentLedState = true;
      digitalWrite(LED_PIN, HIGH);
      
      // Attach servo and give it time to stabilize
      Serial.println("Attaching servo...");
      servos[index].attach(SERVO_PINS[index]);
      delay(500);  // Increased delay for servo to stabilize
      
      // Dispense multiple times based on dispense_count
      for (int i = 0; i < dispenseCount; i++) {
        Serial.printf("Dispense %d of %d\n", i + 1, dispenseCount);
        
        // Open compartment (full rotation)
        Serial.println("Opening compartment (180°)...");
        servos[index].write(SERVO_OPEN_ANGLE);
        currentServoAngles[index] = SERVO_OPEN_ANGLE;
        sendHardwareState();
        delay(DISPENSE_DURATION);  // Wait for medicine to dispense
        
        // Close compartment
        Serial.println("Closing compartment (0°)...");
        servos[index].write(SERVO_CLOSE_ANGLE);
        currentServoAngles[index] = SERVO_CLOSE_ANGLE;
        sendHardwareState();
        delay(1000);  // Give time to fully close
        
        // Short pause between dispenses (except for the last one)
        if (i < dispenseCount - 1) {
          Serial.println("Pausing before next dispense...");
          delay(500);
        }
      }
      
      // Detach servo
      servos[index].detach();
      Serial.println("Servo detached");
      
      // Turn off LED
      currentLedState = false;
      digitalWrite(LED_PIN, LOW);
      
      // Play success sound
      playSuccessSound();
      
      Serial.printf("✓ Manual dispense complete for %s (%d times)\n", medicineName.c_str(), dispenseCount);
      currentOperation = "idle";
      sendHardwareState();
    } else {
      Serial.printf("✗ Invalid compartment number: %d\n", compartment);
    }
  }
}

void updateLCDDisplay() {
  // Don't update LCD during active operations
  if (currentOperation != "idle") {
    return;
  }
  
  static unsigned long lastLCDUpdate = 0;
  
  // Update LCD every 2 seconds when idle
  if (millis() - lastLCDUpdate < 2000) {
    return;
  }
  lastLCDUpdate = millis();
  
  lcd.clear();
  
  // First line: Current time
  lcd.setCursor(0, 0);
  lcd.print(timeClient.getFormattedTime());
  
  // Second line: Next medication or status
  lcd.setCursor(0, 1);
  
  if (scheduleCount > 0) {
    // Find next undispensed schedule
    unsigned long currentTime = getCurrentEpochTime();
    bool foundNext = false;
    
    for (int i = 0; i < scheduleCount; i++) {
      if (!schedules[i].dispensed && schedules[i].scheduledTime > currentTime) {
        String medName = schedules[i].medicineName;
        if (medName.length() > 10) medName = medName.substring(0, 10);
        lcd.print("Nxt:" + medName);
        foundNext = true;
        break;
      }
    }
    
    if (!foundNext) {
      lcd.print("All done today!");
    }
  } else {
    lcd.print("No schedules");
  }
}

void blinkLED() {
  // Don't interfere with LED when it's being used for operations
  if (currentLedState) {
    return;
  }
  
  static unsigned long lastBlink = 0;
  static bool ledState = false;
  
  if (millis() - lastBlink >= 2000) {
    lastBlink = millis();
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}
