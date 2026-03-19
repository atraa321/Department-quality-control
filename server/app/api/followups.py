from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import joinedload

from app import db
from app.models.followup import PatientFollowup
from app.models.patient import DischargedPatient
from app.models.user import User
from datetime import date

followups_bp = Blueprint("followups", __name__)


@followups_bp.route("", methods=["GET"])
@jwt_required()
def list_followups():
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    query = PatientFollowup.query.options(
        joinedload(PatientFollowup.patient),
        joinedload(PatientFollowup.user),
    )
    # 非管理员只看自己的回访
    if user.role != "admin":
        query = query.filter_by(followup_by=uid)

    start = request.args.get("start")
    end = request.args.get("end")
    role_filter = request.args.get("role")
    if start:
        query = query.filter(PatientFollowup.followup_date >= date.fromisoformat(start))
    if end:
        query = query.filter(PatientFollowup.followup_date <= date.fromisoformat(end))
    if role_filter:
        query = query.filter_by(followup_role=role_filter)

    items = query.order_by(PatientFollowup.followup_date.desc()).all()
    return jsonify([i.to_dict() for i in items])


@followups_bp.route("", methods=["POST"])
@jwt_required()
def create_followup():
    data = request.get_json()
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    # 验证患者存在
    patient = db.session.get(DischargedPatient, data.get("patient_id"))
    if not patient:
        return jsonify({"msg": "患者不存在"}), 404

    # 医师只能回访自己的患者
    if user.role == "doctor" and patient.attending_doctor != user.real_name:
        return jsonify({"msg": "只能回访自己的出院患者"}), 403

    role = "nurse" if user.role == "nurse" else "doctor"

    item = PatientFollowup(
        patient_id=data["patient_id"],
        followup_date=date.fromisoformat(data["followup_date"]),
        followup_method=data.get("followup_method", "phone"),
        feedback=data.get("feedback", ""),
        satisfaction=data.get("satisfaction", 5),
        suggestions=data.get("suggestions", ""),
        needs_attention=data.get("needs_attention", False),
        followup_by=uid,
        followup_role=role,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@followups_bp.route("/<int:fid>", methods=["GET"])
@jwt_required()
def get_followup(fid):
    item = db.session.get(PatientFollowup, fid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    return jsonify(item.to_dict())


@followups_bp.route("/<int:fid>", methods=["PUT"])
@jwt_required()
def update_followup(fid):
    item = db.session.get(PatientFollowup, fid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404

    data = request.get_json()
    for field in ["followup_method", "feedback", "satisfaction", "suggestions", "needs_attention"]:
        if field in data:
            setattr(item, field, data[field])
    if "followup_date" in data:
        item.followup_date = date.fromisoformat(data["followup_date"])
    db.session.commit()
    return jsonify(item.to_dict())


@followups_bp.route("/<int:fid>", methods=["DELETE"])
@jwt_required()
def delete_followup(fid):
    item = db.session.get(PatientFollowup, fid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "已删除"})


@followups_bp.route("/stats", methods=["GET"])
@jwt_required()
def followup_stats():
    """按护士统计回访工作量"""
    start = request.args.get("start")
    end = request.args.get("end")

    query = db.session.query(
        PatientFollowup.followup_by,
        User.real_name,
        PatientFollowup.followup_role,
        db.func.count(PatientFollowup.id),
        db.func.avg(PatientFollowup.satisfaction),
    ).join(User, PatientFollowup.followup_by == User.id)

    if start:
        query = query.filter(PatientFollowup.followup_date >= date.fromisoformat(start))
    if end:
        query = query.filter(PatientFollowup.followup_date <= date.fromisoformat(end))

    rows = query.group_by(
        PatientFollowup.followup_by, User.real_name, PatientFollowup.followup_role
    ).all()

    return jsonify([
        {
            "user_id": r[0],
            "real_name": r[1],
            "role": r[2],
            "count": r[3],
            "avg_satisfaction": round(r[4], 2) if r[4] else 0,
        }
        for r in rows
    ])
