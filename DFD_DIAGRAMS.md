# Data Flow Diagrams - PharmaBot Medication Management System

## Level 0 DFD (Context Diagram)

```
                                    ┌─────────────────────────────────────────┐
                                    │                                         │
                                    │      PharmaBot Medication Management    │
                ┌──────────────────>│              System                     │─────────────────┐
                │                   │                                         │                 │
                │                   └─────────────────────────────────────────┘                 │
                │                                                                                │
                │                                                                                │
        ┌───────┴────────┐                                                              ┌───────▼────────┐
        │                │                                                              │                │
        │     User       │                                                              │   ESP32 IoT    │
        │   (Patient)    │                                                              │     Device     │
        │                │                                                              │                │
        └───────┬────────┘                                                              └───────▲────────┘
                │                                                                                │
                │  • Prescription Images                                                        │
                │  • Authentication Credentials                                                 │
                │  • Manual Dispense Commands                                                   │
                │  • Schedule Management                                                        │
                │                                                                                │
                └───────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    │
                ┌───────────────────────────────────▼───────────────────────────────────┐
                │                                                                        │
                │                          External Systems                             │
                │                                                                        │
                │  ┌──────────────────┐              ┌──────────────────┐              │
                │  │  Google Gemini   │              │   WiFi Network   │              │
                │  │   AI Service     │              │                  │              │
                │  └──────────────────┘              └──────────────────┘              │
                │                                                                        │
                └────────────────────────────────────────────────────────────────────────┘

```

### External Entities:
1. **User (Patient)**: Uploads prescriptions, manages schedules, monitors medication adherence
2. **ESP32 IoT Device**: Hardware dispenser for automated medication delivery
3. **Google Gemini AI**: AI service for prescription image parsing and data extraction
4. **WiFi Network**: Communication infrastructure between components

### Data Flows:
- **User → System**: Prescription images, login credentials, manual commands, schedule configurations
- **System → User**: Dashboard statistics, medication schedules, adherence reports, device status
- **ESP32 → System**: Hardware state, dispense confirmations, heartbeat signals, sensor data
- **System → ESP32**: Dispense commands, schedule updates, configuration data
- **System → Gemini AI**: Prescription images for parsing
- **Gemini AI → System**: Structured prescription data (medicines, dosages, frequencies)

---

## Level 1 DFD (Major Processes)

```
                                 User (Patient)
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
            ┌───────────┐      ┌──────────┐      ┌──────────────┐
            │ 1.0       │      │ 2.0      │      │ 3.0          │
            │ User      │      │ Prescrip.│      │ Schedule     │
            │ Auth      │      │ Mgmt     │      │ Management   │
            └─────┬─────┘      └────┬─────┘      └──────┬───────┘
                  │                 │                    │
                  │                 │                    │
                  ▼                 ▼                    ▼
            ┌─────────────────────────────────────────────────┐
            │          D1: User Database                      │
            │  ┌──────────┬──────────────┬──────────────┐    │
            │  │  Users   │Prescriptions │  Medicines   │    │
            │  └──────────┴──────────────┴──────────────┘    │
            └─────────────────────────────────────────────────┘
                  │                 │                    │
                  │                 │                    │
                  ▼                 ▼                    ▼
            ┌─────────┐      ┌──────────┐      ┌──────────────┐
            │ 4.0     │      │ 5.0      │      │ 6.0          │
            │ Device  │      │ AI       │      │ Dispense     │
            │ Control │      │ Parsing  │      │ Logic        │
            └─────┬───┘      └────┬─────┘      └──────┬───────┘
                  │                │                    │
                  │                │                    │
                  ▼                ▼                    ▼
       ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
       │ D2: Device   │   │ D3: Schedules│   │ D4: Hardware │
       │    State     │   │   Database   │   │    State     │
       └──────────────┘   └──────────────┘   └──────────────┘
                  │                                    │
                  └────────────────┬───────────────────┘
                                   │
                                   ▼
                          ESP32 IoT Device
                                   │
                                   ▼
                          Google Gemini AI

```

### Process Descriptions:

#### **Process 1.0: User Authentication**
- **Input**: Username, password (optional)
- **Processing**: 
  - Validate credentials
  - Create/manage user sessions
  - Handle registration and login
- **Output**: Session token, user profile
- **Data Stores**: D1 (Users table)

#### **Process 2.0: Prescription Management**
- **Input**: 
  - Prescription image (PNG/JPG/PDF)
  - User credentials
- **Processing**: 
  - Validate file format and size
  - Send image to Gemini AI for parsing
  - Store prescription data
  - Extract medicine information
- **Output**: 
  - Prescription ID
  - Parsed medicine list
  - Prescription metadata
- **Data Stores**: D1 (Prescriptions, Medicines tables)
- **External**: Google Gemini AI Service

#### **Process 3.0: Schedule Management**
- **Input**: 
  - Medicine data (name, frequency, duration, timing)
  - Start date
  - User preferences
- **Processing**: 
  - Parse frequency patterns (e.g., "1+0+1", "twice daily")
  - Generate time-based schedules
  - Calculate dosage counts per time
  - Handle schedule regeneration
- **Output**: 
  - Daily medication schedules
  - Dosage timing (morning/afternoon/evening)
  - Schedule notifications
- **Data Stores**: D1 (Medicines), D3 (Schedules)

#### **Process 4.0: Device Control & Management**
- **Input**: 
  - Device registration data
  - User commands (manual dispense)
  - Hardware state updates
  - Heartbeat signals
- **Processing**: 
  - Register/authenticate ESP32 devices
  - Manage device status (online/offline)
  - Queue commands for devices
  - Track compartment assignments
  - Monitor device health
- **Output**: 
  - Device status updates
  - Command queue for ESP32
  - Hardware monitoring data
- **Data Stores**: D1 (IoT_Device), D2 (Device State), D4 (Hardware State)

#### **Process 5.0: AI Parsing Service**
- **Input**: Prescription image
- **Processing**: 
  - Image preprocessing
  - OCR and text extraction
  - Structured data extraction:
    - Patient info (name, age, gender)
    - Doctor name
    - Medicine names
    - Dosages
    - Frequencies
    - Instructions
    - Duration
    - Prescription date
- **Output**: Structured JSON prescription data
- **External**: Google Gemini Vision API

#### **Process 6.0: Dispense Logic**
- **Input**: 
  - Schedule triggers (time-based)
  - Manual dispense commands
  - Compartment assignments
  - Dosage counts
- **Processing**: 
  - Validate dosage counts (prevent zero-count dispense)
  - Parse frequency to determine count
  - Create dispense commands with parameters
  - Track dispense history
  - Update schedule status (taken/skipped)
- **Output**: 
  - Dispense commands to ESP32
  - Dispense confirmations
  - Updated schedule status
- **Data Stores**: D3 (Schedules), D4 (Hardware State)

---

## Data Stores:

### **D1: User Database (SQLite)**
- **Users**: id, username, email, created_at
- **Prescriptions**: id, user_id, image_path, doctor_name, prescription_date, patient_name, patient_age, patient_gender, is_active
- **Medicines**: id, prescription_id, name, dosage, frequency, duration, instructions, timing, compartment_number, dose_start_date, is_active

### **D2: Device State Database**
- **IoT_Device**: id, user_id, device_id, device_name, ip_address, is_online, is_active, last_seen, hardware_state (JSON)

### **D3: Schedules Database**
- **Schedules**: id, medicine_id, user_id, scheduled_time, taken, taken_at, skipped, created_at

### **D4: Hardware State (JSON in IoT_Device)**
- servo_angles: [0-180] × 3 compartments
- ultrasonic_distance: float (cm)
- medicine_detected: boolean
- led_state: boolean
- buzzer_state: boolean
- current_operation: string
- pending_commands: array of command objects

---

## Data Flow Details:

### **1. Prescription Upload Flow:**
```
User → Upload Image → Process 2.0 → Validate File
                                   → Save to Storage
                                   → Send to Gemini AI (Process 5.0)
                                   ← Receive Parsed Data
                                   → Store in D1 (Prescriptions, Medicines)
                                   → Generate Schedules (Process 3.0)
                                   → Store in D3 (Schedules)
                                   → Return Success to User
```

### **2. Automated Dispense Flow:**
```
Scheduler (Time Trigger) → Check D3 (upcoming schedules)
                         → Find due schedules
                         → Verify medicine compartment
                         → Get dosage count from frequency
                         → Create dispense command
                         → Store in D2 (pending_commands)
                         → ESP32 polls Process 4.0
                         ← Receive command
                         → Execute dispense (servo control)
                         → Send confirmation to Process 6.0
                         → Mark schedule as taken in D3
                         → Send notification to User
```

### **3. Manual Dispense Flow:**
```
User → Select Medicine + Time of Day → Process 6.0
                                     → Parse frequency for dosage count
                                     → Validate count > 0
                                     → Get compartment from D1 (Medicines)
                                     → Create manual_dispense command
                                     → Add to D2 (pending_commands)
                                     → ESP32 polls Process 4.0
                                     ← Retrieve command
                                     → Execute dispense × count
                                     → Send state updates to Process 4.0
                                     → Update D4 (Hardware State)
                                     → Confirm to User
```

### **4. Device State Synchronization Flow:**
```
ESP32 → Send hardware state → Process 4.0
                            → Parse state data (servos, sensors, LED, buzzer)
                            → Preserve pending_commands (critical!)
                            → Update D2 (IoT_Device.hardware_state)
                            → Store in D4 (Hardware State)
                            ← Return acknowledgment

ESP32 → Poll for commands → Process 4.0
                          → Retrieve from D2 (pending_commands)
                          → Clear commands after retrieval
                          ← Send command array
                          → Execute commands
                          → Send confirmation
```

### **5. Schedule Regeneration Flow:**
```
User → Request regenerate all → Process 3.0
                              → Select start date (default: today)
                              → Get all medicines from D1 (Prescriptions)
                              → For each medicine:
                                  → Delete old schedules from D3
                                  → Parse frequency + duration
                                  → Generate new schedule entries
                                  → Store in D3
                              → Update medicine.dose_start_date in D1
                              → Return summary to User
```

---

## Key Interactions:

### **User-System Interactions:**
1. Register/Login
2. Upload prescription image
3. View dashboard (stats, schedules, medicines)
4. Manual dispense trigger
5. Schedule management (view, regenerate, delete)
6. Device management
7. View medication adherence statistics

### **ESP32-System Interactions:**
1. Device registration
2. Heartbeat (every 60s)
3. Hardware state updates (every 2s)
4. Command polling (every 2s)
5. Schedule synchronization (every 5 min)
6. Dispense confirmations
7. Sensor data reporting (ultrasonic, LED, buzzer)

### **System-AI Interactions:**
1. Send prescription image
2. Receive parsed data:
   - Patient info
   - Medicine details
   - Dosages and frequencies
   - Instructions

---

## Critical Data Flows:

### **State Preservation Issue (Resolved):**
```
PROBLEM: ESP32 sends hardware state → Backend overwrites entire hardware_state JSON
         → pending_commands array is lost → ESP32 never receives commands

SOLUTION: Before updating hardware_state:
         → Parse existing hardware_state from D2
         → Extract pending_commands array
         → Merge with new state data
         → Write combined state back to D2
```

### **Zero-Count Validation:**
```
User triggers manual dispense (afternoon) → Process 6.0
                                          → Parse frequency "1+0+1"
                                          → Morning: 1, Afternoon: 0, Evening: 1
                                          → Validate: afternoon count = 0
                                          → Return error 400
                                          → Play error sound on ESP32
                                          → Notify user "No dosage for this time"
```

---

## System Architecture Summary:

- **Frontend**: Mobile-responsive web UI (Jinja2 templates + CSS)
- **Backend**: Flask REST API (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **IoT Communication**: HTTP polling (ESP32 → Server every 2s)
- **AI Service**: Google Gemini Vision API (cloud-based)
- **Hardware**: ESP32 with 3 servos, ultrasonic sensor, buzzer, LED, 16×2 LCD
- **Time Sync**: NTP client (UTC+6 offset for Asia/Dhaka)
- **Authentication**: Session-based (username only, optional email)

---

## Performance Considerations:

- **Polling Interval**: 2s (commands/state), 30s (schedules check), 60s (heartbeat), 300s (schedule sync)
- **Database**: Indexed on user_id, scheduled_time, medicine_id
- **State Management**: JSON column for flexible hardware state storage
- **Command Queue**: Array in JSON, cleared after retrieval
- **LCD Updates**: Throttled to 2s intervals during idle state
- **Servo Control**: Attach → Move → Detach pattern to prevent jitter

---

## Security & Reliability:

- **Authentication**: Session-based login required for web routes
- **Device Auth**: Username-based verification for ESP32 endpoints
- **Data Validation**: File type/size checks, dosage count validation
- **Error Handling**: Try-catch with rollback for database operations
- **State Recovery**: Heartbeat mechanism to detect offline devices
- **Idempotency**: Schedule status prevents duplicate dispenses

---

**Generated for**: PharmaBot Medication Management System  
**Date**: December 10, 2025  
**Version**: 1.0  
**Architecture**: Flask + ESP32 + Google Gemini AI
