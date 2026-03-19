from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from functools import wraps

auth_bp = Blueprint("auth", __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        uid = int(get_jwt_identity())
        user = db.session.get(User, uid)
        if not user or user.role != "admin":
            return jsonify({"msg": "需要管理员权限"}), 403
        return fn(*args, **kwargs)
    return wrapper


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "用户名或密码错误"}), 401
    if not user.is_active:
        return jsonify({"msg": "账号已被禁用"}), 403

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"msg": "用户不存在"}), 404
    return jsonify(user.to_dict())


@auth_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify([u.to_dict() for u in users])


@auth_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json()
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"msg": "用户名不能为空"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "用户名已存在"}), 400

    user = User(
        username=username,
        real_name=data.get("real_name", username),
        role=data.get("role", "doctor"),
        is_active=True,
    )
    user.set_password(data.get("password", "123456"))
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@auth_bp.route("/users/<int:uid>", methods=["PUT"])
@admin_required
def update_user(uid):
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"msg": "用户不存在"}), 404

    data = request.get_json()
    if "real_name" in data:
        user.real_name = data["real_name"]
    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "password" in data and data["password"]:
        user.set_password(data["password"])

    db.session.commit()
    return jsonify(user.to_dict())


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    data = request.get_json()
    old_pwd = data.get("old_password", "")
    new_pwd = data.get("new_password", "")

    if not user.check_password(old_pwd):
        return jsonify({"msg": "原密码错误"}), 400
    if len(new_pwd) < 4:
        return jsonify({"msg": "新密码至少4位"}), 400

    user.set_password(new_pwd)
    db.session.commit()
    return jsonify({"msg": "密码修改成功"})
