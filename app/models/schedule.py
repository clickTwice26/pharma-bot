from datetime import datetime
from app.models import db


class Schedule(db.Model):
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    taken = db.Column(db.Boolean, default=False)
    taken_at = db.Column(db.DateTime, nullable=True)
    skipped = db.Column(db.Boolean, default=False)
    notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Schedule {self.id} - Medicine {self.medicine_id} at {self.scheduled_time}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'user_id': self.user_id,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'taken': self.taken,
            'taken_at': self.taken_at.isoformat() if self.taken_at else None,
            'skipped': self.skipped,
            'notified': self.notified
        }
