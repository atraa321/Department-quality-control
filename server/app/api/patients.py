from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import joinedload

from app import db
from app.models.patient import DischargedPatient, build_followup_status_map
from app.models.followup import PatientFollowup
from app.models.user import User
from app.api.auth import admin_required
from app.utils.excel_import import parse_patient_file, generate_import_template
from datetime import date, datetime
import os
from io import BytesIO
from openpyxl import Workbook

patients_bp = Blueprint("patients", __name__)


def _serialize_patients(items):
    status_map = build_followup_status_map([item.id for item in items])
    return [
        item.to_dict(status_map.get(item.id))
        for item in items
    ]


@patients_bp.route("", methods=["GET"])
@jwt_required()
def list_patients():
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    query = DischargedPatient.query
    # 医师只看自己的出院患者
    if user.role == "doctor":
        query = query.filter_by(attending_doctor=user.real_name)

    start = request.args.get("start")
    end = request.args.get("end")
    batch = request.args.get("batch")
    if start:
        query = query.filter(DischargedPatient.discharge_date >= date.fromisoformat(start))
    if end:
        query = query.filter(DischargedPatient.discharge_date <= date.fromisoformat(end))
    if batch:
        query = query.filter_by(import_batch=batch)

    items = query.order_by(DischargedPatient.discharge_date.desc()).all()
    return jsonify(_serialize_patients(items))


@patients_bp.route("/import", methods=["POST"])
@admin_required
def import_patients():
    if "file" not in request.files:
        return jsonify({"msg": "请上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"msg": "文件名为空"}), 400

    # 获取列映射
    column_map = request.form.get("column_map", "")
    import json
    try:
        col_map = json.loads(column_map) if column_map else {}
    except json.JSONDecodeError:
        col_map = {}

    batch_name = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        patients = parse_patient_file(file, col_map)
    except Exception as e:
        return jsonify({"msg": f"文件解析失败: {str(e)}"}), 400

    count = 0
    for p in patients:
        patient = DischargedPatient(
            patient_name=p.get("patient_name", ""),
            record_no=p.get("record_no", ""),
            gender=p.get("gender", ""),
            age=p.get("age"),
            diagnosis=p.get("diagnosis", ""),
            admission_date=p.get("admission_date"),
            discharge_date=p.get("discharge_date"),
            attending_doctor=p.get("attending_doctor", ""),
            import_batch=batch_name,
        )
        db.session.add(patient)
        count += 1

    db.session.commit()
    return jsonify({"msg": f"成功导入 {count} 条记录", "batch": batch_name, "count": count})


@patients_bp.route("/template", methods=["GET"])
@jwt_required()
def download_template():
    filepath = generate_import_template()
    return send_file(filepath, as_attachment=True, download_name="出院患者导入模板.xlsx")


@patients_bp.route("/preview", methods=["POST"])
@admin_required
def preview_file():
    """预览上传文件的列名，用于列映射"""
    if "file" not in request.files:
        return jsonify({"msg": "请上传文件"}), 400
    file = request.files["file"]
    from app.utils.excel_import import preview_columns
    try:
        columns, sample_rows = preview_columns(file)
    except Exception as e:
        return jsonify({"msg": f"文件解析失败: {str(e)}"}), 400
    return jsonify({"columns": columns, "sample_rows": sample_rows})


@patients_bp.route("/batches", methods=["GET"])
@jwt_required()
def list_batches():
    batches = db.session.query(
        DischargedPatient.import_batch,
        db.func.count(DischargedPatient.id),
        db.func.min(DischargedPatient.imported_at),
    ).group_by(DischargedPatient.import_batch).order_by(
        db.func.min(DischargedPatient.imported_at).desc()
    ).all()
    return jsonify([
        {"batch": b[0], "count": b[1], "imported_at": b[2].isoformat() if b[2] else None}
        for b in batches
    ])


@patients_bp.route("/backup", methods=["GET"])
@admin_required
def backup_patients():
    patient_items = DischargedPatient.query.order_by(
        DischargedPatient.discharge_date.desc(),
        DischargedPatient.imported_at.desc()
    ).all()
    patient_status_map = build_followup_status_map([item.id for item in patient_items])

    followup_items = PatientFollowup.query.options(
        joinedload(PatientFollowup.patient),
        joinedload(PatientFollowup.user),
    ).order_by(
        PatientFollowup.followup_date.desc(),
        PatientFollowup.created_at.desc()
    ).all()

    wb = Workbook()
    patient_ws = wb.active
    patient_ws.title = "出院患者数据备份"
    patient_headers = [
        "患者姓名", "病案号", "性别", "年龄", "诊断", "入院日期", "出院日期",
        "主管医师", "导入批次", "导入时间", "医师回访", "护士回访",
    ]
    patient_ws.append(patient_headers)

    for item in patient_items:
        followup_status = patient_status_map.get(item.id, {})
        patient_ws.append([
            item.patient_name,
            item.record_no,
            item.gender,
            item.age,
            item.diagnosis,
            item.admission_date.isoformat() if item.admission_date else "",
            item.discharge_date.isoformat() if item.discharge_date else "",
            item.attending_doctor,
            item.import_batch,
            item.imported_at.isoformat(sep=" ", timespec="seconds") if item.imported_at else "",
            "是" if followup_status.get("doctor_followup_done") else "否",
            "是" if followup_status.get("nurse_followup_done") else "否",
        ])

    followup_ws = wb.create_sheet("回访记录备份")
    followup_headers = [
        "回访日期", "患者姓名", "病案号", "回访方式", "患者反馈", "满意度",
        "意见建议", "需重点关注", "回访人", "角色", "登记时间",
    ]
    followup_ws.append(followup_headers)

    method_labels = {"phone": "电话", "visit": "上门", "online": "线上"}
    role_labels = {"doctor": "医师", "nurse": "护士"}
    for item in followup_items:
        followup_ws.append([
            item.followup_date.isoformat() if item.followup_date else "",
            item.patient.patient_name if item.patient else "",
            item.patient.record_no if item.patient else "",
            method_labels.get(item.followup_method, item.followup_method),
            item.feedback,
            item.satisfaction,
            item.suggestions,
            "是" if item.needs_attention else "否",
            item.user.real_name if item.user else "",
            role_labels.get(item.followup_role, item.followup_role),
            item.created_at.isoformat(sep=" ", timespec="seconds") if item.created_at else "",
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"出院患者数据备份_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename)


@patients_bp.route("/clear", methods=["DELETE"])
@admin_required
def clear_patients_data():
    patient_count = DischargedPatient.query.count()
    followup_count = PatientFollowup.query.count()

    PatientFollowup.query.delete(synchronize_session=False)
    DischargedPatient.query.delete(synchronize_session=False)
    db.session.commit()

    return jsonify({
        "msg": f"已清除 {patient_count} 条出院患者数据，并删除 {followup_count} 条回访记录",
        "patient_count": patient_count,
        "followup_count": followup_count,
    })


@patients_bp.route("/<int:pid>", methods=["DELETE"])
@admin_required
def delete_patient(pid):
    item = db.session.get(DischargedPatient, pid)
    if not item:
        return jsonify({"msg": "记录不存在"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "已删除"})
