from app import db
from datetime import datetime


class CaseDiscussion(db.Model):
    __tablename__ = "case_discussions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    record_no = db.Column(db.String(64), default="")
    patient_name = db.Column(db.String(64), default="")
    case_info = db.Column(db.Text, default="")
    diagnosis = db.Column(db.String(256), default="")
    discussion_date = db.Column(db.Date, nullable=False)
    moderator = db.Column(db.String(64), default="")
    speaker = db.Column(db.String(64), default="")
    location = db.Column(db.String(128), default="")
    participant_count = db.Column(db.Integer, default=0)
    discussion_purpose = db.Column(db.String(256), default="")
    discussion_content = db.Column(db.Text, default="")
    participants = db.Column(db.Text, default="")
    conclusion = db.Column(db.Text, default="")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    task = db.relationship("Task", backref="discussion")
    creator = db.relationship("User", backref="discussions")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "record_no": self.record_no,
            "patient_name": self.patient_name,
            "case_info": self.case_info,
            "diagnosis": self.diagnosis,
            "discussion_date": self.discussion_date.isoformat() if self.discussion_date else None,
            "moderator": self.moderator,
            "speaker": self.speaker,
            "location": self.location,
            "participant_count": self.participant_count,
            "discussion_purpose": self.discussion_purpose,
            "discussion_content": self.discussion_content,
            "participants": self.participants,
            "conclusion": self.conclusion,
            "created_by": self.created_by,
            "creator_name": self.creator.real_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
