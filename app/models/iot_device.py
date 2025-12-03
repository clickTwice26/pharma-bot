from datetime import datetime
from app.models import db
from app.utils.timezone import now as tz_now


class IoTDevice(db.Model):
    __tablename__ = 'iot_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_id = db.Column(db.String(100), unique=True, nullable=False)  # ESP32 MAC or unique ID
    device_name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), default='ESP32')
    ip_address = db.Column(db.String(50), nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    hardware_state = db.Column(db.Text, nullable=True)  # JSON string for hardware state
    created_at = db.Column(db.DateTime, default=tz_now)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<IoTDevice {self.device_name} - {self.device_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'ip_address': self.ip_address,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_active': self.is_active
        }
