from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from sqlalchemy.orm import joinedload

from app import db
from app.models.task import Task
from app.models.case_discussion import CaseDiscussion
from app.models.business_study import BusinessStudy
from app.models.medical_check import MedicalRecordCheck
from app.models.patient import DischargedPatient
from app.models.followup import PatientFollowup
from app.models.user import User
from app.api.auth import admin_required
from app.utils.check_catalog import build_check_statistics, get_check_category_label
from app.utils.export import export_to_excel, export_to_word
from datetime import date

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/summary", methods=["GET"])
@admin_required
def summary():
    start = request.args.get("start")
    end = request.args.get("end")

    # 任务统计
    task_q = Task.query
    if start:
        task_q = task_q.filter(Task.deadline >= date.fromisoformat(start))
    if end:
        task_q = task_q.filter(Task.deadline <= date.fromisoformat(end))
    total_tasks = task_q.count()
    completed_tasks = task_q.filter_by(status="completed").count()
    overdue_tasks = task_q.filter_by(status="overdue").count()

    # 各模块统计
    disc_q = CaseDiscussion.query
    study_q = BusinessStudy.query
    check_q = MedicalRecordCheck.query.options(
        joinedload(MedicalRecordCheck.responsible_doctor),
    )
    followup_q = PatientFollowup.query
    patient_q = DischargedPatient.query

    if start:
        disc_q = disc_q.filter(CaseDiscussion.discussion_date >= date.fromisoformat(start))
        study_q = study_q.filter(BusinessStudy.study_date >= date.fromisoformat(start))
        check_q = check_q.filter(MedicalRecordCheck.check_date >= date.fromisoformat(start))
        followup_q = followup_q.filter(PatientFollowup.followup_date >= date.fromisoformat(start))
        patient_q = patient_q.filter(DischargedPatient.discharge_date >= date.fromisoformat(start))
    if end:
        disc_q = disc_q.filter(CaseDiscussion.discussion_date <= date.fromisoformat(end))
        study_q = study_q.filter(BusinessStudy.study_date <= date.fromisoformat(end))
        check_q = check_q.filter(MedicalRecordCheck.check_date <= date.fromisoformat(end))
        followup_q = followup_q.filter(PatientFollowup.followup_date <= date.fromisoformat(end))
        patient_q = patient_q.filter(DischargedPatient.discharge_date <= date.fromisoformat(end))

    check_items = check_q.order_by(MedicalRecordCheck.check_date.desc()).all()
    check_stats = build_check_statistics(check_items)

    # 满意度统计
    avg_sat = db.session.query(db.func.avg(PatientFollowup.satisfaction))
    if start:
        avg_sat = avg_sat.filter(PatientFollowup.followup_date >= date.fromisoformat(start))
    if end:
        avg_sat = avg_sat.filter(PatientFollowup.followup_date <= date.fromisoformat(end))
    avg_sat = avg_sat.scalar()

    return jsonify({
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "overdue": overdue_tasks,
            "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks else 0,
        },
        "discussions": {"count": disc_q.count()},
        "studies": {"count": study_q.count()},
        "checks": {
            **check_stats["summary"],
            "category_stats": check_stats["category_stats"],
            "doctor_stats": check_stats["doctor_stats"],
        },
        "patients": {"count": patient_q.count()},
        "followups": {
            "count": followup_q.count(),
            "avg_satisfaction": round(avg_sat, 2) if avg_sat else 0,
        },
    })


@reports_bp.route("/export/excel", methods=["GET"])
@admin_required
def export_excel():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    module = request.args.get("module", "all")
    period = f"{start} ~ {end}" if start and end else "全部"

    if module == "discussions":
        q = CaseDiscussion.query.options(joinedload(CaseDiscussion.creator))
        if start:
            q = q.filter(CaseDiscussion.discussion_date >= date.fromisoformat(start))
        if end:
            q = q.filter(CaseDiscussion.discussion_date <= date.fromisoformat(end))
        items = q.order_by(CaseDiscussion.discussion_date.desc()).all()
        headers = ["日期", "患者姓名", "诊断", "讨论内容", "参与人员", "结论", "记录人"]
        rows = [[i.discussion_date, i.patient_name, i.diagnosis, i.discussion_content,
                  i.participants, i.conclusion, i.creator.real_name] for i in items]
        title = f"疑难病例讨论记录 ({period})"

    elif module == "studies":
        q = BusinessStudy.query.options(joinedload(BusinessStudy.creator))
        if start:
            q = q.filter(BusinessStudy.study_date >= date.fromisoformat(start))
        if end:
            q = q.filter(BusinessStudy.study_date <= date.fromisoformat(end))
        items = q.order_by(BusinessStudy.study_date.desc()).all()
        headers = ["日期", "主题", "内容", "参与人员", "备注", "记录人"]
        rows = [[i.study_date, i.topic, i.content, i.participants, i.notes,
                  i.creator.real_name] for i in items]
        title = f"业务学习记录 ({period})"

    elif module == "checks":
        q = MedicalRecordCheck.query.options(
            joinedload(MedicalRecordCheck.creator),
            joinedload(MedicalRecordCheck.responsible_doctor),
        )
        if start:
            q = q.filter(MedicalRecordCheck.check_date >= date.fromisoformat(start))
        if end:
            q = q.filter(MedicalRecordCheck.check_date <= date.fromisoformat(end))
        items = q.order_by(MedicalRecordCheck.check_date.desc()).all()
        headers = ["检查日期", "病案号", "患者姓名", "问题分类", "预设模板", "发现问题", "责任医师", "严重程度", "整改状态", "整改反馈", "整改日期", "备注", "检查人"]
        rows = [[i.check_date, i.record_no, i.patient_name, get_check_category_label(i.issue_category), i.issue_template, i.issue_found,
              i.responsible_doctor.real_name if i.responsible_doctor else "",
                  "严重" if i.severity == "serious" else "一般",
              "已整改" if i.is_rectified else "待整改", i.rectification_feedback, i.rectified_date, i.remarks,
                  i.creator.real_name] for i in items]
        title = f"病历质控检查记录 ({period})"

    elif module == "followups":
        q = PatientFollowup.query.options(
            joinedload(PatientFollowup.patient),
            joinedload(PatientFollowup.user),
        )
        if start:
            q = q.filter(PatientFollowup.followup_date >= date.fromisoformat(start))
        if end:
            q = q.filter(PatientFollowup.followup_date <= date.fromisoformat(end))
        items = q.order_by(PatientFollowup.followup_date.desc()).all()
        methods = {"phone": "电话", "visit": "上门", "online": "线上"}
        headers = ["回访日期", "患者姓名", "回访方式", "反馈", "满意度", "意见建议", "需重点关注", "回访人", "角色"]
        rows = [[i.followup_date, i.patient.patient_name if i.patient else "",
                  methods.get(i.followup_method, i.followup_method), i.feedback,
                  i.satisfaction, i.suggestions,
                  "是" if i.needs_attention else "否",
                  i.user.real_name, "护士" if i.followup_role == "nurse" else "医师"]
                 for i in items]
        title = f"出院患者回访记录 ({period})"

    else:
        return jsonify({"msg": "请指定导出模块: discussions/studies/checks/followups"}), 400

    output = export_to_excel(title, headers, rows)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name=f"{title}.xlsx")


@reports_bp.route("/export/word", methods=["GET"])
@admin_required
def export_word():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    period = f"{start} ~ {end}" if start and end else "全部"
    title = f"科室质控工作汇总报告 ({period})"

    sections = []

    # 疑难病例讨论
    q = CaseDiscussion.query.options(joinedload(CaseDiscussion.creator))
    if start:
        q = q.filter(CaseDiscussion.discussion_date >= date.fromisoformat(start))
    if end:
        q = q.filter(CaseDiscussion.discussion_date <= date.fromisoformat(end))
    discs = q.order_by(CaseDiscussion.discussion_date.desc()).all()
    sections.append({
        "heading": f"一、疑难病例讨论（共{len(discs)}次）",
        "table": {
            "headers": ["日期", "患者", "诊断", "结论"],
            "rows": [[d.discussion_date, d.patient_name, d.diagnosis, d.conclusion] for d in discs],
        }
    })

    # 业务学习
    q = BusinessStudy.query.options(joinedload(BusinessStudy.creator))
    if start:
        q = q.filter(BusinessStudy.study_date >= date.fromisoformat(start))
    if end:
        q = q.filter(BusinessStudy.study_date <= date.fromisoformat(end))
    studies = q.order_by(BusinessStudy.study_date.desc()).all()
    sections.append({
        "heading": f"二、业务学习（共{len(studies)}次）",
        "table": {
            "headers": ["日期", "主题", "参与人员"],
            "rows": [[s.study_date, s.topic, s.participants] for s in studies],
        }
    })

    # 病历检查
    q = MedicalRecordCheck.query.options(joinedload(MedicalRecordCheck.responsible_doctor))
    if start:
        q = q.filter(MedicalRecordCheck.check_date >= date.fromisoformat(start))
    if end:
        q = q.filter(MedicalRecordCheck.check_date <= date.fromisoformat(end))
    checks = q.order_by(MedicalRecordCheck.check_date.desc()).all()
    check_stats = build_check_statistics(checks)
    sections.append({
        "heading": f"三、病历质控检查（共{len(checks)}份，严重问题{check_stats['summary']['serious']}个，已整改{check_stats['summary']['rectified']}个）",
        "table": {
            "headers": ["日期", "病案号", "患者", "分类", "责任医师", "问题", "严重程度", "整改状态"],
            "rows": [[c.check_date, c.record_no, c.patient_name, get_check_category_label(c.issue_category),
                       c.responsible_doctor.real_name if c.responsible_doctor else "",
                       c.issue_found,
                       "严重" if c.severity == "serious" else "一般",
                       "已整改" if c.is_rectified else "待整改"] for c in checks],
        }
    })
    sections.append({
        "heading": "三-1、按问题分类统计",
        "table": {
            "headers": ["分类", "总数", "严重问题", "已整改", "待整改"],
            "rows": [[item["label"], item["count"], item["serious"], item["rectified"], item["pending"]] for item in check_stats["category_stats"]],
        }
    })
    sections.append({
        "heading": "三-2、按责任医师统计整改情况",
        "table": {
            "headers": ["责任医师", "问题总数", "严重问题", "已整改", "待整改"],
            "rows": [[item["doctor_name"], item["count"], item["serious"], item["rectified"], item["pending"]] for item in check_stats["doctor_stats"]],
        }
    })

    # 回访统计
    q = PatientFollowup.query
    if start:
        q = q.filter(PatientFollowup.followup_date >= date.fromisoformat(start))
    if end:
        q = q.filter(PatientFollowup.followup_date <= date.fromisoformat(end))
    fups = q.all()
    avg_sat = sum(f.satisfaction for f in fups) / len(fups) if fups else 0
    sections.append({
        "heading": f"四、出院患者回访（共{len(fups)}次，平均满意度{avg_sat:.1f}分）",
        "content": f"回访总次数：{len(fups)}\n平均满意度：{avg_sat:.1f}/5",
    })

    output = export_to_word(title, sections)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     as_attachment=True, download_name=f"{title}.docx")
