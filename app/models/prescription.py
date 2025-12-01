from datetime import datetime
from app.models import db
from app.utils.timezone import now as tz_now


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    parsed_data = db.Column(db.Text, nullable=True)  # JSON string
    doctor_name = db.Column(db.String(100), nullable=True)
    prescription_date = db.Column(db.Date, nullable=True)
    patient_name = db.Column(db.String(100), nullable=True)
    patient_age = db.Column(db.String(20), nullable=True)
    patient_gender = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=tz_now)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    medicines = db.relationship('Medicine', backref='prescription', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Prescription {self.id} - User {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_path': self.image_path,
            'doctor_name': self.doctor_name,
            'prescription_date': self.prescription_date.isoformat() if self.prescription_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
