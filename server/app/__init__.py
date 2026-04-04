from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from sqlalchemy import text
import os

db = SQLAlchemy()
jwt = JWTManager()


def _resolve_static_folder():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("KSQC_STATIC_DIR", "").strip(),
        os.path.abspath(os.path.join(app_dir, "../../frontend/dist")),
        os.path.abspath(os.path.join(app_dir, "../dist")),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(os.path.join(candidate, "index.html")):
            return candidate
    return candidates[1]


def create_app():
    app = Flask(__name__, static_folder=_resolve_static_folder(), static_url_path="/")
    app.config.from_object("app.config.Config")

    # 确保数据目录存在
    os.makedirs(app.config.get("DATA_DIR", "data"), exist_ok=True)
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

    CORS(app)
    db.init_app(app)
    jwt.init_app(app)

    # 注册蓝图
    from app.api.auth import auth_bp
    from app.api.tasks import tasks_bp
    from app.api.discussions import discussions_bp
    from app.api.studies import studies_bp
    from app.api.checks import checks_bp
    from app.api.patients import patients_bp
    from app.api.followups import followups_bp
    from app.api.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(discussions_bp, url_prefix="/api/discussions")
    app.register_blueprint(studies_bp, url_prefix="/api/studies")
    app.register_blueprint(checks_bp, url_prefix="/api/checks")
    app.register_blueprint(patients_bp, url_prefix="/api/patients")
    app.register_blueprint(followups_bp, url_prefix="/api/followups")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    # 前端路由 - 所有非API路径返回index.html
    @app.route("/")
    @app.route("/<path:path>")
    def serve_frontend(path=""):
        if path and app.static_folder and os.path.exists(os.path.join(app.static_folder, path)):
            return app.send_static_file(path)
        if app.static_folder and os.path.exists(os.path.join(app.static_folder, "index.html")):
            return app.send_static_file("index.html")
        return (
            "前端静态资源未部署。请先解压前端部署包到与 server 同级的 frontend/dist，"
            "或设置环境变量 KSQC_STATIC_DIR 指向前端 dist 目录。",
            503,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    with app.app_context():
        from app.models import user, task, case_discussion, business_study, medical_check, patient, followup
        db.create_all()
        _ensure_schema_updates()
        _ensure_indexes()
        _init_admin(app)

    return app


def _init_admin(app):
    """初始化默认管理员账号"""
    from app.models.user import User
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            real_name="科主任",
            role="admin",
            is_active=True,
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


def _ensure_schema_updates():
    schema_updates = {
        "tasks": [
            ("carryover_source_id", "ALTER TABLE tasks ADD COLUMN carryover_source_id INTEGER"),
        ],
        "business_studies": [
            ("record_no", "ALTER TABLE business_studies ADD COLUMN record_no VARCHAR(64) DEFAULT ''"),
            ("host", "ALTER TABLE business_studies ADD COLUMN host VARCHAR(64) DEFAULT ''"),
            ("speaker", "ALTER TABLE business_studies ADD COLUMN speaker VARCHAR(64) DEFAULT ''"),
            ("location", "ALTER TABLE business_studies ADD COLUMN location VARCHAR(128) DEFAULT ''"),
            ("study_method", "ALTER TABLE business_studies ADD COLUMN study_method VARCHAR(64) DEFAULT ''"),
            ("participant_count", "ALTER TABLE business_studies ADD COLUMN participant_count INTEGER DEFAULT 0"),
        ],
        "case_discussions": [
            ("record_no", "ALTER TABLE case_discussions ADD COLUMN record_no VARCHAR(64) DEFAULT ''"),
            ("moderator", "ALTER TABLE case_discussions ADD COLUMN moderator VARCHAR(64) DEFAULT ''"),
            ("speaker", "ALTER TABLE case_discussions ADD COLUMN speaker VARCHAR(64) DEFAULT ''"),
            ("location", "ALTER TABLE case_discussions ADD COLUMN location VARCHAR(128) DEFAULT ''"),
            ("participant_count", "ALTER TABLE case_discussions ADD COLUMN participant_count INTEGER DEFAULT 0"),
            ("discussion_purpose", "ALTER TABLE case_discussions ADD COLUMN discussion_purpose VARCHAR(256) DEFAULT ''"),
        ],
        "medical_record_checks": [
            ("responsible_doctor_id", "ALTER TABLE medical_record_checks ADD COLUMN responsible_doctor_id INTEGER"),
            ("issue_category", "ALTER TABLE medical_record_checks ADD COLUMN issue_category VARCHAR(64) DEFAULT 'other'"),
            ("issue_template", "ALTER TABLE medical_record_checks ADD COLUMN issue_template VARCHAR(128) DEFAULT ''"),
            ("rectification_status", "ALTER TABLE medical_record_checks ADD COLUMN rectification_status VARCHAR(16) DEFAULT 'pending'"),
            ("rectification_feedback", "ALTER TABLE medical_record_checks ADD COLUMN rectification_feedback TEXT DEFAULT ''"),
            ("rectified_at", "ALTER TABLE medical_record_checks ADD COLUMN rectified_at DATETIME"),
            ("rectified_by", "ALTER TABLE medical_record_checks ADD COLUMN rectified_by INTEGER"),
            ("rectification_task_id", "ALTER TABLE medical_record_checks ADD COLUMN rectification_task_id INTEGER"),
        ],
        "discharged_patients": [
            ("phone", "ALTER TABLE discharged_patients ADD COLUMN phone VARCHAR(64) DEFAULT ''"),
            ("address", "ALTER TABLE discharged_patients ADD COLUMN address VARCHAR(255) DEFAULT ''"),
            ("discharge_department", "ALTER TABLE discharged_patients ADD COLUMN discharge_department VARCHAR(128) DEFAULT ''"),
        ],
    }

    for table_name, columns in schema_updates.items():
        existing_columns = {
            row[1] for row in db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        }
        for column_name, alter_sql in columns:
            if column_name not in existing_columns:
                db.session.execute(text(alter_sql))
                existing_columns.add(column_name)
    db.session.commit()


def _ensure_indexes():
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_users_role_active ON users (role, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_status_deadline ON tasks (assigned_to, status, deadline)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_type_deadline ON tasks (type, deadline)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks (created_by)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_carryover_source ON tasks (carryover_source_id)",
        "CREATE INDEX IF NOT EXISTS idx_case_discussions_date ON case_discussions (discussion_date)",
        "CREATE INDEX IF NOT EXISTS idx_case_discussions_created_by ON case_discussions (created_by)",
        "CREATE INDEX IF NOT EXISTS idx_business_studies_date ON business_studies (study_date)",
        "CREATE INDEX IF NOT EXISTS idx_business_studies_created_by ON business_studies (created_by)",
        "CREATE INDEX IF NOT EXISTS idx_medical_checks_check_date ON medical_record_checks (check_date)",
        "CREATE INDEX IF NOT EXISTS idx_medical_checks_task_id ON medical_record_checks (task_id)",
        "CREATE INDEX IF NOT EXISTS idx_medical_checks_rectification_task_id ON medical_record_checks (rectification_task_id)",
        "CREATE INDEX IF NOT EXISTS idx_medical_checks_doctor_status ON medical_record_checks (responsible_doctor_id, rectification_status)",
        "CREATE INDEX IF NOT EXISTS idx_medical_checks_created_by ON medical_record_checks (created_by)",
        "CREATE INDEX IF NOT EXISTS idx_medical_checks_rectified_by ON medical_record_checks (rectified_by)",
        "CREATE INDEX IF NOT EXISTS idx_discharged_patients_date_doctor ON discharged_patients (discharge_date, attending_doctor)",
        "CREATE INDEX IF NOT EXISTS idx_discharged_patients_batch ON discharged_patients (import_batch)",
        "CREATE INDEX IF NOT EXISTS idx_discharged_patients_record_no ON discharged_patients (record_no)",
        "CREATE INDEX IF NOT EXISTS idx_patient_followups_patient_role ON patient_followups (patient_id, followup_role)",
        "CREATE INDEX IF NOT EXISTS idx_patient_followups_by_date ON patient_followups (followup_by, followup_date)",
        "CREATE INDEX IF NOT EXISTS idx_patient_followups_role_date ON patient_followups (followup_role, followup_date)",
    ]

    for statement in index_statements:
        db.session.execute(text(statement))
    db.session.commit()
