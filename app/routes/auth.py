from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from app.db import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    password = data.get("password", "")

    print(f"[DEBUG] 登入嘗試 - 學號: {student_id}, 密碼長度: {len(password)}")

    if not student_id or not password:
        return jsonify({"ok": False, "message": "請輸入學號與密碼"}), 400

    # ✅ 1) 先查 user（一定要先有 user）
    user = db.users.find_one({"student_id": student_id})
    print(f"[DEBUG] 查詢用戶: {user is not None}")

    # ✅ 2) 再判斷 user 存不存在
    if not user:
        print(f"[DEBUG] 用戶 {student_id} 不存在")
        return jsonify({"ok": False, "message": "帳號或密碼錯誤"}), 401

    # ✅ 3) 再取 password_hash
    stored_hash = user.get("password_hash")
    if not stored_hash:
        print(f"[DEBUG] 用戶 {student_id} 無密碼雜湊")
        return jsonify({"ok": False, "message": "此帳號尚未設定密碼，請聯絡管理者"}), 400

    # ✅ 4) 驗證密碼
    if not check_password_hash(stored_hash, password):
        print(f"[DEBUG] 用戶 {student_id} 密碼錯誤")
        return jsonify({"ok": False, "message": "帳號或密碼錯誤"}), 401

    print(f"[DEBUG] 用戶 {student_id} 登入成功")

    # ✅ 5) 登入成功回傳（前端要用）
    return jsonify({
        "ok": True,
        "participant_id": str(user.get("_id")),
        "name": user.get("name", ""),
        "class_name": user.get("class_name", ""),
        "role": user.get("role", "student")
    })
