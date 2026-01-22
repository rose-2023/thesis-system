from flask import Blueprint, request, jsonify
from datetime import datetime
from app.db import db

student_bp = Blueprint("student", __name__)
PRE_TOTAL = 10

@student_bp.get("/entry")
def entry():
    participant_id = request.args.get("participant_id", "").strip()
    if not participant_id:
        return jsonify({"ok": False, "message": "缺少 participant_id"}), 400

    # 已完成前測
    done = db.sessions.find_one({
        "participant_id": participant_id,
        "type": "pre",
        "end_time": {"$ne": None}
    })
    if done:
        return jsonify({"ok": True, "next": "home"})

    # 找未結束的 pre session，沒有就建一筆
    s = db.sessions.find_one({
        "participant_id": participant_id,
        "type": "pre",
        "end_time": None
    })
    if not s:
        r = db.sessions.insert_one({
            "participant_id": participant_id,
            "type": "pre",
            "unit": None,
            "start_time": datetime.utcnow(),
            "end_time": None,
            "correct_count": 0,
            "wrong_count": 0
        })
        sid = str(r.inserted_id)
    else:
        sid = str(s["_id"])

    return jsonify({"ok": True, "next": "pre", "session_id": sid})
