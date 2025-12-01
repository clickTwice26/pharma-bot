"""
API Routes for AJAX requests and ESP32 communication
"""
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json

from app.models import db
from app.models.user import User
from app.models.prescription import Prescription
from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.models.iot_device import IoTDevice
from app.services.gemini_service import GeminiPrescriptionParser
from app.iot.esp32_manager import ESP32Manager

api_bp = Blueprint('api', __name__, url_prefix='/api')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required_api(f):
    """Decorator for API routes requiring authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@api_bp.route('/prescription/upload', methods=['POST'])
@login_required_api
def upload_prescription():
    """Upload and parse prescription image"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Use PNG, JPG, or JPEG'}), 400
    
    try:
        # Save file
        filename = secure_filename(f"{session['user_id']}_{datetime.utcnow().timestamp()}_{file.filename}")
        upload_folder = os.path.join('app', 'static', 'uploads', 'prescriptions')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Parse with Gemini AI
        parser = GeminiPrescriptionParser()
        parsed_data = parser.parse_prescription(filepath)
        
        # Validate parsed data
        is_valid, message = parser.validate_parsed_data(parsed_data)
        
        if not is_valid:
            return jsonify({'error': message, 'raw_data': parsed_data}), 400
        
        # Save prescription to database
        prescription = Prescription(
            user_id=session['user_id'],
            image_path=f'uploads/prescriptions/{filename}',
            parsed_data=json.dumps(parsed_data),
            doctor_name=parsed_data.get('doctor_name'),
            prescription_date=datetime.strptime(parsed_data['prescription_date'], '%Y-%m-%d').date() 
                if parsed_data.get('prescription_date') else None
        )
        db.session.add(prescription)
        db.session.flush()
        
        # Save medicines
        medicines_created = []
        for med_data in parsed_data.get('medicines', []):
            medicine = Medicine(
                prescription_id=prescription.id,
                name=med_data['name'],
                dosage=med_data['dosage'],
                frequency=med_data['frequency'],
                duration=med_data.get('duration'),
                instructions=med_data.get('instructions'),
                timing=med_data.get('timing')
            )
            db.session.add(medicine)
            medicines_created.append(med_data['name'])
            
            # Create schedules
            create_schedules_for_medicine(medicine, session['user_id'], parser)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'prescription_id': prescription.id,
            'medicines': medicines_created,
            'parsed_data': parsed_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def create_schedules_for_medicine(medicine, user_id, parser):
    """Create medication schedules based on frequency"""
    times = parser.extract_timing_from_frequency(medicine.frequency)
    
    # Parse duration to get number of days
    duration_days = parse_duration(medicine.duration) if medicine.duration else 7
    
    # Create schedules for the duration
    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for day in range(duration_days):
        schedule_date = start_date + timedelta(days=day)
        for time_str in times:
            hour, minute = map(int, time_str.split(':'))
            scheduled_time = schedule_date.replace(hour=hour, minute=minute)
            
            schedule = Schedule(
                medicine_id=medicine.id,
                user_id=user_id,
                scheduled_time=scheduled_time
            )
            db.session.add(schedule)


def parse_duration(duration_str):
    """Parse duration string to number of days"""
    duration_str = duration_str.lower()
    
    if 'day' in duration_str:
        return int(''.join(filter(str.isdigit, duration_str)) or 7)
    elif 'week' in duration_str:
        weeks = int(''.join(filter(str.isdigit, duration_str)) or 1)
        return weeks * 7
    elif 'month' in duration_str:
        months = int(''.join(filter(str.isdigit, duration_str)) or 1)
        return months * 30
    
    return 7  # Default to 7 days


@api_bp.route('/schedule/<int:schedule_id>/mark-taken', methods=['POST'])
@login_required_api
def mark_taken(schedule_id):
    """Mark a scheduled dose as taken"""
    schedule = Schedule.query.filter_by(
        id=schedule_id,
        user_id=session['user_id']
    ).first()
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    schedule.taken = True
    schedule.taken_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'schedule': schedule.to_dict()}), 200


@api_bp.route('/schedule/<int:schedule_id>/mark-skipped', methods=['POST'])
@login_required_api
def mark_skipped(schedule_id):
    """Mark a scheduled dose as skipped"""
    schedule = Schedule.query.filter_by(
        id=schedule_id,
        user_id=session['user_id']
    ).first()
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    schedule.skipped = True
    db.session.commit()
    
    return jsonify({'success': True, 'schedule': schedule.to_dict()}), 200


@api_bp.route('/device/register', methods=['POST'])
@login_required_api
def register_device():
    """Register a new ESP32 device"""
    data = request.get_json()
    
    device_id = data.get('device_id')
    device_name = data.get('device_name')
    ip_address = data.get('ip_address')
    
    if not device_id or not device_name:
        return jsonify({'error': 'device_id and device_name are required'}), 400
    
    device = ESP32Manager.register_device(
        user_id=session['user_id'],
        device_id=device_id,
        device_name=device_name,
        ip_address=ip_address
    )
    
    return jsonify({'success': True, 'device': device.to_dict()}), 201


@api_bp.route('/device/<string:device_id>/status', methods=['POST'])
def device_status(device_id):
    """ESP32 device heartbeat/status update"""
    data = request.get_json() or {}
    ip_address = data.get('ip_address') or request.remote_addr
    
    success = ESP32Manager.update_device_status(
        device_id=device_id,
        is_online=True,
        ip_address=ip_address
    )
    
    if success:
        return jsonify({'success': True, 'message': 'Status updated'}), 200
    else:
        return jsonify({'error': 'Device not found'}), 404


@api_bp.route('/device/<string:device_id>/notify', methods=['POST'])
@login_required_api
def notify_device(device_id):
    """Send notification to ESP32 device"""
    data = request.get_json()
    
    medicine_name = data.get('medicine_name')
    dosage = data.get('dosage')
    instructions = data.get('instructions', '')
    
    result = ESP32Manager.send_notification(
        device_id=device_id,
        medicine_name=medicine_name,
        dosage=dosage,
        instructions=instructions
    )
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@api_bp.route('/device/<string:device_id>/dispense', methods=['POST'])
@login_required_api
def dispense_medicine(device_id):
    """Command ESP32 to dispense medicine"""
    data = request.get_json()
    
    compartment = data.get('compartment', 1)
    medicine_name = data.get('medicine_name', 'Medicine')
    
    result = ESP32Manager.send_dispense_command(
        device_id=device_id,
        compartment_number=compartment,
        medicine_name=medicine_name
    )
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@api_bp.route('/dashboard/stats', methods=['GET'])
@login_required_api
def dashboard_stats():
    """Get dashboard statistics"""
    user_id = session['user_id']
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    stats = {
        'total_prescriptions': Prescription.query.filter_by(user_id=user_id).count(),
        'active_medicines': Medicine.query.join(Prescription).filter(
            Prescription.user_id == user_id,
            Medicine.is_active == True
        ).count(),
        'today_total': Schedule.query.filter(
            Schedule.user_id == user_id,
            Schedule.scheduled_time >= today_start,
            Schedule.scheduled_time < today_end
        ).count(),
        'today_taken': Schedule.query.filter(
            Schedule.user_id == user_id,
            Schedule.scheduled_time >= today_start,
            Schedule.scheduled_time < today_end,
            Schedule.taken == True
        ).count(),
        'devices_online': IoTDevice.query.filter_by(
            user_id=user_id,
            is_online=True,
            is_active=True
        ).count()
    }
    
    return jsonify(stats), 200
