from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.medical_check import MedicalRecordCheck
from app.models.task import Task
from app.models.user import User
from app.utils.check_catalog import CHECK_CATEGORY_OPTIONS, build_check_statistics, get_check_category_label, normalize_check_category
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from datetime import date, datetime, timedelta

checks_bp = Blueprint("checks", __name__)

CHECK_QUERY_OPTIONS = (
    joinedload(MedicalRecordCheck.creator),
    joinedload(MedicalRecordCheck.responsible_doctor),
    joinedload(MedicalRecordCheck.rectifier),
)


def _current_user():
    uid = int(get_jwt_identity())
    return db.session.get(User, uid)


def _normalize_payload(data):
    payload = dict(data or {})
    payload["issue_category"] = normalize_check_category(payload.get("issue_category"))
    payload["issue_template"] = (payload.get("issue_template") or "").strip()
    payload["issue_found"] = (payload.get("issue_found") or "").strip()
    payload["remarks"] = (payload.get("remarks") or "").strip()
    payload["rectification_feedback"] = (payload.get("rectification_feedback") or "").strip()
    return payload


def _parse_doctor_id(value):
    if value in (None, "", 0):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("责任医师格式不正确")


def _ensure_doctor(doctor_id):
    if not doctor_id:
        return None
    doctor = db.session.get(User, doctor_id)
    if not doctor or not doctor.is_active or doctor.role != "doctor":
        raise ValueError("请选择有效的管床医师")
    return doctor


def _check_permission(user, target_doctor_id):
    if user.role == "doctor" and target_doctor_id == user.id:
        raise ValueError("默认不能检查本人负责的病历")


def _build_rectification_task_title(item):
    label = get_check_category_label(item.issue_category)
    subject = item.record_no or item.patient_name or "病历"
    return f"病历问题整改 {subject}（{label}）"


def _build_rectification_task_description(item):
    return "\n".join([
        f"病案号：{item.record_no or '未填写'}",
        f"患者姓名：{item.patient_name or '未填写'}",
        f"问题分类：{get_check_category_label(item.issue_category)}",
        f"预设问题：{item.issue_template or '未选择'}",
        f"发现问题：{item.issue_found or '未填写'}",
        f"严重程度：{'严重问题' if item.severity == 'serious' else '一般问题'}",
        f"检查日期：{item.check_date.isoformat() if item.check_date else ''}",
    ])


def _rectification_deadline(item):
    if item.task and item.task.deadline and item.task.deadline >= date.today():
        return item.task.deadline
    return item.check_date + timedelta(days=7)


def _sync_rectification_task(item, creator_id):
    if not item.responsible_doctor_id or item.is_rectified:
        if item.rectification_task and item.rectification_task.status != "completed":
            item.rectification_task.status = "completed"
        return

    title = _build_rectification_task_title(item)
    description = _build_rectification_task_description(item)
    deadline = _rectification_deadline(item)

    if item.rectification_task:
        task = item.rectification_task
        task.title = title
        task.description = description
        task.assigned_to = item.responsible_doctor_id
        task.deadline = deadline
        if task.status == "completed" and not item.is_rectified:
            task.status = "pending"
        return

    task = Task(
        type="check",
        title=title,
        description=description,
        assigned_to=item.responsible_doctor_id,
        deadline=deadline,
        status="pending",
        created_by=creator_id,
    )
    db.session.add(task)
    db.session.flush()
    item.rectification_task_id = task.id


def _set_rectified(item, user):
    item.rectification_status = "rectified"
    item.is_rectified = True
    item.rectified_by = user.id
    item.rectified_at = datetime.now()
    item.rectified_date = item.rectified_at.date()
    if item.rectification_task:
        item.rectification_task.status = "completed"


def _set_pending(item):
    item.rectification_status = "pending"
    item.is_rectified = False
    item.rectified_by = None
    item.rectified_at = None
    item.rectified_date = None
    if item.rectification_task and item.rectification_task.status == "completed":
        item.rectification_task.status = "pending"


def _apply_full_update(item, payload):
    for field in ["record_no", "patient_name", "issue_template", "issue_found", "severity", "remarks", "rectification_feedback"]:
        if field in payload:
            setattr(item, field, payload[field])
    if "issue_category" in payload:
        item.issue_category = normalize_check_category(payload.get("issue_category"))
    if "check_date" in payload:
        item.check_date = date.fromisoformat(payload["check_date"])
    if "task_id" in payload:
        item.task_id = payload.get("task_id")
    if "responsible_doctor_id" in payload:
        item.responsible_doctor_id = _parse_doctor_id(payload.get("responsible_doctor_id"))


@checks_bp.route("/meta", methods=["GET"])
@jwt_required()
def checks_meta():
    doctors = User.query.filter_by(role="doctor", is_active=True).order_by(User.real_name.asc()).all()
    user = _current_user()
    return jsonify({
        "categories": CHECK_CATEGORY_OPTIONS,
        "doctors": [doctor.to_dict() for doctor in doctors],
        "current_user": user.to_dict() if user else None,
    })


@checks_bp.route("/stats", methods=["GET"])
@jwt_required()
def check_stats():
    start = request.args.get("start")
    end = request.args.get("end")
    user = _current_user()

    query = MedicalRecordCheck.query.options(*CHECK_QUERY_OPTIONS)
    if user.role != "admin":
        query = query.filter(or_(
            MedicalRecordCheck.created_by == user.id,
            MedicalRecordCheck.responsible_doctor_id == user.id,
            MedicalRecordCheck.rectified_by == user.id,
        ))
    if start:
        query = query.filter(MedicalRecordCheck.check_date >= date.fromisoformat(start))
    if end:
        query = query.filter(MedicalRecordCheck.check_date <= date.fromisoformat(end))
    items = query.order_by(MedicalRecordCheck.check_date.desc()).all()
    return jsonify(build_check_statistics(items))


@checks_bp.route("", methods=["GET"])
@jwt_required()
def list_checks():
    user = _current_user()
    start = request.args.get("start")
    end = request.args.get("end")
    task_id = request.args.get("task_id")
    query = MedicalRecordCheck.query.options(*CHECK_QUERY_OPTIONS)
    if user.role != "admin":
        query = query.filter(or_(
            MedicalRecordCheck.created_by == user.id,
            MedicalRecordCheck.responsible_doctor_id == user.id,
            MedicalRecordCheck.rectified_by == user.id,
        ))
    if task_id:
        try:
            task_id_value = int(task_id)
        except ValueError:
            return jsonify({"msg": "任务参数不正确"}), 400
        query = query.filter(or_(
            MedicalRecordCheck.task_id == task_id_value,
            MedicalRecordCheck.rectification_task_id == task_id_value,
        ))
    if start:
        query = query.filter(MedicalRecordCheck.check_date >= date.fromisoformat(start))
    if end:
        query = query.filter(MedicalRecordCheck.check_date <= date.fromisoformat(end))
    items = query.order_by(MedicalRecordCheck.check_date.desc()).all()
    return jsonify([i.to_dict() for i in items])


@checks_bp.route("", methods=["POST"])
@jwt_required()
def create_check():
    payload = _normalize_payload(request.get_json())
    user = _current_user()

    try:
        responsible_doctor_id = _parse_doctor_id(payload.get("responsible_doctor_id"))
        _ensure_doctor(responsible_doctor_id)
        _check_permission(user, responsible_doctor_id)
    except ValueError as exc:
        return jsonify({"msg": str(exc)}), 400

    item = MedicalRecordCheck(
        task_id=payload.get("task_id"),
        check_date=date.fromisoformat(payload["check_date"]),
        record_no=payload.get("record_no", ""),
        patient_name=payload.get("patient_name", ""),
        responsible_doctor_id=responsible_doctor_id,
        issue_category=payload.get("issue_category", "other"),
        issue_template=payload.get("issue_template", ""),
        issue_found=payload.get("issue_found", ""),
        severity=payload.get("severity", "general"),
        rectification_status="pending",
        rectification_feedback=payload.get("rectification_feedback", ""),
        is_rectified=False,
        remarks=payload.get("remarks", ""),
        created_by=user.id,
    )
    db.session.add(item)
    db.session.flush()

    if payload.get("is_rectified") or payload.get("rectification_status") == "rectified":
        _set_rectified(item, user)
    else:
        _sync_rectification_task(item, user.id)

    if item.task_id:
        task = db.session.get(Task, item.task_id)
        if task:
            task.status = "completed"

    db.session.commit()
    return jsonify(item.to_dict()), 201


@checks_bp.route("/<int:cid>", methods=["GET"])
@jwt_required()
def get_check(cid):
    item = db.session.get(MedicalRecordCheck, cid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    return jsonify(item.to_dict())


@checks_bp.route("/<int:cid>", methods=["PUT"])
@jwt_required()
def update_check(cid):
    item = db.session.get(MedicalRecordCheck, cid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    payload = _normalize_payload(request.get_json())
    user = _current_user()
    is_admin = user.role == "admin"
    is_creator = item.created_by == user.id
    is_responsible_doctor = item.responsible_doctor_id == user.id

    if not (is_admin or is_creator or is_responsible_doctor):
        return jsonify({"msg": "没有权限修改该记录"}), 403

    if is_admin or is_creator:
        try:
            if "responsible_doctor_id" in payload:
                doctor_id = _parse_doctor_id(payload.get("responsible_doctor_id"))
                _ensure_doctor(doctor_id)
                _check_permission(user, doctor_id)
            _apply_full_update(item, payload)
        except ValueError as exc:
            return jsonify({"msg": str(exc)}), 400

    if "rectification_feedback" in payload:
        item.rectification_feedback = payload.get("rectification_feedback", "")

    target_status = payload.get("rectification_status")
    if payload.get("is_rectified") is True:
        target_status = "rectified"
    elif payload.get("is_rectified") is False and target_status is None:
        target_status = "pending"

    if target_status == "rectified":
        if not (is_admin or is_responsible_doctor):
            return jsonify({"msg": "只有责任医师或管理员可以确认整改"}), 403
        _set_rectified(item, user)
    elif target_status == "pending":
        if is_admin or is_creator:
            _set_pending(item)

    if not item.is_rectified:
        _sync_rectification_task(item, item.created_by)

    db.session.commit()
    return jsonify(item.to_dict())


@checks_bp.route("/<int:cid>", methods=["DELETE"])
@jwt_required()
def delete_check(cid):
    item = db.session.get(MedicalRecordCheck, cid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    user = _current_user()
    if user.role != "admin" and item.created_by != user.id:
        return jsonify({"msg": "没有权限删除该记录"}), 403
    if item.rectification_task and item.rectification_task.status != "completed":
        item.rectification_task.status = "completed"
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "已删除"})
