from app import db
from datetime import datetime
from app.utils.check_catalog import get_check_category_label


class MedicalRecordCheck(db.Model):
    __tablename__ = "medical_record_checks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    check_date = db.Column(db.Date, nullable=False)
    record_no = db.Column(db.String(64), default="")
    patient_name = db.Column(db.String(64), default="")
    responsible_doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    issue_category = db.Column(db.String(64), default="other")
    issue_template = db.Column(db.String(128), default="")
    issue_found = db.Column(db.Text, default="")
    severity = db.Column(db.String(16), default="general")  # general/serious
    rectification_status = db.Column(db.String(16), default="pending")
    rectification_feedback = db.Column(db.Text, default="")
    is_rectified = db.Column(db.Boolean, default=False)
    rectified_date = db.Column(db.Date, nullable=True)
    rectified_at = db.Column(db.DateTime, nullable=True)
    rectified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    rectification_task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    remarks = db.Column(db.Text, default="")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    task = db.relationship("Task", foreign_keys=[task_id], backref="scheduled_checks")
    creator = db.relationship("User", foreign_keys=[created_by], backref="checks")
    responsible_doctor = db.relationship("User", foreign_keys=[responsible_doctor_id], backref="responsible_checks")
    rectifier = db.relationship("User", foreign_keys=[rectified_by], backref="rectified_checks")
    rectification_task = db.relationship("Task", foreign_keys=[rectification_task_id], backref="rectification_records")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "check_date": self.check_date.isoformat() if self.check_date else None,
            "record_no": self.record_no,
            "patient_name": self.patient_name,
            "responsible_doctor_id": self.responsible_doctor_id,
            "responsible_doctor_name": self.responsible_doctor.real_name if self.responsible_doctor else None,
            "issue_category": self.issue_category,
            "issue_category_label": get_check_category_label(self.issue_category),
            "issue_template": self.issue_template,
            "issue_found": self.issue_found,
            "severity": self.severity,
            "rectification_status": self.rectification_status,
            "rectification_feedback": self.rectification_feedback,
            "is_rectified": self.is_rectified,
            "rectified_date": self.rectified_date.isoformat() if self.rectified_date else None,
            "rectified_at": self.rectified_at.isoformat() if self.rectified_at else None,
            "rectified_by": self.rectified_by,
            "rectified_by_name": self.rectifier.real_name if self.rectifier else None,
            "rectification_task_id": self.rectification_task_id,
            "remarks": self.remarks,
            "created_by": self.created_by,
            "creator_name": self.creator.real_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
