from datetime import datetime
from app.models import db
from app.utils.timezone import now as tz_now


class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)  # e.g., "500mg", "2 tablets"
    frequency = db.Column(db.String(100), nullable=False)  # e.g., "twice daily", "every 8 hours"
    duration = db.Column(db.String(100), nullable=True)  # e.g., "7 days", "2 weeks"
    instructions = db.Column(db.Text, nullable=True)  # e.g., "Take after meals"
    timing = db.Column(db.String(200), nullable=True)  # e.g., "morning, evening"
    created_at = db.Column(db.DateTime, default=tz_now)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='medicine', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Medicine {self.name} - {self.dosage}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'prescription_id': self.prescription_id,
            'name': self.name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'instructions': self.instructions,
            'timing': self.timing,
            'is_active': self.is_active
        }
