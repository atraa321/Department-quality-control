from datetime import datetime

from sqlalchemy import case, func

from app import db


class DischargedPatient(db.Model):
    __tablename__ = "discharged_patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(64), nullable=False)
    record_no = db.Column(db.String(64), default="")
    gender = db.Column(db.String(8), default="")
    age = db.Column(db.Integer, nullable=True)
    diagnosis = db.Column(db.String(512), default="")
    admission_date = db.Column(db.Date, nullable=True)
    discharge_date = db.Column(db.Date, nullable=True)
    attending_doctor = db.Column(db.String(64), default="")
    import_batch = db.Column(db.String(64), default="")
    imported_at = db.Column(db.DateTime, default=datetime.now)

    followups = db.relationship("PatientFollowup", backref="patient", lazy="dynamic")

    def to_dict(self, followup_status=None):
        followup_status = followup_status or {}
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "record_no": self.record_no,
            "gender": self.gender,
            "age": self.age,
            "diagnosis": self.diagnosis,
            "admission_date": self.admission_date.isoformat() if self.admission_date else None,
            "discharge_date": self.discharge_date.isoformat() if self.discharge_date else None,
            "attending_doctor": self.attending_doctor,
            "import_batch": self.import_batch,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "doctor_followup_done": followup_status.get("doctor_followup_done", self.has_doctor_followup()),
            "nurse_followup_done": followup_status.get("nurse_followup_done", self.has_nurse_followup()),
        }

    def has_doctor_followup(self):
        from app.models.followup import PatientFollowup
        return self.followups.filter_by(followup_role="doctor").count() > 0

    def has_nurse_followup(self):
        from app.models.followup import PatientFollowup
        return self.followups.filter_by(followup_role="nurse").count() > 0


def build_followup_status_map(patient_ids):
    if not patient_ids:
        return {}

    from app.models.followup import PatientFollowup

    status_map = {}
    chunk_size = 800
    for start in range(0, len(patient_ids), chunk_size):
        rows = db.session.query(
            PatientFollowup.patient_id,
            func.max(case((PatientFollowup.followup_role == "doctor", 1), else_=0)).label("doctor_done"),
            func.max(case((PatientFollowup.followup_role == "nurse", 1), else_=0)).label("nurse_done"),
        ).filter(
            PatientFollowup.patient_id.in_(patient_ids[start:start + chunk_size])
        ).group_by(
            PatientFollowup.patient_id
        ).all()

        for row in rows:
            status_map[row.patient_id] = {
                "doctor_followup_done": bool(row.doctor_done),
                "nurse_followup_done": bool(row.nurse_done),
            }
    return status_map
