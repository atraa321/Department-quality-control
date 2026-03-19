from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.models.task import Task
from app.models.followup import PatientFollowup
from app.models.patient import DischargedPatient
from app.models.user import User
from app.api.auth import admin_required
from datetime import date, datetime, timedelta

tasks_bp = Blueprint("tasks", __name__)


TASK_TYPE_LABELS = {
    "discussion": "病例讨论",
    "study": "业务学习",
    "check": "病历检查",
    "followup": "患者回访",
}


def _parse_task_date(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field_name}格式不正确")


def _build_deadlines(start_date, end_date, quantity):
    if quantity < 1:
        raise ValueError("任务数量必须大于0")
    if quantity == 1:
        return [end_date]

    total_days = (end_date - start_date).days
    return [
        start_date + timedelta(days=round((index + 1) * total_days / quantity))
        for index in range(quantity)
    ]


def _build_weekly_deadlines(start_date, end_date):
    deadlines = []
    cursor = start_date
    while cursor <= end_date:
        week_end = min(cursor + timedelta(days=6), end_date)
        deadlines.append(week_end)
        cursor = week_end + timedelta(days=1)
    return deadlines


def _refresh_overdue_tasks():
    today = date.today()
    overdue_tasks = Task.query.filter(
        Task.deadline < today,
        Task.status.in_(["pending", "in_progress"]),
    ).all()
    for task in overdue_tasks:
        task.status = "overdue"
    if overdue_tasks:
        db.session.commit()


def _task_query(eager=True):
    if not eager:
        return Task.query

    options = [
        joinedload(Task.assignee),
        joinedload(Task.creator),
    ]
    for relation_name in ("scheduled_checks", "rectification_records"):
        relation = getattr(Task, relation_name, None)
        if relation is not None:
            options.append(selectinload(relation))
    return Task.query.options(*options)


def _task_scope_for_user(user, eager=True):
    query = _task_query(eager=eager)
    if user.role != "admin":
        query = query.filter(Task.assigned_to == user.id)
    return query


def _serialize_pending_tasks(user_id):
    tasks = _task_query().filter(
        Task.assigned_to == user_id,
        Task.status.in_(["pending", "in_progress", "overdue"]),
    ).order_by(Task.deadline.asc()).all()

    today = date.today()
    result = []
    pending_count = 0
    overdue_count = 0
    for task in tasks:
        item = task.to_dict()
        is_overdue = task.deadline < today and task.status != "completed"
        item["is_overdue"] = is_overdue
        if is_overdue:
            overdue_count += 1
        else:
            pending_count += 1
        result.append(item)
    return result, pending_count, overdue_count


def _pending_followup_count(user):
    if user.role == "admin":
        return 0

    followed_subquery = db.session.query(
        PatientFollowup.patient_id.label("patient_id")
    ).filter(
        PatientFollowup.followup_role == ("nurse" if user.role == "nurse" else "doctor")
    ).distinct().subquery()

    query = db.session.query(func.count(DischargedPatient.id)).outerjoin(
        followed_subquery,
        followed_subquery.c.patient_id == DischargedPatient.id,
    ).filter(
        followed_subquery.c.patient_id.is_(None)
    )

    if user.role == "doctor":
        query = query.filter(DischargedPatient.attending_doctor == user.real_name)

    return query.scalar() or 0


def _distribute_cases(total_cases, bucket_count):
    if total_cases < 1:
        raise ValueError("病例数必须大于0")
    if bucket_count < 1:
        return []

    base = total_cases // bucket_count
    remainder = total_cases % bucket_count
    return [base + (1 if index < remainder else 0) for index in range(bucket_count)]


def _make_task_title(task_type, deadline, index=None, quantity=1, case_count=None):
    type_label = TASK_TYPE_LABELS.get(task_type, task_type)
    suffix = f"（{case_count}例）" if case_count else ""
    if quantity > 1 and index is not None:
        return f"{type_label}任务 {deadline.isoformat()} #{index + 1}{suffix}"
    return f"{type_label}任务 {deadline.isoformat()}{suffix}"


def _merge_task_description(task_type, description, case_count=None):
    if not case_count:
        return description
    if task_type == "followup":
        prefix = f"本周计划回访 {case_count} 例"
    elif task_type == "check":
        prefix = f"本周计划检查 {case_count} 例病历"
    else:
        prefix = f"本周计划处理 {case_count} 项"
    if not description:
        return prefix
    return f"{prefix}\n{description}"


def _build_carryover_title(title):
    if "结转" in title:
        return title
    return f"{title}（上周未完成结转）"


def _build_carryover_description(source_task):
    prefix = f"上期未完成任务结转，原截止日期：{source_task.deadline.isoformat()}"
    if not source_task.description:
        return prefix
    return f"{prefix}\n{source_task.description}"


def _create_check_carryover_tasks(assigned_to, start_date, deadline, creator_id):
    source_tasks = Task.query.filter(
        Task.type == "check",
        Task.assigned_to == assigned_to,
        Task.deadline < start_date,
        Task.status.in_(["pending", "in_progress", "overdue"]),
        Task.title.like("病历检查任务%"),
    ).order_by(Task.deadline.asc()).all()

    carryover_tasks = []
    for source_task in source_tasks:
        exists = Task.query.filter(
            Task.carryover_source_id == source_task.id,
        ).first()
        if exists:
            continue

        carryover_task = Task(
            type="check",
            title=_build_carryover_title(source_task.title),
            description=_build_carryover_description(source_task),
            assigned_to=source_task.assigned_to,
            deadline=deadline,
            status="pending",
            carryover_source_id=source_task.id,
            created_by=creator_id,
        )
        db.session.add(carryover_task)
        carryover_tasks.append(carryover_task)
    return carryover_tasks


@tasks_bp.route("", methods=["GET"])
@jwt_required()
def list_tasks():
    _refresh_overdue_tasks()
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    query = _task_scope_for_user(user)

    # 筛选参数
    task_type = request.args.get("type")
    status = request.args.get("status")
    assigned_to = request.args.get("assigned_to")
    if task_type:
        query = query.filter_by(type=task_type)
    if status:
        query = query.filter_by(status=status)
    if assigned_to:
        try:
            query = query.filter_by(assigned_to=int(assigned_to))
        except ValueError:
            return jsonify({"msg": "负责人参数不正确"}), 400

    tasks = query.order_by(Task.deadline.asc()).all()
    return jsonify([t.to_dict() for t in tasks])


@tasks_bp.route("", methods=["POST"])
@admin_required
def create_task():
    data = request.get_json() or {}
    task_type = data.get("type", "discussion")
    description = (data.get("description") or "").strip()
    raw_title = (data.get("title") or "").strip()
    assigned_to = data.get("assigned_to")
    quantity = data.get("quantity", 1)

    if not assigned_to:
        return jsonify({"msg": "请选择负责人"}), 400

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify({"msg": "任务数量必须为整数"}), 400

    if quantity < 1:
        return jsonify({"msg": "任务数量必须大于0"}), 400

    try:
        single_deadline = _parse_task_date(data.get("deadline"), "截止日期")
        start_date = _parse_task_date(data.get("start_date"), "开始日期")
        end_date = _parse_task_date(data.get("end_date"), "结束日期")
    except ValueError as exc:
        return jsonify({"msg": str(exc)}), 400

    if single_deadline:
        start_date = single_deadline
        end_date = single_deadline
    elif start_date and not end_date:
        end_date = start_date
    elif end_date and not start_date:
        start_date = end_date

    if not start_date or not end_date:
        return jsonify({"msg": "请填写任务时间"}), 400

    if start_date > end_date:
        return jsonify({"msg": "开始日期不能晚于结束日期"}), 400

    try:
        if task_type in ("followup", "check"):
            deadlines = _build_weekly_deadlines(start_date, end_date)
            case_counts = _distribute_cases(quantity, len(deadlines))
        else:
            deadlines = _build_deadlines(start_date, end_date, quantity)
            case_counts = [None] * len(deadlines)
    except ValueError as exc:
        return jsonify({"msg": str(exc)}), 400

    created_tasks = []
    creator_id = int(get_jwt_identity())

    if task_type == "check" and deadlines:
        created_tasks.extend(_create_check_carryover_tasks(assigned_to, start_date, deadlines[0], creator_id))

    for index, deadline in enumerate(deadlines):
        case_count = case_counts[index] if index < len(case_counts) else None
        if task_type in ("followup", "check") and not case_count:
            continue
        title = raw_title or _make_task_title(task_type, deadline, index=index, quantity=len(deadlines), case_count=case_count)
        task = Task(
            type=task_type,
            title=title,
            description=_merge_task_description(task_type, description, case_count=case_count),
            assigned_to=assigned_to,
            deadline=deadline,
            status="pending",
            created_by=creator_id,
        )
        db.session.add(task)
        created_tasks.append(task)

    db.session.commit()

    if len(created_tasks) == 1:
        return jsonify(created_tasks[0].to_dict()), 201
    return jsonify({
        "count": len(created_tasks),
        "tasks": [task.to_dict() for task in created_tasks],
    }), 201


@tasks_bp.route("/<int:tid>", methods=["GET"])
@jwt_required()
def get_task(tid):
    task = db.session.get(Task, tid)
    if not task:
        return jsonify({"msg": "任务不存在"}), 404
    return jsonify(task.to_dict())


@tasks_bp.route("/<int:tid>", methods=["PUT"])
@jwt_required()
def update_task(tid):
    task = db.session.get(Task, tid)
    if not task:
        return jsonify({"msg": "任务不存在"}), 404

    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    data = request.get_json()
    # 管理员可以修改所有字段
    if user.role == "admin":
        if "title" in data:
            title = (data.get("title") or "").strip()
            task.title = title or _make_task_title(task.type, task.deadline)
        if "type" in data:
            task.type = data["type"]
        if "description" in data:
            task.description = data["description"]
        if "assigned_to" in data:
            task.assigned_to = data["assigned_to"]
        if "deadline" in data:
            task.deadline = date.fromisoformat(data["deadline"])
            if "title" not in data and not task.title:
                task.title = _make_task_title(task.type, task.deadline)
    # 任何被分配人可以更新状态
    if "status" in data and data["status"] in ("pending", "in_progress", "completed"):
        task.status = data["status"]

    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.route("/<int:tid>", methods=["DELETE"])
@admin_required
def delete_task(tid):
    task = db.session.get(Task, tid)
    if not task:
        return jsonify({"msg": "任务不存在"}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({"msg": "已删除"})


@tasks_bp.route("/batch-delete", methods=["POST"])
@admin_required
def batch_delete_tasks():
    data = request.get_json() or {}
    ids = data.get("ids") or []

    try:
        task_ids = [int(task_id) for task_id in ids]
    except (TypeError, ValueError):
        return jsonify({"msg": "任务ID格式不正确"}), 400

    if not task_ids:
        return jsonify({"msg": "请选择要删除的任务"}), 400

    tasks = Task.query.filter(Task.id.in_(task_ids)).all()
    existing_ids = {task.id for task in tasks}
    missing_ids = [task_id for task_id in task_ids if task_id not in existing_ids]
    if missing_ids:
        return jsonify({"msg": f"以下任务不存在：{', '.join(str(task_id) for task_id in missing_ids)}"}), 404

    for task in tasks:
        db.session.delete(task)
    db.session.commit()
    return jsonify({"msg": "已删除", "count": len(tasks)})


@tasks_bp.route("/my-pending", methods=["GET"])
@jwt_required()
def my_pending_tasks():
    """获取当前用户的待办和过期任务（用于桌面提醒）"""
    _refresh_overdue_tasks()
    uid = int(get_jwt_identity())
    result, _, _ = _serialize_pending_tasks(uid)
    return jsonify(result)


@tasks_bp.route("/dashboard-summary", methods=["GET"])
@jwt_required()
def dashboard_summary():
    _refresh_overdue_tasks()
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)

    pending_tasks, pending_count, overdue_count = _serialize_pending_tasks(uid)
    completed_count = _task_scope_for_user(user, eager=False).filter(Task.status == "completed").count()

    return jsonify({
        "pending_tasks": pending_tasks,
        "stats": {
            "pending_tasks": pending_count,
            "overdue_tasks": overdue_count,
            "completed_tasks": completed_count,
            "pending_followups": _pending_followup_count(user),
        },
    })
