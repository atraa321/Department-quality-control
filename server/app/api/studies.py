from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import joinedload

from app import db
from app.models.business_study import BusinessStudy
from app.models.task import Task
from app.utils.export import export_record_to_word
from datetime import date

studies_bp = Blueprint("studies", __name__)

STUDY_QUERY_OPTIONS = (
    joinedload(BusinessStudy.creator),
)


def _parse_participant_count(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _build_study_record_no(item):
    return f"YWXX-{item.study_date.strftime('%Y%m%d')}-{item.id:04d}"


@studies_bp.route("", methods=["GET"])
@jwt_required()
def list_studies():
    start = request.args.get("start")
    end = request.args.get("end")
    query = BusinessStudy.query.options(*STUDY_QUERY_OPTIONS)
    if start:
        query = query.filter(BusinessStudy.study_date >= date.fromisoformat(start))
    if end:
        query = query.filter(BusinessStudy.study_date <= date.fromisoformat(end))
    items = query.order_by(BusinessStudy.study_date.desc()).all()
    return jsonify([i.to_dict() for i in items])


@studies_bp.route("", methods=["POST"])
@jwt_required()
def create_study():
    data = request.get_json()
    uid = int(get_jwt_identity())

    item = BusinessStudy(
        task_id=data.get("task_id"),
        record_no=(data.get("record_no") or "").strip(),
        topic=data.get("topic", ""),
        study_date=date.fromisoformat(data["study_date"]),
        host=data.get("host", ""),
        speaker=data.get("speaker", ""),
        location=data.get("location", ""),
        study_method=data.get("study_method", ""),
        participant_count=_parse_participant_count(data.get("participant_count")),
        content=data.get("content", ""),
        participants=data.get("participants", ""),
        notes=data.get("notes", ""),
        created_by=uid,
    )
    db.session.add(item)
    db.session.flush()

    if not item.record_no:
        item.record_no = _build_study_record_no(item)

    if item.task_id:
        task = db.session.get(Task, item.task_id)
        if task:
            task.status = "completed"

    db.session.commit()
    return jsonify(item.to_dict()), 201


@studies_bp.route("/<int:sid>", methods=["GET"])
@jwt_required()
def get_study(sid):
    item = db.session.get(BusinessStudy, sid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    return jsonify(item.to_dict())


@studies_bp.route("/<int:sid>", methods=["PUT"])
@jwt_required()
def update_study(sid):
    item = db.session.get(BusinessStudy, sid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    data = request.get_json()
    for field in ["record_no", "topic", "host", "speaker", "location", "study_method", "content", "participants", "notes"]:
        if field in data:
            setattr(item, field, data[field])
    if "participant_count" in data:
        item.participant_count = _parse_participant_count(data.get("participant_count"))
    if "study_date" in data:
        item.study_date = date.fromisoformat(data["study_date"])
        if not item.record_no:
            item.record_no = _build_study_record_no(item)
    db.session.commit()
    return jsonify(item.to_dict())


@studies_bp.route("/<int:sid>/export-word", methods=["GET"])
@jwt_required()
def export_study_word(sid):
    item = db.session.get(BusinessStudy, sid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404

    record_no = item.record_no or _build_study_record_no(item)

    metadata_rows = [
        ["记录编号", record_no, "学习日期", item.study_date.isoformat() if item.study_date else ""],
        ["学习主题", item.topic, "学习方式", item.study_method],
        ["主持人", item.host, "主讲人", item.speaker],
        ["参加人数", item.participant_count or "", "学习地点", item.location],
        ["参与人员", item.participants, "记录人", item.creator.real_name if item.creator else ""],
    ]
    sections = [
        {"heading": "学习内容记录", "content": item.content},
        {"heading": "备注与补充说明", "content": item.notes},
    ]
    title = "业务学习记录"
    footer_text = f"文书编号：{record_no}    打印日期：{date.today().isoformat()}"
    output = export_record_to_word(
        title,
        "科室业务学习打印版",
        metadata_rows,
        sections,
        signatures=["记录人签名", "科主任审核", "日期"],
        footer_text=footer_text,
    )
    filename = f"{record_no}_业务学习记录.docx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


@studies_bp.route("/<int:sid>", methods=["DELETE"])
@jwt_required()
def delete_study(sid):
    item = db.session.get(BusinessStudy, sid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "已删除"})
