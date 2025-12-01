"""
IoT Device Manager for ESP32 Communication
Handles device registration, status updates, and medication notifications
"""
import requests
from datetime import datetime
from app.models import db
from app.models.iot_device import IoTDevice


class ESP32Manager:
    """Manager for ESP32 device communication"""
    
    @staticmethod
    def register_device(user_id, device_id, device_name, ip_address=None):
        """Register a new ESP32 device"""
        device = IoTDevice.query.filter_by(device_id=device_id).first()
        
        if device:
            # Update existing device
            device.user_id = user_id
            device.device_name = device_name
            device.ip_address = ip_address
            device.is_online = True
            device.last_seen = datetime.utcnow()
        else:
            # Create new device
            device = IoTDevice(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                ip_address=ip_address,
                is_online=True,
                last_seen=datetime.utcnow()
            )
            db.session.add(device)
        
        db.session.commit()
        return device
    
    @staticmethod
    def update_device_status(device_id, is_online=True, ip_address=None):
        """Update device online status"""
        device = IoTDevice.query.filter_by(device_id=device_id).first()
        
        if device:
            device.is_online = is_online
            device.last_seen = datetime.utcnow()
            if ip_address:
                device.ip_address = ip_address
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def send_notification(device_id, medicine_name, dosage, instructions):
        """Send medication reminder to ESP32 device"""
        device = IoTDevice.query.filter_by(device_id=device_id).first()
        
        if not device or not device.is_online or not device.ip_address:
            return {'success': False, 'error': 'Device not available'}
        
        try:
            # Prepare notification data
            notification_data = {
                'type': 'medication_reminder',
                'medicine': medicine_name,
                'dosage': dosage,
                'instructions': instructions,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send HTTP POST to ESP32
            url = f"http://{device.ip_address}/notify"
            response = requests.post(url, json=notification_data, timeout=5)
            
            if response.status_code == 200:
                return {'success': True, 'response': response.json()}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            # Mark device as offline if unreachable
            device.is_online = False
            db.session.commit()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def send_dispense_command(device_id, compartment_number, medicine_name):
        """Send command to ESP32 to dispense medicine"""
        device = IoTDevice.query.filter_by(device_id=device_id).first()
        
        if not device or not device.is_online or not device.ip_address:
            return {'success': False, 'error': 'Device not available'}
        
        try:
            command_data = {
                'command': 'dispense',
                'compartment': compartment_number,
                'medicine': medicine_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            url = f"http://{device.ip_address}/dispense"
            response = requests.post(url, json=command_data, timeout=5)
            
            if response.status_code == 200:
                return {'success': True, 'response': response.json()}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            device.is_online = False
            db.session.commit()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_user_devices(user_id):
        """Get all devices for a user"""
        devices = IoTDevice.query.filter_by(user_id=user_id, is_active=True).all()
        return [device.to_dict() for device in devices]
    
    @staticmethod
    def remove_device(device_id):
        """Deactivate a device"""
        device = IoTDevice.query.filter_by(device_id=device_id).first()
        if device:
            device.is_active = False
            device.is_online = False
            db.session.commit()
            return True
        return False
