# PharmaBot Arduino Medication Dispenser

## Hardware Setup Guide

### Required Components:
1. **ESP32 Development Board** (or Arduino Uno with WiFi Shield)
2. **DS3231 RTC Module** - For accurate timekeeping
3. **6x SG90 Servo Motors** - For medicine compartments
4. **Buzzer** - For medication alerts
5. **3x LEDs** (Red, Green, Blue) - Status indicators
6. **2x Push Buttons** - Confirm and Skip
7. **Resistors** - 220Ω for LEDs, 10KΩ for buttons
8. **Breadboard and Jumper Wires**
9. **Power Supply** - 5V 2A adapter

### Wiring Diagram:

```
ESP32 Pin Connections:
├── Servo Motors
│   ├── GPIO 13 → Servo 1 (Compartment 0)
│   ├── GPIO 12 → Servo 2 (Compartment 1)
│   ├── GPIO 14 → Servo 3 (Compartment 2)
│   ├── GPIO 27 → Servo 4 (Compartment 3)
│   ├── GPIO 26 → Servo 5 (Compartment 4)
│   └── GPIO 25 → Servo 6 (Compartment 5)
│
├── Indicators
│   ├── GPIO 18 → Buzzer (+)
│   ├── GPIO 19 → Red LED (→ 220Ω → GND)
│   ├── GPIO 21 → Green LED (→ 220Ω → GND)
│   └── GPIO 22 → Blue LED (→ 220Ω → GND)
│
├── Buttons
│   ├── GPIO 23 → Confirm Button (→ 10KΩ → GND)
│   └── GPIO 5 → Skip Button (→ 10KΩ → GND)
│
└── I2C (RTC Module)
    ├── GPIO 21 (SDA) → RTC SDA
    └── GPIO 22 (SCL) → RTC SCL
```

### Power Connections:
- All servos: 5V and GND from external power supply
- ESP32: 5V from USB or external supply
- RTC Module: 3.3V from ESP32
- All components share common GND

## Software Setup

### 1. Arduino IDE Setup:
```bash
# Install ESP32 Board Support
# Go to: File → Preferences → Additional Board Manager URLs
# Add: https://dl.espressif.com/dl/package_esp32_index.json

# Install Required Libraries:
# Tools → Manage Libraries → Install:
- WiFi (built-in)
- HTTPClient (built-in)
- ArduinoJson (by Benoit Blanchon)
- ESP32Servo (by Kevin Harrington)
- RTClib (by Adafruit)
```

### 2. Configure Arduino Code:
Edit `medication_dispenser.ino`:

```cpp
// WiFi Credentials
const char* WIFI_SSID = "YourWiFiName";
const char* WIFI_PASSWORD = "YourWiFiPassword";

// Server Configuration
const char* SERVER_URL = "http://pharmabot.shagato.me";
const char* USERNAME = "your_username";  // Your PharmaBot username
```

### 3. Upload Code:
1. Connect ESP32 to computer via USB
2. Select Board: `Tools → Board → ESP32 Dev Module`
3. Select Port: `Tools → Port → (your COM port)`
4. Click Upload button

## Medicine Compartment Assignment

### Via Web Interface:
1. Go to http://pharmabot.shagato.me
2. Login with your username
3. Go to Prescriptions → Select prescription
4. Click "View Schedule" on any medicine
5. Assign compartment number (0-5) for each medicine

### Via API (from Arduino Serial Monitor):
```
Send GET request:
/api/device/schedules?username=your_username

Update compartment:
POST /api/device/medicine/update-compartment
{
  "username": "your_username",
  "medicine_id": 1,
  "compartment_number": 0
}
```

## API Endpoints

### 1. Get Server Time (for RTC sync)
```
GET /api/device/time
Response: {
  "timestamp": 1733049600,
  "datetime": "2025-12-01 14:00:00",
  "timezone": "Asia/Dhaka"
}
```

### 2. Get Schedules
```
GET /api/device/schedules?username=your_username
Response: {
  "success": true,
  "schedules": [
    {
      "id": 1,
      "medicine_name": "Paracetamol",
      "dosage": "500mg",
      "compartment_number": 0,
      "scheduled_timestamp": 1733049600,
      "instructions": "Take after meal"
    }
  ]
}
```

### 3. Mark as Taken
```
POST /api/schedule/1/mark-taken
Body: { "username": "your_username" }
```

### 4. Device Heartbeat
```
POST /api/device/heartbeat
Body: {
  "device_id": "ESP32_UNIQUE_ID",
  "username": "your_username",
  "device_name": "Living Room Dispenser"
}
```

## LED Status Indicators

| LED Color | Status |
|-----------|--------|
| 🔴 Red    | WiFi connection error / System error |
| 🟢 Green  | Connected and ready / Dispensing |
| 🔵 Blue   | Syncing data / Medication alert |

## Buzzer Alerts

- **3 beeps** - Medication time
- **2 beeps** - Successful dispense
- **5 beeps** - Error/Warning

## Operation

### Normal Operation:
1. Device syncs schedules every 5 minutes
2. Checks for due medications every 60 seconds
3. When medication time arrives:
   - Buzzer sounds 3 times
   - Blue LED blinks
   - Waits 30 seconds for user confirmation
4. User presses:
   - **Confirm button** → Dispenses medicine immediately
   - **Skip button** → Marks as skipped
   - **No button** → Auto-dispenses after 30 seconds

### Manual Override:
- Hold Confirm button for 3 seconds to test dispensing
- Press Reset button to restart device

## Troubleshooting

### WiFi Not Connecting:
- Check SSID and password
- Ensure 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Move closer to router

### RTC Time Wrong:
- Device auto-syncs with server on boot
- Check server URL is correct
- Verify internet connection

### Servo Not Moving:
- Check power supply (servos need separate 5V power)
- Verify pin connections
- Test servo angle values (0-180)

### No Schedules Received:
- Verify username is correct
- Check if prescriptions exist on web portal
- Ensure medicines have compartment numbers assigned

## Maintenance

### Daily:
- Check LED indicators are functioning
- Verify WiFi connection (green LED)

### Weekly:
- Refill medicine compartments
- Check servo movement
- Verify schedule accuracy

### Monthly:
- Replace RTC battery if needed
- Clean compartments
- Update firmware if available

## Safety Notes

⚠️ **IMPORTANT:**
1. This is an assistive device, not a replacement for medical supervision
2. Always verify medication schedules on web portal
3. Keep device out of reach of children
4. Do not expose to water
5. Use only prescribed medications
6. Consult healthcare provider for any concerns

## Support

For issues or questions:
- Web Portal: http://pharmabot.shagato.me
- Email: support@pharmabot.com
- GitHub: https://github.com/yourusername/pharmabot
