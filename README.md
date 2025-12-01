# PharmaBot - Smart IoT Medication Management System

A comprehensive medication management system with AI-powered prescription parsing, IoT device integration (ESP32), and a beautiful mobile-app-like interface.

## 🌟 Features

### Core Features
- **AI Prescription Parsing**: Uses Google Gemini AI to extract structured data from prescription images
- **Smart Scheduling**: Automatically creates medication schedules based on prescription data
- **IoT Integration**: ESP32 device support for medication dispensing and reminders
- **Mobile-First Design**: Beautiful, responsive UI that looks and feels like a native mobile app
- **Real-time Notifications**: Push notifications to ESP32 devices for medication reminders
- **Simple Authentication**: Username-only registration and login

### Technical Features
- SQLite database with SQLAlchemy ORM
- RESTful API for IoT devices
- File upload with validation
- Real-time device status tracking
- Medication adherence tracking
- Beautiful gradient UI with modern design system

## 📁 Project Structure

```
dld_project_backend/
├── app/
│   ├── models/              # Database models
│   │   ├── user.py         # User model
│   │   ├── prescription.py # Prescription model
│   │   ├── medicine.py     # Medicine model
│   │   ├── schedule.py     # Schedule model
│   │   └── iot_device.py   # IoT device model
│   ├── routes/             # Web routes
│   │   └── main.py         # Main application routes
│   ├── api/                # REST API routes
│   │   └── routes.py       # API endpoints for devices
│   ├── services/           # Business logic
│   │   └── gemini_service.py  # AI prescription parser
│   ├── iot/                # IoT integration
│   │   └── esp32_manager.py   # ESP32 device manager
│   ├── templates/          # Jinja2 templates
│   │   ├── mobile_base.html   # Base mobile template
│   │   ├── dashboard.html     # Home dashboard
│   │   ├── prescriptions.html # Prescriptions list
│   │   ├── prescription_detail.html
│   │   ├── schedules.html     # Medication schedule
│   │   ├── devices.html       # IoT devices management
│   │   ├── profile.html       # User profile
│   │   ├── login.html         # Login page
│   │   └── register.html      # Registration page
│   ├── static/             # Static files
│   │   ├── css/
│   │   │   └── mobile.css     # Mobile-app design system
│   │   ├── js/
│   │   │   └── mobile.js      # Mobile interactions
│   │   └── uploads/
│   │       └── prescriptions/ # Uploaded images
│   ├── __init__.py         # App factory
│   └── config.py           # Configuration
├── instance/               # SQLite database (auto-created)
├── run.py                  # Application entry point (robust)
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- ESP32 device (optional, for IoT features)

### 2. Installation

```bash
# Clone or navigate to project directory
cd dld_project_backend

# Run the application (it will auto-create venv and install dependencies)
python3 run.py
```

The robust run script will automatically:
- Check Python version
- Create virtual environment if needed
- Auto-activate the virtual environment
- Install missing dependencies
- Create database tables
- Start the server on port 7878

### 3. Configuration

Create a `.env` file from the example:
```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your-actual-gemini-api-key-here
```

### 4. Access the Application

Open your browser and navigate to:
```
http://localhost:7878
```

## 📱 Usage Guide

### Getting Started
1. **Register**: Create an account with just a username
2. **Upload Prescription**: Take a photo of your prescription and upload it
3. **AI Processing**: Gemini AI automatically extracts medicine information
4. **Auto-Schedule**: System creates medication schedule automatically
5. **Track Adherence**: Mark doses as taken or skipped

### IoT Device Setup (ESP32)

1. **Flash ESP32**: Upload the PharmaBot firmware to your ESP32
2. **Connect to WiFi**: Configure ESP32 WiFi settings
3. **Get Device ID**: Note the MAC address or unique ID
4. **Register Device**: Add device in the app's Devices section
5. **Auto-Connect**: Device will appear online automatically

## 🔌 API Endpoints

### For ESP32 Devices

#### Register Device
```http
POST /api/device/register
Content-Type: application/json

{
  "device_id": "ESP32-AABBCCDD",
  "device_name": "Bedroom Dispenser",
  "ip_address": "192.168.1.100"
}
```

#### Device Heartbeat
```http
POST /api/device/{device_id}/status
Content-Type: application/json

{
  "ip_address": "192.168.1.100"
}
```

#### Receive Notification (ESP32 endpoint)
```http
POST http://{esp32_ip}/notify
Content-Type: application/json

{
  "type": "medication_reminder",
  "medicine": "Paracetamol",
  "dosage": "500mg",
  "instructions": "Take after meals",
  "timestamp": "2025-12-01T10:00:00"
}
```

#### Dispense Medicine (ESP32 endpoint)
```http
POST http://{esp32_ip}/dispense
Content-Type: application/json

{
  "command": "dispense",
  "compartment": 1,
  "medicine": "Paracetamol",
  "timestamp": "2025-12-01T10:00:00"
}
```

### For Web Interface

#### Upload Prescription
```http
POST /api/prescription/upload
Content-Type: multipart/form-data

file: [prescription_image.jpg]
```

#### Mark Dose as Taken
```http
POST /api/schedule/{schedule_id}/mark-taken
```

#### Get Dashboard Stats
```http
GET /api/dashboard/stats
```

## 🎨 Design System

The app uses a modern, mobile-first design system with:
- **Primary Color**: Indigo (#6366f1)
- **Success Color**: Green (#10b981)
- **Danger Color**: Red (#ef4444)
- **Border Radius**: 8px, 12px, 16px
- **Typography**: System fonts (-apple-system, Segoe UI, Roboto)
- **Layout**: Max width 480px for mobile-app feel
- **Bottom Navigation**: Fixed navigation bar
- **Cards**: Elevated with subtle shadows
- **Gradients**: Beautiful gradient backgrounds

## 🤖 AI Integration

### Gemini AI Prescription Parser

The system uses Google's Gemini 1.5 Flash model to:
1. Analyze prescription images
2. Extract doctor name and date
3. Identify all medicines
4. Parse dosage, frequency, duration
5. Extract special instructions
6. Determine timing (morning, evening, etc.)

### Extracted Data Schema
```json
{
  "doctor_name": "Dr. Smith",
  "prescription_date": "2025-12-01",
  "medicines": [
    {
      "name": "Paracetamol",
      "dosage": "500mg",
      "frequency": "three times daily",
      "duration": "5 days",
      "instructions": "Take after meals with water",
      "timing": "morning, afternoon, evening"
    }
  ]
}
```

## 📊 Database Schema

### Models
- **User**: Username, email, created_at
- **Prescription**: User reference, image path, parsed data
- **Medicine**: Prescription reference, name, dosage, frequency, duration
- **Schedule**: Medicine reference, scheduled time, taken status
- **IoTDevice**: User reference, device ID, IP address, online status

## 🔧 Development

### Run in Development Mode
```bash
python3 run.py
```

### Database Migrations
The app automatically creates tables on first run.

### Adding New Features
1. Models: Add to `app/models/`
2. Routes: Add to `app/routes/` or `app/api/`
3. Services: Add business logic to `app/services/`
4. Templates: Add to `app/templates/`
5. Styles: Update `app/static/css/mobile.css`

## 🛡️ Security Notes

- Change `SECRET_KEY` in production
- Keep `GEMINI_API_KEY` secret
- Use HTTPS in production
- Validate all file uploads
- Sanitize user inputs
- Implement rate limiting for API

## 📝 TODO / Future Enhancements

- [ ] Password authentication (optional)
- [ ] Email notifications
- [ ] SMS reminders via Twilio
- [ ] Multiple language support
- [ ] Dark mode theme
- [ ] Export medication history
- [ ] Family member accounts
- [ ] Pharmacy integration
- [ ] Medication interaction warnings
- [ ] Barcode scanning for medicines
- [ ] Voice reminders on ESP32
- [ ] Progressive Web App (PWA) support

## 🐛 Troubleshooting

### Common Issues

**Gemini API Error**:
- Ensure GEMINI_API_KEY is set correctly in .env
- Check API key has quota remaining
- Verify image is clear and readable

**ESP32 Not Connecting**:
- Check device is on same network
- Verify IP address is correct
- Ensure firewall allows port 7878
- Check ESP32 WiFi credentials

**Upload Fails**:
- Check file size (max 16MB)
- Use supported formats (PNG, JPG, JPEG)
- Ensure uploads directory exists and is writable

## 📜 License

MIT License - Feel free to use this project for personal or commercial purposes.

## 👥 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📧 Support

For support, please open an issue on the repository or contact the development team.

---

**Built with ❤️ using Flask, Gemini AI, and ESP32**
