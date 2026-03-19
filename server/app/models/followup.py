from app import db
from datetime import datetime


class PatientFollowup(db.Model):
    __tablename__ = "patient_followups"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("discharged_patients.id"), nullable=False)
    followup_date = db.Column(db.Date, nullable=False)
    followup_method = db.Column(db.String(16), default="phone")  # phone/visit/online
    feedback = db.Column(db.Text, default="")
    satisfaction = db.Column(db.Integer, default=5)  # 1-5
    suggestions = db.Column(db.Text, default="")
    needs_attention = db.Column(db.Boolean, default=False)
    followup_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    followup_role = db.Column(db.String(16), nullable=False)  # doctor/nurse
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", backref="followups")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient.patient_name if self.patient else None,
            "followup_date": self.followup_date.isoformat() if self.followup_date else None,
            "followup_method": self.followup_method,
            "feedback": self.feedback,
            "satisfaction": self.satisfaction,
            "suggestions": self.suggestions,
            "needs_attention": self.needs_attention,
            "followup_by": self.followup_by,
            "followup_by_name": self.user.real_name if self.user else None,
            "followup_role": self.followup_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
