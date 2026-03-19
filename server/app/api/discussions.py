from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import joinedload

from app import db
from app.models.case_discussion import CaseDiscussion
from app.models.task import Task
from app.utils.export import export_record_to_word
from datetime import date

discussions_bp = Blueprint("discussions", __name__)

DISCUSSION_QUERY_OPTIONS = (
    joinedload(CaseDiscussion.creator),
)


def _parse_participant_count(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _build_discussion_record_no(item):
    return f"YNBL-{item.discussion_date.strftime('%Y%m%d')}-{item.id:04d}"


@discussions_bp.route("", methods=["GET"])
@jwt_required()
def list_discussions():
    start = request.args.get("start")
    end = request.args.get("end")
    query = CaseDiscussion.query.options(*DISCUSSION_QUERY_OPTIONS)
    if start:
        query = query.filter(CaseDiscussion.discussion_date >= date.fromisoformat(start))
    if end:
        query = query.filter(CaseDiscussion.discussion_date <= date.fromisoformat(end))
    items = query.order_by(CaseDiscussion.discussion_date.desc()).all()
    return jsonify([i.to_dict() for i in items])


@discussions_bp.route("", methods=["POST"])
@jwt_required()
def create_discussion():
    data = request.get_json()
    uid = int(get_jwt_identity())

    item = CaseDiscussion(
        task_id=data.get("task_id"),
        record_no=(data.get("record_no") or "").strip(),
        patient_name=data.get("patient_name", ""),
        case_info=data.get("case_info", ""),
        diagnosis=data.get("diagnosis", ""),
        discussion_date=date.fromisoformat(data["discussion_date"]),
        moderator=data.get("moderator", ""),
        speaker=data.get("speaker", ""),
        location=data.get("location", ""),
        participant_count=_parse_participant_count(data.get("participant_count")),
        discussion_purpose=data.get("discussion_purpose", ""),
        discussion_content=data.get("discussion_content", ""),
        participants=data.get("participants", ""),
        conclusion=data.get("conclusion", ""),
        created_by=uid,
    )
    db.session.add(item)
    db.session.flush()

    if not item.record_no:
        item.record_no = _build_discussion_record_no(item)

    # 关联任务自动完成
    if item.task_id:
        task = db.session.get(Task, item.task_id)
        if task:
            task.status = "completed"

    db.session.commit()
    return jsonify(item.to_dict()), 201


@discussions_bp.route("/<int:did>", methods=["GET"])
@jwt_required()
def get_discussion(did):
    item = db.session.get(CaseDiscussion, did)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    return jsonify(item.to_dict())


@discussions_bp.route("/<int:did>", methods=["PUT"])
@jwt_required()
def update_discussion(did):
    item = db.session.get(CaseDiscussion, did)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    data = request.get_json()
    for field in ["record_no", "patient_name", "case_info", "diagnosis", "moderator", "speaker", "location", "discussion_purpose", "discussion_content", "participants", "conclusion"]:
        if field in data:
            setattr(item, field, data[field])
    if "participant_count" in data:
        item.participant_count = _parse_participant_count(data.get("participant_count"))
    if "discussion_date" in data:
        item.discussion_date = date.fromisoformat(data["discussion_date"])
        if not item.record_no:
            item.record_no = _build_discussion_record_no(item)
    db.session.commit()
    return jsonify(item.to_dict())


@discussions_bp.route("/<int:did>/export-word", methods=["GET"])
@jwt_required()
def export_discussion_word(did):
    item = db.session.get(CaseDiscussion, did)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404

    record_no = item.record_no or _build_discussion_record_no(item)

    metadata_rows = [
        ["记录编号", record_no, "讨论日期", item.discussion_date.isoformat() if item.discussion_date else ""],
        ["患者姓名", item.patient_name, "临床诊断", item.diagnosis],
        ["讨论主持人", item.moderator, "主讲人", item.speaker],
        ["参加人数", item.participant_count or "", "讨论地点", item.location],
        ["讨论目的", item.discussion_purpose, "记录人", item.creator.real_name if item.creator else ""],
        ["参与人员", item.participants, "", ""],
    ]
    sections = [
        {"heading": "病例信息摘要", "content": item.case_info},
        {"heading": "讨论内容", "content": item.discussion_content},
        {"heading": "讨论结论与处理意见", "content": item.conclusion},
    ]
    title = "疑难病例讨论记录"
    footer_text = f"文书编号：{record_no}    打印日期：{date.today().isoformat()}"
    output = export_record_to_word(
        title,
        "科室疑难病例讨论打印版",
        metadata_rows,
        sections,
        signatures=["记录人签名", "审核人签名", "日期"],
        footer_text=footer_text,
    )
    filename = f"{record_no}_疑难病例讨论记录.docx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


@discussions_bp.route("/<int:did>", methods=["DELETE"])
@jwt_required()
def delete_discussion(did):
    item = db.session.get(CaseDiscussion, did)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "已删除"})
