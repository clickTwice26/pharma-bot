/*
 * PharmaBot ESP32 Firmware
 * 
 * This Arduino sketch enables ESP32 to work with the PharmaBot system.
 * Features:
 * - WiFi connectivity
 * - HTTP server for receiving commands
 * - LED/Buzzer for medication reminders
 * - Servo motor for dispensing (optional)
 * - Automatic heartbeat to server
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// PharmaBot Server Configuration
const char* serverUrl = "http://YOUR_SERVER_IP:7878";
String deviceId = "";  // Will be set to MAC address

// Hardware Pins
const int LED_PIN = 2;           // Built-in LED
const int BUZZER_PIN = 4;        // Buzzer for alerts
const int SERVO_PIN = 5;         // Servo for dispensing (optional)

// Web Server
WebServer server(80);

// Timing
unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 60000;  // 1 minute

void setup() {
  Serial.begin(115200);
  
  // Initialize hardware
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Get Device ID from MAC address
  deviceId = "ESP32-" + WiFi.macAddress();
  deviceId.replace(":", "");
  
  Serial.println("\n=================================");
  Serial.println("PharmaBot ESP32 Firmware v1.0");
  Serial.println("=================================");
  Serial.println("Device ID: " + deviceId);
  
  // Connect to WiFi
  connectWiFi();
  
  // Setup HTTP server routes
  server.on("/notify", HTTP_POST, handleNotification);
  server.on("/dispense", HTTP_POST, handleDispense);
  server.on("/status", HTTP_GET, handleStatus);
  server.onNotFound(handleNotFound);
  
  server.begin();
  Serial.println("HTTP server started on port 80");
  Serial.println("Local IP: " + WiFi.localIP().toString());
  Serial.println("=================================\n");
  
  // Send initial registration
  registerDevice();
  
  // Startup animation
  startupAnimation();
}

void loop() {
  // Handle HTTP requests
  server.handleClient();
  
  // Send periodic heartbeat
  unsigned long currentMillis = millis();
  if (currentMillis - lastHeartbeat >= heartbeatInterval) {
    sendHeartbeat();
    lastHeartbeat = currentMillis;
  }
  
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected! Reconnecting...");
    connectWiFi();
  }
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));  // Blink LED
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_PIN, HIGH);
    delay(1000);
    digitalWrite(LED_PIN, LOW);
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

void registerDevice() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  HTTPClient http;
  String url = String(serverUrl) + "/api/device/register";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<256> doc;
  doc["device_id"] = deviceId;
  doc["device_name"] = "ESP32 Dispenser";
  doc["ip_address"] = WiFi.localIP().toString();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Device registration response: " + response);
  } else {
    Serial.println("Device registration failed: " + String(httpCode));
  }
  
  http.end();
}

void sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  HTTPClient http;
  String url = String(serverUrl) + "/api/device/" + deviceId + "/status";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  StaticJsonDocument<128> doc;
  doc["ip_address"] = WiFi.localIP().toString();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == 200) {
    Serial.println("Heartbeat sent successfully");
    blinkLED(1, 100);
  } else {
    Serial.println("Heartbeat failed: " + String(httpCode));
  }
  
  http.end();
}

void handleNotification() {
  if (server.hasArg("plain")) {
    String body = server.arg("plain");
    Serial.println("Notification received:");
    Serial.println(body);
    
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, body);
    
    if (!error) {
      String medicine = doc["medicine"];
      String dosage = doc["dosage"];
      String instructions = doc["instructions"];
      
      Serial.println("Medicine: " + medicine);
      Serial.println("Dosage: " + dosage);
      Serial.println("Instructions: " + instructions);
      
      // Play notification
      playAlert();
      
      server.send(200, "application/json", "{\"success\":true,\"message\":\"Notification received\"}");
    } else {
      server.send(400, "application/json", "{\"success\":false,\"error\":\"Invalid JSON\"}");
    }
  } else {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"No data\"}");
  }
}

void handleDispense() {
  if (server.hasArg("plain")) {
    String body = server.arg("plain");
    Serial.println("Dispense command received:");
    Serial.println(body);
    
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, body);
    
    if (!error) {
      int compartment = doc["compartment"];
      String medicine = doc["medicine"];
      
      Serial.println("Dispensing from compartment " + String(compartment));
      Serial.println("Medicine: " + medicine);
      
      // Dispense medicine (implement your dispenser logic here)
      dispenseMedicine(compartment);
      
      server.send(200, "application/json", "{\"success\":true,\"message\":\"Medicine dispensed\"}");
    } else {
      server.send(400, "application/json", "{\"success\":false,\"error\":\"Invalid JSON\"}");
    }
  } else {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"No data\"}");
  }
}

void handleStatus() {
  StaticJsonDocument<256> doc;
  doc["device_id"] = deviceId;
  doc["status"] = "online";
  doc["ip_address"] = WiFi.localIP().toString();
  doc["uptime"] = millis() / 1000;
  doc["wifi_rssi"] = WiFi.RSSI();
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  server.send(200, "application/json", jsonString);
}

void handleNotFound() {
  server.send(404, "text/plain", "Not Found");
}

void playAlert() {
  // Visual alert (LED blinks)
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
  
  // Audio alert (buzzer beeps)
  for (int i = 0; i < 3; i++) {
    tone(BUZZER_PIN, 1000, 200);  // 1kHz for 200ms
    delay(300);
  }
}

void dispenseMedicine(int compartment) {
  Serial.println("Dispensing from compartment " + String(compartment));
  
  // Example: Blink LED pattern for dispensing
  for (int i = 0; i < 10; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
  
  // TODO: Implement actual servo motor control for dispenser
  // Example:
  // myServo.write(90);  // Open compartment
  // delay(2000);
  // myServo.write(0);   // Close compartment
  
  Serial.println("Dispense complete!");
}

void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
  }
}

void startupAnimation() {
  // Blink LED 3 times
  blinkLED(3, 200);
  
  // Play startup tone
  tone(BUZZER_PIN, 1000, 100);
  delay(150);
  tone(BUZZER_PIN, 1500, 100);
  delay(150);
  tone(BUZZER_PIN, 2000, 100);
}

/*
 * Installation Instructions:
 * 
 * 1. Install Arduino IDE
 * 2. Install ESP32 board support:
 *    - File -> Preferences -> Additional Boards Manager URLs
 *    - Add: https://dl.espressif.com/dl/package_esp32_index.json
 * 3. Install required libraries:
 *    - ArduinoJson (by Benoit Blanchon)
 * 4. Update WiFi credentials (ssid and password)
 * 5. Update serverUrl with your PharmaBot server IP
 * 6. Select board: ESP32 Dev Module
 * 7. Upload to ESP32
 * 8. Open Serial Monitor (115200 baud) to see device ID
 * 9. Register device in PharmaBot web interface
 */
