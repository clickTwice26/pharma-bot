"""
API Routes for AJAX requests and ESP32 communication
"""
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
from app.utils.timezone import now as tz_now, today_start as tz_today_start

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
        return jsonify({'error': 'No file provided', 'message': 'Please select a file to upload'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected', 'message': 'Please select a file to upload'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'error': 'Invalid file type',
            'message': 'Please upload a PNG, JPG, or JPEG image file'
        }), 400
    
    try:
        # Save file
        filename = secure_filename(f"{session['user_id']}_{int(tz_now().timestamp())}_{file.filename}")
        upload_folder = os.path.join('app', 'static', 'uploads', 'prescriptions')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Parse with Gemini AI
        parser = GeminiPrescriptionParser()
        parsed_data = parser.parse_prescription(filepath)
        
        # Check for errors in parsing
        if 'error' in parsed_data:
            return jsonify({
                'error': parsed_data.get('error'),
                'message': parsed_data.get('message', 'Failed to parse prescription'),
                'details': parsed_data.get('details', '')
            }), 400
        
        # Validate parsed data
        is_valid, message = parser.validate_parsed_data(parsed_data)
        
        if not is_valid:
            return jsonify({
                'error': 'Validation failed',
                'message': message,
                'raw_data': parsed_data
            }), 400
        
        # Save prescription to database
        prescription = Prescription(
            user_id=session['user_id'],
            image_path=f'uploads/prescriptions/{filename}',
            parsed_data=json.dumps(parsed_data),
            doctor_name=parsed_data.get('doctor_name'),
            prescription_date=datetime.strptime(parsed_data['prescription_date'], '%Y-%m-%d').date() 
                if parsed_data.get('prescription_date') else None,
            patient_name=parsed_data.get('patient_name'),
            patient_age=parsed_data.get('patient_age'),
            patient_gender=parsed_data.get('patient_gender')
        )
        db.session.add(prescription)
        db.session.flush()
        
        # Save medicines
        medicines_created = []
        medicines_list = []
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
            medicines_list.append(medicine)
        
        # Flush to get medicine IDs
        db.session.flush()
        
        # Now create schedules after medicines have IDs
        for medicine in medicines_list:
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


def create_schedules_for_medicine(medicine, user_id, parser, start_date=None):
    """Create medication schedules based on frequency and prescription date"""
    times = parser.extract_timing_from_frequency(medicine.frequency)
    
    # Parse duration to get number of days
    duration_days = parse_duration(medicine.duration) if medicine.duration else 7
    
    # Use prescription date if available, otherwise use today
    if start_date is None:
        # Get prescription date from medicine's prescription
        prescription = Prescription.query.get(medicine.prescription_id)
        if prescription and prescription.prescription_date:
            start_date = tz_today_start().replace(
                year=prescription.prescription_date.year,
                month=prescription.prescription_date.month,
                day=prescription.prescription_date.day
            )
        else:
            start_date = tz_today_start()
    
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
    schedule.taken_at = tz_now()
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


@api_bp.route('/medicine/<int:medicine_id>/schedules', methods=['GET'])
@login_required_api
def get_medicine_schedules(medicine_id):
    """Get all schedules for a specific medicine"""
    user_id = session['user_id']
    
    # Verify medicine belongs to user
    medicine = Medicine.query.join(Prescription).filter(
        Medicine.id == medicine_id,
        Prescription.user_id == user_id
    ).first()
    
    if not medicine:
        return jsonify({'error': 'Medicine not found'}), 404
    
    schedules = Schedule.query.filter_by(
        medicine_id=medicine_id,
        user_id=user_id
    ).order_by(Schedule.scheduled_time).all()
    
    return jsonify({
        'success': True,
        'medicine': medicine.to_dict(),
        'schedules': [s.to_dict() for s in schedules]
    }), 200


@api_bp.route('/medicine/<int:medicine_id>/regenerate-schedules', methods=['POST'])
@login_required_api
def regenerate_schedules(medicine_id):
    """Regenerate schedules for a medicine from a specific date"""
    user_id = session['user_id']
    data = request.get_json() or {}
    
    # Verify medicine belongs to user
    medicine = Medicine.query.join(Prescription).filter(
        Medicine.id == medicine_id,
        Prescription.user_id == user_id
    ).first()
    
    if not medicine:
        return jsonify({'error': 'Medicine not found'}), 404
    
    try:
        # Get start date from request or use prescription date
        start_date_str = data.get('start_date')
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            prescription = Prescription.query.get(medicine.prescription_id)
            if prescription and prescription.prescription_date:
                start_date = tz_today_start().replace(
                    year=prescription.prescription_date.year,
                    month=prescription.prescription_date.month,
                    day=prescription.prescription_date.day
                )
            else:
                start_date = tz_today_start()
        
        # Delete existing future schedules (keep historical ones)
        Schedule.query.filter(
            Schedule.medicine_id == medicine_id,
            Schedule.user_id == user_id,
            Schedule.scheduled_time >= tz_now(),
            Schedule.taken == False
        ).delete()
        
        # Create new schedules
        parser = GeminiPrescriptionParser()
        create_schedules_for_medicine(medicine, user_id, parser, start_date)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedules regenerated successfully',
            'start_date': start_date.strftime('%Y-%m-%d')
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/prescription/<int:prescription_id>/auto-assign-slots', methods=['POST'])
@login_required_api
def auto_assign_slots(prescription_id):
    """Auto-assign available compartment slots to medicines"""
    user_id = session['user_id']
    
    # Verify prescription belongs to user
    prescription = Prescription.query.filter_by(
        id=prescription_id,
        user_id=user_id
    ).first()
    
    if not prescription:
        return jsonify({'error': 'Prescription not found'}), 404
    
    try:
        # Get all medicines for this prescription
        medicines = Medicine.query.filter_by(
            prescription_id=prescription_id,
            is_active=True
        ).order_by(Medicine.id).all()
        
        if not medicines:
            return jsonify({'error': 'No medicines found'}), 404
        
        # Available slots (1-3)
        available_slots = [1, 2, 3]
        assigned_count = 0
        unassigned_count = 0
        
        for medicine in medicines:
            if available_slots:
                # Assign the next available slot
                slot = available_slots.pop(0)
                medicine.compartment_number = slot
                assigned_count += 1
            else:
                # Mark as not enough slots (use 0 or None)
                medicine.compartment_number = 0
                unassigned_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
            'message': f'Assigned {assigned_count} medicines, {unassigned_count} without slots'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/schedule/<int:schedule_id>', methods=['PUT'])
@login_required_api
def update_schedule(schedule_id):
    """Update a specific schedule's time"""
    user_id = session['user_id']
    data = request.get_json()
    
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    if schedule.taken:
        return jsonify({'error': 'Cannot edit a schedule that has been taken'}), 400
    
    try:
        # Update scheduled time
        new_time_str = data.get('scheduled_time')
        if new_time_str:
            new_time = datetime.strptime(new_time_str, '%Y-%m-%d %H:%M')
            schedule.scheduled_time = new_time
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'schedule': schedule.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_bp.route('/schedule/<int:schedule_id>', methods=['DELETE'])
@login_required_api
def delete_schedule(schedule_id):
    """Delete a specific schedule"""
    user_id = session['user_id']
    
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    if schedule.taken:
        return jsonify({'error': 'Cannot delete a schedule that has been taken'}), 400
    
    db.session.delete(schedule)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Schedule deleted successfully'}), 200


@api_bp.route('/device/register', methods=['POST'])
def register_device():
    """Register a new Arduino/ESP32 device (no auth required for device)"""
    data = request.get_json()
    
    device_id = data.get('device_id')
    device_name = data.get('device_name')
    ip_address = data.get('ip_address')
    username = data.get('username')
    
    if not device_id or not device_name or not username:
        return jsonify({'error': 'device_id, device_name, and username are required'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    device = IoTDevice.query.filter_by(device_id=device_id, user_id=user.id).first()
    
    if device:
        device.device_name = device_name
        device.ip_address = ip_address
        device.last_seen = tz_now()
        device.is_online = True
    else:
        device = IoTDevice(
            user_id=user.id,
            device_id=device_id,
            device_name=device_name,
            device_type='Arduino',
            ip_address=ip_address,
            is_online=True,
            last_seen=tz_now()
        )
        db.session.add(device)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Device registered successfully',
        'device_id': device_id
    }), 200


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


@api_bp.route('/prescription/<int:prescription_id>', methods=['DELETE'])
@login_required_api
def delete_prescription(prescription_id):
    """Delete a prescription and all associated data"""
    try:
        user_id = session['user_id']
        
        # Get prescription and verify ownership
        prescription = Prescription.query.filter_by(
            id=prescription_id,
            user_id=user_id
        ).first()
        
        if not prescription:
            return jsonify({
                'error': 'Not found',
                'message': 'Prescription not found or you do not have permission to delete it'
            }), 404
        
        # Delete associated schedules first
        Schedule.query.filter(
            Schedule.medicine_id.in_(
                db.session.query(Medicine.id).filter(Medicine.prescription_id == prescription_id)
            )
        ).delete(synchronize_session=False)
        
        # Delete associated medicines
        Medicine.query.filter_by(prescription_id=prescription_id).delete()
        
        # Delete the prescription image file
        if prescription.image_path:
            try:
                image_full_path = os.path.join('app', 'static', prescription.image_path)
                if os.path.exists(image_full_path):
                    os.remove(image_full_path)
            except Exception as e:
                print(f"Error deleting image file: {str(e)}")
        
        # Delete the prescription
        db.session.delete(prescription)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Prescription deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Deletion failed',
            'message': str(e)
        }), 500


@api_bp.route('/dashboard/stats', methods=['GET'])
@login_required_api
def dashboard_stats():
    """Get dashboard statistics"""
    user_id = session['user_id']
    
    today_start = tz_today_start()
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


# ==================== ARDUINO/ESP32 DEVICE API ENDPOINTS ====================

@api_bp.route('/device/time', methods=['GET'])
def get_server_time():
    """Get current server timestamp for RTC synchronization"""
    current_time = tz_now()
    return jsonify({
        'timestamp': int(current_time.timestamp()),
        'datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'timezone': 'Asia/Dhaka'
    }), 200


@api_bp.route('/device/schedules', methods=['GET'])
def get_device_schedules():
    """
    Get upcoming schedules for Arduino device
    Query params: username (required)
    Returns schedules for the next 7 days with medicine compartment mapping
    """
    username = request.args.get('username')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Find user by username
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get schedules for next 7 days
    now = tz_now()
    future_date = now + timedelta(days=7)
    
    schedules = Schedule.query.filter(
        Schedule.user_id == user.id,
        Schedule.scheduled_time >= now,
        Schedule.scheduled_time <= future_date,
        Schedule.taken == False
    ).order_by(Schedule.scheduled_time).all()
    
    # Format schedules for Arduino (only include medicines with valid compartment slots)
    schedules_data = []
    for schedule in schedules:
        medicine = schedule.medicine
        # Only include schedules with valid compartment numbers (1-3)
        if medicine.compartment_number and medicine.compartment_number > 0:
            schedules_data.append({
                'schedule_id': schedule.id,
                'medicine_id': medicine.id,
                'medicine_name': medicine.name,
                'dosage': medicine.dosage,
                'instructions': medicine.instructions or '',
                'compartment_number': medicine.compartment_number,
                'scheduled_time': int(schedule.scheduled_time.timestamp()),
                'taken': schedule.taken,
                'skipped': schedule.skipped
            })
    
    return jsonify({
        'success': True,
        'username': username,
        'schedules': schedules_data,
        'count': len(schedules_data),
        'server_time': now.strftime('%Y-%m-%d %H:%M:%S')
    }), 200


@api_bp.route('/device/medicine/update-compartment', methods=['POST'])
def update_medicine_compartment():
    """
    Update compartment number for a medicine
    Used to assign servo motors to medicines
    """
    data = request.get_json()
    
    medicine_id = data.get('medicine_id')
    compartment_number = data.get('compartment_number')
    username = data.get('username')
    
    if not all([medicine_id, compartment_number is not None, username]):
        return jsonify({'error': 'medicine_id, compartment_number, and username are required'}), 400
    
    # Verify user
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get medicine and verify ownership
    medicine = Medicine.query.join(Prescription).filter(
        Medicine.id == medicine_id,
        Prescription.user_id == user.id
    ).first()
    
    if not medicine:
        return jsonify({'error': 'Medicine not found'}), 404
    
    # Update compartment number
    medicine.compartment_number = compartment_number
    db.session.commit()
    
    return jsonify({
        'success': True,
        'medicine': medicine.to_dict()
    }), 200


@api_bp.route('/device/heartbeat', methods=['POST'])
def device_heartbeat():
    """
    Arduino device heartbeat to update last seen timestamp
    """
    data = request.get_json()
    
    device_id = data.get('device_id')
    username = data.get('username')
    
    if not device_id or not username:
        return jsonify({'error': 'device_id and username are required'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update or create device
    device = IoTDevice.query.filter_by(device_id=device_id, user_id=user.id).first()
    
    if device:
        device.last_seen = tz_now()
        device.is_online = True
    else:
        device = IoTDevice(
            user_id=user.id,
            device_id=device_id,
            device_name=data.get('device_name', 'Arduino Dispenser'),
            device_type='Arduino',
            is_online=True,
            last_seen=tz_now()
        )
        db.session.add(device)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Heartbeat received',
        'server_time': tz_now().strftime('%Y-%m-%d %H:%M:%S')
    }), 200


@api_bp.route('/device/dispense', methods=['POST'])
def mark_schedule_dispensed():
    """
    Mark a schedule as dispensed/taken after Arduino dispenses medicine
    """
    data = request.get_json()
    
    schedule_id = data.get('schedule_id')
    device_id = data.get('device_id')
    
    if not schedule_id:
        return jsonify({'error': 'schedule_id is required'}), 400
    
    schedule = Schedule.query.get(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    schedule.taken = True
    schedule.taken_at = tz_now()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Schedule marked as dispensed',
        'schedule_id': schedule_id
    }), 200


@api_bp.route('/device/state', methods=['POST'])
def update_device_state():
    """
    Receive real-time hardware state updates from ESP32
    """
    data = request.get_json()
    device_id = data.get('device_id')
    if not device_id:
        return jsonify({'error': 'device_id is required'}), 400
    
    username = data.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    device = IoTDevice.query.filter_by(
        device_id=device_id,
        user_id=user.id
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Store hardware state in device hardware_state
    device.hardware_state = json.dumps({
        'servo_angles': data.get('servo_angles', [0, 0, 0]),
        'ultrasonic_distance': data.get('ultrasonic_distance', 0),
        'medicine_detected': data.get('medicine_detected', False),
        'led_state': data.get('led_state', False),
        'buzzer_state': data.get('buzzer_state', False),
        'current_operation': data.get('current_operation', 'idle'),
        'last_dispense_time': data.get('last_dispense_time'),
        'timestamp': tz_now().isoformat()
    })
    
    db.session.commit()
    
    return jsonify({'success': True}), 200


@api_bp.route('/device/monitor/<device_id>', methods=['GET'])
@login_required_api
def monitor_device(device_id):
    """
    Get current hardware state for real-time monitoring
    """
    user_id = session.get('user_id')
    
    device = IoTDevice.query.filter_by(
        device_id=device_id,
        user_id=user_id
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Parse hardware state from hardware_state
    hardware_state = {}
    if device.hardware_state:
        try:
            hardware_state = json.loads(device.hardware_state)
        except:
            hardware_state = {}
    
    # Check if device is online (heartbeat within 5 minutes)
    is_online = False
    if device.last_seen:
        time_diff = (tz_now() - device.last_seen).total_seconds()
        is_online = time_diff < 300
    
    return jsonify({
        'device_id': device.device_id,
        'device_name': device.device_name,
        'is_online': is_online,
        'last_seen': device.last_seen.isoformat() if device.last_seen else None,
        'hardware_state': hardware_state
    }), 200


@api_bp.route('/device/simulate', methods=['POST'])
@login_required_api
def simulate_device():
    """
    Simulate device hardware operations for testing
    """
    data = request.get_json()
    
    operation = data.get('operation')
    compartment = data.get('compartment', 1)
    
    if not operation:
        return jsonify({'error': 'operation is required'}), 400
    
    result = {
        'success': True,
        'operation': operation,
        'compartment': compartment,
        'timestamp': tz_now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if operation == 'test_servo':
        result['message'] = f'Servo motor {compartment} tested: 0° → 90° → 180° → 0°'
    elif operation == 'test_ultrasonic':
        result['message'] = 'Ultrasonic sensor tested'
        result['distance'] = 8.5
        result['medicine_detected'] = True
    elif operation == 'test_buzzer':
        result['message'] = 'Buzzer alert played'
    elif operation == 'test_led':
        result['message'] = 'LED indicator tested'
    elif operation == 'dispense':
        result['message'] = f'Medicine dispensed from compartment {compartment}'
    else:
        return jsonify({'error': 'Invalid operation'}), 400
    
    return jsonify(result), 200


@api_bp.route('/device/command', methods=['POST'])
@login_required_api
def send_device_command():
    """
    Send command to ESP32 device for manual control
    """
    data = request.get_json()
    
    device_id = data.get('device_id')
    command = data.get('command')
    
    if not device_id or not command:
        return jsonify({'error': 'device_id and command are required'}), 400
    
    user_id = session.get('user_id')
    device = IoTDevice.query.filter_by(
        device_id=device_id,
        user_id=user_id
    ).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Store command in device hardware_state for ESP32 to fetch
    state_data = {}
    if device.hardware_state:
        try:
            state_data = json.loads(device.hardware_state)
        except:
            state_data = {}
    
    # Add pending command
    if 'pending_commands' not in state_data:
        state_data['pending_commands'] = []
    
    state_data['pending_commands'].append({
        'command': command,
        'params': data.get('params', {}),
        'timestamp': tz_now().isoformat()
    })
    
    device.hardware_state = json.dumps(state_data)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Command {command} sent to device'
    }), 200


@api_bp.route('/device/commands', methods=['GET'])
def get_device_commands():
    """
    ESP32 polls this endpoint to get pending commands
    """
    device_id = request.args.get('device_id')
    username = request.args.get('username')
    
    if not device_id or not username:
        return jsonify({'commands': []}), 200
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'commands': []}), 200
    
    device = IoTDevice.query.filter_by(
        device_id=device_id,
        user_id=user.id
    ).first()
    
    if not device or not device.hardware_state:
        return jsonify({'commands': []}), 200
    
    try:
        state_data = json.loads(device.hardware_state)
        commands = state_data.get('pending_commands', [])
        
        # Clear pending commands after fetching
        state_data['pending_commands'] = []
        device.hardware_state = json.dumps(state_data)
        db.session.commit()
        
        return jsonify({'commands': commands}), 200
    except:
        return jsonify({'commands': []}), 200
