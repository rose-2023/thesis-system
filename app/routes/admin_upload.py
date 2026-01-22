import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from bson import ObjectId 
from app.db import db

admin_upload_bp = Blueprint("admin_upload", __name__)

ALLOWED_EXT = {"mp4", "webm", "mov"}  # 你也可以只留 mp4
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "videos")

def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXT

@admin_upload_bp.post("/video")
def upload_video():
    # ===== 1) 取得 form 欄位 =====
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    uploaded_by = (request.form.get("uploaded_by") or "").strip()  # 先用 admin id/participant_id
    unit = (request.form.get("unit") or "").strip()          # e.g. "U1"

    if not unit or not title:
        return jsonify({"ok": False, "message": "unit 與 title 必填"}), 400

    # ===== 2) 取得檔案 =====
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "缺少檔案欄位 file"}), 400

    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"ok": False, "message": "未選擇檔案"}), 400

    if not allowed_file(f.filename):
        return jsonify({"ok": False, "message": "檔案格式不支援（建議 mp4）"}), 400

    # ===== 3) 存檔 =====
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    original_name = f.filename
    safe_name = secure_filename(original_name)

    ext = safe_name.rsplit(".", 1)[1].lower()
    uniq = uuid.uuid4().hex[:8]
    filename = f"{unit}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uniq}.{ext}"

    save_path = os.path.join(UPLOAD_DIR, filename)
    f.save(save_path)

    size = os.path.getsize(save_path)
    content_type = f.mimetype

    # ===== 4) 寫入 MongoDB =====
    doc = {
        "unit": unit,
        "title": title,
        "description": description,
        "filename": filename,
        "original_name": original_name,
        "content_type": content_type,
        "size": size,
        "path": os.path.join("uploads", "videos", filename).replace("\\", "/"),
        "uploaded_by": uploaded_by,
        "created_at": datetime.now(timezone.utc),
        "active": True
    }
    r = db.videos.insert_one(doc)

    return jsonify({
        "ok": True,
        "video_id": str(r.inserted_id),
        "filename": filename,
        "path": doc["path"]
    })

@admin_upload_bp.get("/videos")
def list_videos():
    unit = (request.args.get("unit") or "").strip()
    q = {}
    if unit:
        q["unit"] = unit

    vids = list(db.videos.find(q).sort("created_at", -1).limit(50))
    for v in vids:
        v["_id"] = str(v["_id"])
        if "active" not in v:
            v["active"] = True  # 沒有 active 的舊資料，先視為啟用
    return jsonify({"ok": True, "videos": vids})

@admin_upload_bp.patch("/video/<video_id>/active")
def set_video_active(video_id):
    try:
        vid = ObjectId(video_id)
    except Exception:
        return jsonify({"ok": False, "message": "video_id 格式錯誤"}), 400

    data = request.get_json() or {}
    active = data.get("active", None)
    if active is None:
        return jsonify({"ok": False, "message": "缺少 active 欄位"}), 400

    r = db.videos.update_one({"_id": vid}, {"$set": {"active": bool(active)}})
    if r.matched_count == 0:
        return jsonify({"ok": False, "message": "找不到影片"}), 404

    return jsonify({"ok": True, "video_id": video_id, "active": bool(active)})