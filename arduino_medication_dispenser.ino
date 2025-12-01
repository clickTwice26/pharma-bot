#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <NTPClient.h>
#include <WiFiUdp.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL = "http://YOUR_SERVER_IP:7878";
const char* USERNAME = "YOUR_USERNAME";
const char* DEVICE_ID = "ESP32_001";
const char* DEVICE_NAME = "Living Room Dispenser";

const long UTC_OFFSET = 6 * 3600;
const int NUM_COMPARTMENTS = 8;
const int SERVO_OPEN_ANGLE = 90;
const int SERVO_CLOSE_ANGLE = 0;
const int DISPENSE_DURATION = 3000;

const int SERVO_PINS[NUM_COMPARTMENTS] = {13, 12, 14, 27, 26, 25, 33, 32};
const int BUZZER_PIN = 23;
const int LED_PIN = 2;

Servo servos[NUM_COMPARTMENTS];
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", UTC_OFFSET, 60000);

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
const unsigned long SYNC_INTERVAL = 300000;
const unsigned long CHECK_INTERVAL = 30000;

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=================================");
  Serial.println("PharmaBot Medication Dispenser");
  Serial.println("=================================\n");
  
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  
  initializeServos();
  connectWiFi();
  
  timeClient.begin();
  updateTime();
  registerDevice();
  syncSchedules();
  
  Serial.println("\n✓ Setup complete! Device is ready.\n");
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
  
  blinkLED();
  delay(100);
}

void initializeServos() {
  Serial.println("Initializing servos...");
  for (int i = 0; i < NUM_COMPARTMENTS; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(SERVO_CLOSE_ANGLE);
    delay(100);
  }
  Serial.println("✓ Servos initialized");
}

void dispenseFromCompartment(int compartmentNumber) {
  if (compartmentNumber < 1 || compartmentNumber > NUM_COMPARTMENTS) {
    Serial.println("✗ Invalid compartment number");
    return;
  }
  
  int index = compartmentNumber - 1;
  Serial.printf("Dispensing from compartment %d...\n", compartmentNumber);
  
  playAlertSound();
  
  digitalWrite(LED_PIN, HIGH);
  servos[index].write(SERVO_OPEN_ANGLE);
  Serial.println("✓ Compartment opened");
  
  delay(DISPENSE_DURATION);
  
  servos[index].write(SERVO_CLOSE_ANGLE);
  digitalWrite(LED_PIN, LOW);
  Serial.println("✓ Compartment closed");
  
  playSuccessSound();
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
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
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    playErrorSound();
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
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/device/schedules?username=" + String(USERNAME);
  http.begin(url);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String response = http.getString();
    parseSchedules(response);
  } else {
    Serial.printf("✗ Failed to sync schedules (HTTP %d)\n", httpCode);
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

void blinkLED() {
  static unsigned long lastBlink = 0;
  static bool ledState = false;
  
  if (millis() - lastBlink >= 2000) {
    lastBlink = millis();
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}
