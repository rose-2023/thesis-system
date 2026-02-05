import os
import re
import uuid
import subprocess
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from bson import ObjectId

from app.db import db

admin_upload_bp = Blueprint("admin_upload", __name__)

PROJECT_ROOT = os.getcwd()
UPLOADS_ROOT = os.path.join(PROJECT_ROOT, "uploads")


# =============================
# 基本設定
# =============================
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov"}
ALLOWED_SUB_EXT = {"srt", "txt"}

PROJECT_ROOT = os.getcwd()

UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads", "videos")
THUMB_DIR = os.path.join(UPLOADS_ROOT, "thumbnails") 
SUBTITLE_DIR = os.path.join(PROJECT_ROOT, "uploads", "subtitles")
# rel = os.path.join("uploads", "thumbnails", out_name).replace("\\", "/")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(SUBTITLE_DIR, exist_ok=True)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

# ✅ Windows 若找不到 ffmpeg/ffprobe，會改用環境變數 PATH 查找
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.environ.get("FFPROBE_BIN", "ffprobe")


# ✅ 一定要在「檔案一開始（全域）」就建立資料夾
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(SUBTITLE_DIR, exist_ok=True)


@admin_upload_bp.get("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOADS_ROOT, filename)


# =============================
# 工具函式
# =============================
def allowed_ext(filename: str, allowed_set: set) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_set


def get_file_size(f):
    """取得檔案大小（支援流式讀取）"""
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    return size


def now_utc():
    return datetime.now(timezone.utc)


def safe_iso(dt: datetime):
    """讓 datetime 可 JSON"""
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


# =============================
# SRT / TXT 時間軸檢查
# =============================
SRT_TIME_RE = re.compile(
    r"(?P<hs>\d{2}):(?P<ms>\d{2}):(?P<ss>\d{2}),(?P<hms>\d{3})\s*-->\s*"
    r"(?P<he>\d{2}):(?P<me>\d{2}):(?P<se>\d{2}),(?P<hme>\d{3})"
)

TXT_TIME_RE = re.compile(
    # 允許：00:00:01.234 或 00:00:01,234 或 00:00:01 --> 00:00:03
    r"(?P<hs>\d{2}):(?P<ms>\d{2}):(?P<ss>\d{2})([.,](?P<hms>\d{1,3}))?"
    r"\s*(-->\s*)?"
    r"(?P<he>\d{2})?:?(?P<me>\d{2})?:?(?P<se>\d{2})?([.,](?P<hme>\d{1,3}))?"
)

def _to_ms(h, m, s, ms):
    h = int(h); m = int(m); s = int(s)
    ms = int(ms) if ms is not None and ms != "" else 0
    if ms < 0: ms = 0
    if ms > 999: ms = 999
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def validate_srt_text(text: str, max_errors=20):
    """
    檢查：
    1) 每段時間格式正確
    2) start < end
    3) 時間不得倒退（下一段 start 不能小於上一段 start）
    """
    errors = []
    blocks = 0
    last_start = None

    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        if "-->" not in line_stripped:
            continue

        m = SRT_TIME_RE.search(line_stripped)
        if not m:
            errors.append(f"第 {idx} 行：時間格式錯誤（應為 00:00:00,000 --> 00:00:00,000）")
            if len(errors) >= max_errors:
                break
            continue

        start_ms = _to_ms(m.group("hs"), m.group("ms"), m.group("ss"), m.group("hms"))
        end_ms = _to_ms(m.group("he"), m.group("me"), m.group("se"), m.group("hme"))

        blocks += 1

        if start_ms >= end_ms:
            errors.append(f"第 {idx} 行：開始時間 >= 結束時間")
        if last_start is not None and start_ms < last_start:
            errors.append(f"第 {idx} 行：時間軸倒退（本段開始小於上一段開始）")

        last_start = start_ms

        if len(errors) >= max_errors:
            break

    if blocks == 0:
        errors.append("找不到任何字幕時間段（沒有 '-->'）")

    return (len(errors) == 0), blocks, errors


def validate_txt_text(text: str, max_errors=20):
    """
    TXT 很多格式不一，這裡採「保守」檢查：
    - 只要找到像時間的行（含 00:00:xx），嘗試解析
    - 若行內同時有 start/end（含 -->）就檢查 start < end
    - 若只有單一時間，檢查時間不得倒退
    """
    errors = []
    blocks = 0
    last_t = None

    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 只有含 "00:00:00" 這種才處理
        if not re.search(r"\d{2}:\d{2}:\d{2}", line_stripped):
            continue

        # 若有 -->，盡量用 srt 的格式
        if "-->" in line_stripped:
            # 嘗試 SRT 解析（允許 , 或 .）
            line_norm = line_stripped.replace(".", ",")
            m = SRT_TIME_RE.search(line_norm)
            if not m:
                errors.append(f"第 {idx} 行：時間格式錯誤")
                if len(errors) >= max_errors:
                    break
                continue

            start_ms = _to_ms(m.group("hs"), m.group("ms"), m.group("ss"), m.group("hms"))
            end_ms = _to_ms(m.group("he"), m.group("me"), m.group("se"), m.group("hme"))

            blocks += 1
            if start_ms >= end_ms:
                errors.append(f"第 {idx} 行：開始時間 >= 結束時間")
            if last_t is not None and start_ms < last_t:
                errors.append(f"第 {idx} 行：時間軸倒退（本段開始小於上一段）")
            last_t = start_ms
        else:
            # 只有單一時間：抓第一個時間
            m = re.search(r"(\d{2}):(\d{2}):(\d{2})([.,](\d{1,3}))?", line_stripped)
            if not m:
                continue
            hh, mm, ss = m.group(1), m.group(2), m.group(3)
            ms = m.group(5) if m.group(5) else "0"
            t_ms = _to_ms(hh, mm, ss, ms)
            blocks += 1

            if last_t is not None and t_ms < last_t:
                errors.append(f"第 {idx} 行：時間軸倒退（此時間小於上一個時間）")
            last_t = t_ms

        if len(errors) >= max_errors:
            break

    if blocks == 0:
        errors.append("找不到任何可解析的時間（例如 00:00:01）")

    return (len(errors) == 0), blocks, errors


def validate_subtitle_file(path: str):
    """
    根據副檔名檢查字幕時間軸
    """
    ext = path.rsplit(".", 1)[1].lower()
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except UnicodeDecodeError:
        # 有些字幕可能是 cp950 / big5，這裡再試一次
        with open(path, "r", encoding="cp950", errors="ignore") as f:
            text = f.read()

    if ext == "srt":
        return validate_srt_text(text)
    else:
        return validate_txt_text(text)


# =============================
# ffprobe 取得影片長度（秒）
# =============================
def probe_duration_sec(video_path: str):
    """
    用 ffprobe 取得影片秒數。若找不到或失敗，回 None。
    """
    try:
        cmd = [
            FFPROBE_BIN,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if r.returncode != 0:
            print(f"[WARN] ffprobe duration failed: {r.stderr.strip()}")
            return None
        val = (r.stdout or "").strip()
        if not val:
            return None
        return int(float(val))
    except Exception as e:
        print(f"[WARN] ffprobe duration exception: {e}")
        return None


# =============================
# ffmpeg 產生縮圖
# =============================
def generate_thumbnail(video_path: str, filename_no_ext: str):
    """
    產生縮圖檔（jpg），回傳相對路徑 uploads/thumbs/xxx.jpg
    若 ffmpeg 不可用或失敗，回 None
    """
    try:
        out_name = f"{filename_no_ext}.jpg"
        out_path = os.path.join(THUMB_DIR, out_name)

        # 取 1 秒處的畫面（可自行調整）
        cmd = [
            FFMPEG_BIN,
            "-y",
            "-ss", "00:00:01",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if r.returncode != 0:
            print(f"[WARN] generate_thumbnail failed: {r.stderr.strip()}")
            return None

        rel = os.path.join("thumbnails", out_name).replace("\\", "/")
        return rel
    except Exception as e:
        print(f"[WARN] generate_thumbnail exception: {e}")
        return None


# =============================
# 診斷端點
# =============================
@admin_upload_bp.get("/health")
def health_check():
    """檢查 MongoDB 連接和數據"""
    try:
        total = db.videos.count_documents({})
        users_total = db.users.count_documents({})
        return jsonify({
            "ok": True,
            "db_connected": True,
            "videos_count": total,
            "users_count": users_total,
            "db_name": db.name
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "db_connected": False,
            "error": str(e)
        }), 500


@admin_upload_bp.get("/debug/videos-raw")
def debug_videos_raw():
    """原始查询测试 - 不经过任何处理"""
    try:
        cursor = db.videos.find({}).limit(5)
        videos = list(cursor)
        result = []
        for v in videos:
            v["_id"] = str(v["_id"])
            result.append(v)
        return jsonify({"ok": True, "count": len(result), "videos": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================
# ✅ 新增：字幕檢查端點
# POST /api/admin_upload/subtitle/validate
# form-data: file
# =============================
@admin_upload_bp.post("/subtitle/validate")
def subtitle_validate():
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "缺少檔案欄位 file"}), 400

    f = request.files["file"]
    if not f or f.filename == "":
        return jsonify({"ok": False, "message": "未選擇檔案"}), 400

    if not allowed_ext(f.filename, ALLOWED_SUB_EXT):
        return jsonify({"ok": False, "message": "字幕格式只支援 .srt / .txt"}), 400

    # 存到暫存（仍放在 uploads/subtitles）
    original_name = f.filename
    original_ext = original_name.rsplit(".", 1)[1].lower()

    safe_name = secure_filename(original_name)
    if not safe_name:
        safe_name = "subtitle"

    uniq = uuid.uuid4().hex[:8]
    save_name = f"validate_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uniq}.{original_ext}"
    save_path = os.path.join(SUBTITLE_DIR, save_name)
    f.save(save_path)

    ok, blocks, errors = validate_subtitle_file(save_path)

    # 驗證用檔案可選擇刪掉（避免堆積）
    try:
        os.remove(save_path)
    except Exception:
        pass

    if ok:
        return jsonify({"ok": True, "blocks": blocks})
    else:
        return jsonify({"ok": False, "errors": errors, "blocks": blocks}), 400


# =============================
# 上傳影片（字幕必填 + 先檢查字幕時間軸）
# POST /api/admin_upload/video
# form-data:
#   unit, title, description, uploaded_by
#   file (video)
#   subtitle (srt/txt) ✅ 必填
# =============================
@admin_upload_bp.post("/video")
def upload_video():
    # 1) 取得 form 欄位
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    uploaded_by = (request.form.get("uploaded_by") or "").strip()
    unit = (request.form.get("unit") or "").strip()

    if not unit or not title:
        return jsonify({"ok": False, "message": "unit 與 title 必填"}), 400

    # 2) 取得影片
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "缺少影片欄位 file"}), 400

    vf = request.files["file"]
    if not vf or vf.filename == "":
        return jsonify({"ok": False, "message": "未選擇影片檔案"}), 400

    if not allowed_ext(vf.filename, ALLOWED_VIDEO_EXT):
        return jsonify({"ok": False, "message": "影片格式不支援（建議 mp4）"}), 400

    # 3) 取得字幕（必填）
    if "subtitle" not in request.files:
        return jsonify({"ok": False, "message": "字幕檔必填（欄位 subtitle）"}), 400

    sf = request.files["subtitle"]
    if not sf or sf.filename == "":
        return jsonify({"ok": False, "message": "字幕檔必填（.srt / .txt）"}), 400

    if not allowed_ext(sf.filename, ALLOWED_SUB_EXT):
        return jsonify({"ok": False, "message": "字幕格式只支援 .srt / .txt"}), 400

    # 影片大小驗證
    file_size = get_file_size(vf)
    if file_size > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_size_mb = file_size / (1024 * 1024)
        return jsonify({
            "ok": False,
            "message": f"影片檔案太大（{actual_size_mb:.1f}MB）。最大限制：{max_size_mb:.0f}MB"
        }), 413

    # 4) 先把字幕存下來，並檢查時間軸
    sub_original_name = sf.filename
    sub_ext = sub_original_name.rsplit(".", 1)[1].lower()

    sub_safe_name = secure_filename(sub_original_name)
    if not sub_safe_name:
        sub_safe_name = "subtitle"

    sub_uniq = uuid.uuid4().hex[:8]
    subtitle_filename = f"{unit}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{sub_uniq}.{sub_ext}"
    subtitle_path = os.path.join(SUBTITLE_DIR, subtitle_filename)
    sf.save(subtitle_path)

    ok_sub, blocks, sub_errors = validate_subtitle_file(subtitle_path)
    if not ok_sub:
        # 字幕有錯：直接回錯，不要繼續上傳影片
        #（並且把字幕檔刪掉，避免堆積）
        try:
            os.remove(subtitle_path)
        except Exception:
            pass

        return jsonify({
            "ok": False,
            "message": "字幕時間軸有錯，請檢查後再上傳",
            "subtitle_errors": sub_errors,
            "blocks": blocks
        }), 400

    # 5) 存影片
    original_name = vf.filename
    video_ext = original_name.rsplit(".", 1)[1].lower()

    safe_name = secure_filename(original_name)
    if not safe_name:
        safe_name = "video"

    uniq = uuid.uuid4().hex[:8]
    filename = f"{unit}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uniq}.{video_ext}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    vf.save(save_path)

    size = os.path.getsize(save_path)
    content_type = vf.mimetype

    # 6) 取得長度 / 產生縮圖（失敗不影響上傳）
    duration_sec = probe_duration_sec(save_path)
    filename_no_ext = filename.rsplit(".", 1)[0]
    thumbnail_rel = generate_thumbnail(save_path, filename_no_ext)

    # 7) 寫入 MongoDB（軟刪除/啟用狀態欄位）
    doc = {
        "unit": unit,
        "title": title,
        "description": description,
        "filename": filename,
        "original_name": original_name,
        "content_type": content_type,
        "size": size,
        "path": os.path.join("uploads", "videos", filename).replace("\\", "/"),
        "uploaded_by": uploaded_by or "admin",
        "created_at": now_utc(),

        # 狀態
        "active": True,
        "deleted": False,
        "deleted_at": None,
        "deleted_by": None,

        # 字幕
        "subtitle_filename": subtitle_filename,
        "subtitle_path": os.path.join("uploads", "subtitles", subtitle_filename).replace("\\", "/"),
        "subtitle_blocks": blocks,

        # 影片資訊
        "duration_sec": duration_sec,
        "thumbnail": thumbnail_rel
    }

    r = db.videos.insert_one(doc)

    return jsonify({
        "ok": True,
        "video_id": str(r.inserted_id),
        "filename": filename,
        "path": doc["path"],
        "thumbnail": doc["thumbnail"],
        "duration_sec": doc["duration_sec"],
        "subtitle_path": doc["subtitle_path"]
    })


# =============================
# 影片清單（分頁/搜尋/分類）
# GET /api/admin_upload/videos?status=active|inactive|deleted&unit=&title=&page=1&per_page=10
# =============================
@admin_upload_bp.get("/videos")
def list_videos():
    try:
        status = (request.args.get("status") or "active").strip()
        q_unit = (request.args.get("unit") or "").strip()
        q_title = (request.args.get("title") or "").strip()

        page = int(request.args.get("page") or 1)
        per_page = int(request.args.get("per_page") or 10)
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10

        q = {}

        # status 分類
        if status == "deleted":
            q["deleted"] = True
        elif status == "inactive":
            q["deleted"] = False
            q["active"] = False
        else:  # active
            q["deleted"] = False
            q["active"] = True

        # 搜尋條件
        if q_unit:
            q["unit"] = q_unit

        if q_title:
            q["title"] = {"$regex": re.escape(q_title), "$options": "i"}

        total = db.videos.count_documents(q)

        cursor = (
            db.videos.find(q)
            .sort("created_at", -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        vids = list(cursor)

        # ObjectId / datetime 序列化
        for v in vids:
            v["_id"] = str(v["_id"])
            if isinstance(v.get("created_at"), datetime):
                v["created_at"] = safe_iso(v["created_at"])
            if isinstance(v.get("deleted_at"), datetime):
                v["deleted_at"] = safe_iso(v["deleted_at"])

            # 防呆欄位
            if "active" not in v:
                v["active"] = True
            if "deleted" not in v:
                v["deleted"] = False

        return jsonify({
            "ok": True,
            "videos": vids,
            "total": total,
            "page": page,
            "per_page": per_page
        })
    except Exception as e:
        return jsonify({"ok": False, "message": "讀取失敗", "error": str(e)}), 500


# =============================
# 啟用/停用
# PATCH /api/admin_upload/video/<video_id>/active  json: {active: true/false}
# =============================
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

    # 已刪除的不允許再切 active（避免狀態混亂）
    v = db.videos.find_one({"_id": vid})
    if not v:
        return jsonify({"ok": False, "message": "找不到影片"}), 404
    if v.get("deleted"):
        return jsonify({"ok": False, "message": "已刪除影片不可切換啟用狀態"}), 400

    r = db.videos.update_one({"_id": vid}, {"$set": {"active": bool(active)}})
    if r.matched_count == 0:
        return jsonify({"ok": False, "message": "找不到影片"}), 404

    return jsonify({"ok": True, "video_id": video_id, "active": bool(active)})


# =============================
# 軟刪除（資料庫不刪除）
# PATCH /api/admin_upload/video/<video_id>/delete  json: {deleted_by: "admin"}
# =============================
@admin_upload_bp.patch("/video/<video_id>/delete")
def soft_delete_video(video_id):
    try:
        vid = ObjectId(video_id)
    except Exception:
        return jsonify({"ok": False, "message": "video_id 格式錯誤"}), 400

    data = request.get_json() or {}
    deleted_by = (data.get("deleted_by") or "admin").strip()

    v = db.videos.find_one({"_id": vid})
    if not v:
        return jsonify({"ok": False, "message": "找不到影片"}), 404
    if v.get("deleted"):
        return jsonify({"ok": False, "message": "此影片已在已刪除分類"}), 400

    db.videos.update_one(
        {"_id": vid},
        {"$set": {
            "deleted": True,
            "deleted_at": now_utc(),
            "deleted_by": deleted_by,
            "active": False
        }}
    )
    return jsonify({"ok": True, "video_id": video_id})


# =============================
# （保留）真刪除端點：如果你未來要用可以保留
# 但依你需求：資料庫不能刪除，所以前端不會呼叫這個
# =============================
@admin_upload_bp.delete("/video/<video_id>")
def delete_video(video_id):
    return jsonify({
        "ok": False,
        "message": "此系統採用軟刪除，資料庫不提供硬刪除。"
    }), 400
