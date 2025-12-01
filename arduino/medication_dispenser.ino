/*
 * PharmaBot Medication Dispenser
 * ESP32/Arduino Based Automatic Medicine Dispenser
 * 
 * Features:
 * - WiFi connectivity to fetch schedules from server
 * - Multiple servo motors for different medicine compartments
 * - RTC module for accurate timekeeping
 * - Buzzer for medication alerts
 * - LED indicators
 * 
 * Hardware Requirements:
 * - ESP32/Arduino Uno with WiFi Shield
 * - DS3231 RTC Module
 * - 6 x Servo Motors (SG90)
 * - Buzzer
 * - LEDs (Red, Green, Blue)
 * - Push buttons for manual override
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <RTClib.h>

// ==================== CONFIGURATION ====================
// WiFi Credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Server Configuration
const char* SERVER_URL = "http://pharmabot.shagato.me";
const char* USERNAME = "YOUR_USERNAME";  // User's username
const int CHECK_INTERVAL = 60000;  // Check every 60 seconds

// Hardware Pin Configuration
#define NUM_SERVOS 6
const int SERVO_PINS[NUM_SERVOS] = {13, 12, 14, 27, 26, 25};  // GPIO pins for servos
const int BUZZER_PIN = 18;
const int LED_RED = 19;
const int LED_GREEN = 21;
const int LED_BLUE = 22;
const int BUTTON_CONFIRM = 23;
const int BUTTON_SKIP = 5;

// Servo Configuration
const int SERVO_OPEN_ANGLE = 90;   // Angle to dispense
const int SERVO_CLOSE_ANGLE = 0;   // Angle to close
const int DISPENSE_DURATION = 2000; // Keep open for 2 seconds

// ==================== GLOBAL VARIABLES ====================
Servo servos[NUM_SERVOS];
RTC_DS3231 rtc;
HTTPClient http;

struct MedicineSchedule {
  int id;
  int medicineId;
  String medicineName;
  String dosage;
  String instructions;
  int compartmentNumber;  // Servo motor index (0-5)
  unsigned long scheduledTime;  // Unix timestamp
  bool taken;
  bool notified;
};

MedicineSchedule schedules[50];  // Store up to 50 upcoming schedules
int scheduleCount = 0;
unsigned long lastCheckTime = 0;
unsigned long lastSyncTime = 0;
const unsigned long SYNC_INTERVAL = 300000;  // Sync every 5 minutes

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  Serial.println("PharmaBot Medication Dispenser Starting...");
  
  // Initialize pins
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  pinMode(BUTTON_CONFIRM, INPUT_PULLUP);
  pinMode(BUTTON_SKIP, INPUT_PULLUP);
  
  // Initialize servos
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(SERVO_CLOSE_ANGLE);
  }
  
  // Initialize RTC
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    blinkLED(LED_RED, 5);
  } else {
    Serial.println("RTC initialized");
    if (rtc.lostPower()) {
      Serial.println("RTC lost power, setting time from compile time");
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
  }
  
  // Connect to WiFi
  connectWiFi();
  
  // Initial sync
  syncSchedules();
  
  blinkLED(LED_GREEN, 3);
  Serial.println("Setup complete!");
}

// ==================== MAIN LOOP ====================
void loop() {
  unsigned long currentMillis = millis();
  
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    setLED(LED_RED, true);
    connectWiFi();
    return;
  } else {
    setLED(LED_GREEN, true);
  }
  
  // Periodic schedule sync
  if (currentMillis - lastSyncTime >= SYNC_INTERVAL) {
    syncSchedules();
    lastSyncTime = currentMillis;
  }
  
  // Check schedules every minute
  if (currentMillis - lastCheckTime >= CHECK_INTERVAL) {
    checkSchedules();
    lastCheckTime = currentMillis;
  }
  
  // Check buttons
  checkButtons();
  
  delay(100);
}

// ==================== WiFi FUNCTIONS ====================
void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    // Sync RTC with server time
    syncTimeWithServer();
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

void syncTimeWithServer() {
  String url = String(SERVER_URL) + "/api/device/time";
  http.begin(url);
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    
    unsigned long serverTime = doc["timestamp"];
    if (serverTime > 0) {
      rtc.adjust(DateTime(serverTime));
      Serial.println("RTC synced with server time");
    }
  }
  
  http.end();
}

// ==================== SCHEDULE FUNCTIONS ====================
void syncSchedules() {
  Serial.println("Syncing schedules from server...");
  setLED(LED_BLUE, true);
  
  String url = String(SERVER_URL) + "/api/device/schedules?username=" + USERNAME;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    parseSchedules(payload);
    Serial.print("Loaded ");
    Serial.print(scheduleCount);
    Serial.println(" schedules");
    blinkLED(LED_GREEN, 2);
  } else {
    Serial.print("HTTP Error: ");
    Serial.println(httpCode);
    blinkLED(LED_RED, 2);
  }
  
  http.end();
  setLED(LED_BLUE, false);
}

void parseSchedules(String json) {
  DynamicJsonDocument doc(8192);
  DeserializationError error = deserializeJson(doc, json);
  
  if (error) {
    Serial.print("JSON parse error: ");
    Serial.println(error.c_str());
    return;
  }
  
  JsonArray schedulesArray = doc["schedules"].as<JsonArray>();
  scheduleCount = 0;
  
  for (JsonObject schedule : schedulesArray) {
    if (scheduleCount >= 50) break;
    
    schedules[scheduleCount].id = schedule["id"];
    schedules[scheduleCount].medicineId = schedule["medicine_id"];
    schedules[scheduleCount].medicineName = schedule["medicine_name"].as<String>();
    schedules[scheduleCount].dosage = schedule["dosage"].as<String>();
    schedules[scheduleCount].instructions = schedule["instructions"].as<String>();
    schedules[scheduleCount].compartmentNumber = schedule["compartment_number"];
    schedules[scheduleCount].scheduledTime = schedule["scheduled_timestamp"];
    schedules[scheduleCount].taken = schedule["taken"];
    schedules[scheduleCount].notified = false;
    
    scheduleCount++;
  }
}

void checkSchedules() {
  DateTime now = rtc.now();
  unsigned long currentTime = now.unixtime();
  
  Serial.print("Checking schedules at: ");
  Serial.println(now.timestamp());
  
  for (int i = 0; i < scheduleCount; i++) {
    if (schedules[i].taken) continue;
    
    // Check if it's time to dispense (within 2 minutes)
    long timeDiff = currentTime - schedules[i].scheduledTime;
    
    if (timeDiff >= 0 && timeDiff <= 120) {  // Within 2 minutes
      if (!schedules[i].notified) {
        notifyMedication(i);
        schedules[i].notified = true;
      }
    }
  }
}

// ==================== MEDICATION DISPENSING ====================
void notifyMedication(int scheduleIndex) {
  Serial.println("==============================================");
  Serial.println("TIME FOR MEDICATION!");
  Serial.print("Medicine: ");
  Serial.println(schedules[scheduleIndex].medicineName);
  Serial.print("Dosage: ");
  Serial.println(schedules[scheduleIndex].dosage);
  Serial.print("Instructions: ");
  Serial.println(schedules[scheduleIndex].instructions);
  Serial.println("==============================================");
  
  // Sound buzzer
  buzzerAlert();
  
  // Blink LED
  for (int i = 0; i < 10; i++) {
    setLED(LED_BLUE, true);
    delay(300);
    setLED(LED_BLUE, false);
    delay(300);
  }
  
  // Wait for user confirmation or auto-dispense after 30 seconds
  unsigned long startWait = millis();
  bool confirmed = false;
  
  while (millis() - startWait < 30000) {  // Wait 30 seconds
    if (digitalRead(BUTTON_CONFIRM) == LOW) {
      confirmed = true;
      dispenseMedicine(scheduleIndex);
      break;
    }
    
    if (digitalRead(BUTTON_SKIP) == LOW) {
      Serial.println("Medication skipped by user");
      markAsSkipped(scheduleIndex);
      return;
    }
    
    delay(100);
  }
  
  if (!confirmed) {
    // Auto-dispense after timeout
    Serial.println("Auto-dispensing after timeout");
    dispenseMedicine(scheduleIndex);
  }
}

void dispenseMedicine(int scheduleIndex) {
  int compartment = schedules[scheduleIndex].compartmentNumber;
  
  if (compartment < 0 || compartment >= NUM_SERVOS) {
    Serial.println("Invalid compartment number!");
    return;
  }
  
  Serial.print("Dispensing from compartment ");
  Serial.println(compartment);
  
  // Open compartment
  servos[compartment].write(SERVO_OPEN_ANGLE);
  setLED(LED_GREEN, true);
  
  // Keep open for dispense duration
  delay(DISPENSE_DURATION);
  
  // Close compartment
  servos[compartment].write(SERVO_CLOSE_ANGLE);
  setLED(LED_GREEN, false);
  
  // Mark as taken on server
  markAsTaken(scheduleIndex);
  
  // Success tone
  tone(BUZZER_PIN, 1000, 200);
  delay(300);
  tone(BUZZER_PIN, 1500, 200);
  
  Serial.println("Medicine dispensed successfully!");
}

// ==================== SERVER COMMUNICATION ====================
void markAsTaken(int scheduleIndex) {
  schedules[scheduleIndex].taken = true;
  
  String url = String(SERVER_URL) + "/api/schedule/" + String(schedules[scheduleIndex].id) + "/mark-taken";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Send username for authentication
  String payload = "{\"username\":\"" + String(USERNAME) + "\"}";
  int httpCode = http.POST(payload);
  
  if (httpCode == HTTP_CODE_OK) {
    Serial.println("Marked as taken on server");
  } else {
    Serial.print("Failed to mark as taken: ");
    Serial.println(httpCode);
  }
  
  http.end();
}

void markAsSkipped(int scheduleIndex) {
  String url = String(SERVER_URL) + "/api/schedule/" + String(schedules[scheduleIndex].id) + "/mark-skipped";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  String payload = "{\"username\":\"" + String(USERNAME) + "\"}";
  int httpCode = http.POST(payload);
  
  if (httpCode == HTTP_CODE_OK) {
    Serial.println("Marked as skipped on server");
  }
  
  http.end();
}

// ==================== BUTTON HANDLING ====================
void checkButtons() {
  // Manual dispense buttons can be added here
  // For testing purposes
}

// ==================== HELPER FUNCTIONS ====================
void buzzerAlert() {
  for (int i = 0; i < 3; i++) {
    tone(BUZZER_PIN, 2000, 500);
    delay(700);
  }
  noTone(BUZZER_PIN);
}

void setLED(int pin, bool state) {
  digitalWrite(pin, state ? HIGH : LOW);
}

void blinkLED(int pin, int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(200);
    digitalWrite(pin, LOW);
    delay(200);
  }
}

void tone(int pin, int frequency, int duration) {
  ledcSetup(0, frequency, 8);
  ledcAttachPin(pin, 0);
  ledcWriteTone(0, frequency);
  delay(duration);
  ledcWriteTone(0, 0);
}

void noTone(int pin) {
  ledcWriteTone(0, 0);
}
