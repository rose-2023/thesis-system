from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from app.db import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    password = data.get("password", "")

    if not student_id or not password:
        return jsonify({"ok": False, "message": "請輸入學號與密碼"}), 400

    # ✅ 1) 先查 user（一定要先有 user）
    user = db.users.find_one({"student_id": student_id})

    # ✅ 2) 再判斷 user 存不存在
    if not user:
        return jsonify({"ok": False, "message": "帳號或密碼錯誤"}), 401

    # ✅ 3) 再取 password_hash
    stored_hash = user.get("password_hash")
    if not stored_hash:
        return jsonify({"ok": False, "message": "此帳號尚未設定密碼，請聯絡管理者"}), 400

    # ✅ 4) 驗證密碼
    if not check_password_hash(stored_hash, password):
        return jsonify({"ok": False, "message": "帳號或密碼錯誤"}), 401

    # ✅ 5) 登入成功回傳（前端要用）
    return jsonify({
        "ok": True,
        "participant_id": str(user.get("_id")),
        "name": user.get("name", ""),
        "class_name": user.get("class_name", ""),
        "role": user.get("role", "student")
    })
