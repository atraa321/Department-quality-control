from app import db
from datetime import datetime


class BusinessStudy(db.Model):
    __tablename__ = "business_studies"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    record_no = db.Column(db.String(64), default="")
    topic = db.Column(db.String(256), nullable=False)
    study_date = db.Column(db.Date, nullable=False)
    host = db.Column(db.String(64), default="")
    speaker = db.Column(db.String(64), default="")
    location = db.Column(db.String(128), default="")
    study_method = db.Column(db.String(64), default="")
    participant_count = db.Column(db.Integer, default=0)
    content = db.Column(db.Text, default="")
    participants = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    task = db.relationship("Task", backref="study")
    creator = db.relationship("User", backref="studies")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "record_no": self.record_no,
            "topic": self.topic,
            "study_date": self.study_date.isoformat() if self.study_date else None,
            "host": self.host,
            "speaker": self.speaker,
            "location": self.location,
            "study_method": self.study_method,
            "participant_count": self.participant_count,
            "content": self.content,
            "participants": self.participants,
            "notes": self.notes,
            "created_by": self.created_by,
            "creator_name": self.creator.real_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
