from app import db
from datetime import datetime


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32), nullable=False)  # discussion/study/check/followup
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, default="")
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(16), default="pending")  # pending/in_progress/completed/overdue
    carryover_source_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    assignee = db.relationship("User", foreign_keys=[assigned_to], backref="assigned_tasks")
    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        linked_check = None
        check_task_kind = None
        if hasattr(self, "rectification_records") and self.rectification_records:
            linked_check = self.rectification_records[0]
            check_task_kind = "rectification"
        elif hasattr(self, "scheduled_checks") and self.scheduled_checks:
            linked_check = self.scheduled_checks[0]
            check_task_kind = "scheduled"

        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.real_name if self.assignee else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
            "carryover_source_id": self.carryover_source_id,
            "is_carryover": bool(self.carryover_source_id),
            "linked_check_id": linked_check.id if linked_check else None,
            "check_task_kind": check_task_kind,
            "created_by": self.created_by,
            "creator_name": self.creator.real_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
