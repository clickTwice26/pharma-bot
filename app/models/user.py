from datetime import datetime
from app.models import db
from app.utils.timezone import now as tz_now


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=tz_now)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    prescriptions = db.relationship('Prescription', backref='user', lazy=True)
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    iot_devices = db.relationship('IoTDevice', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
