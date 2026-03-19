import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ks-quality-control-secret-key-2026-secure")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "..", "data", "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-ks-quality-control-2026-secure")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB上传限制
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "uploads")
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, "..", "templates")
    DATA_DIR = os.path.join(BASE_DIR, "..", "data")
