from flask import Blueprint, request, jsonify
from datetime import datetime,timezone
from app.db import db
import os
import re
from openai import OpenAI
from bson import ObjectId

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
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


@student_bp.get("/unit/<unit>/learning")
def unit_learning(unit):
    # 1) 找該單元最新一筆啟用影片
    v = db.videos.find_one(
        {"unit": unit, "active": True, "deleted": False},
        sort=[("created_at", -1)]
    )
    if not v:
        return jsonify({"ok": False, "message": f"{unit} 尚未有啟用中的影片"}), 404

    # 2) 組影片 URL（前端會再加上 BACKEND base）
    video_url = "/" + (v.get("path") or "").lstrip("/")

    # 3) 從字幕檔做「簡易條列重點」（先讓畫面有東西）
    subtitle_path = v.get("subtitle_path") or ""
    bullets = []

    try:
        # subtitle_path 例如 uploads/subtitles/xxx.srt（相對於專案根目錄）
        full = os.path.join(os.getcwd(), subtitle_path.replace("/", os.sep))
        with open(full, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = f.read()

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        for ln in lines:
            # 跳過序號
            if re.fullmatch(r"\d+", ln):
                continue
            # 跳過時間軸
            if "-->" in ln:
                continue
            # 跳過像 00:00:00,000 這類
            if re.search(r"\d{2}:\d{2}:\d{2}", ln):
                continue

            # 太短的不要
            if len(ln) < 6:
                continue

            bullets.append(ln)

            if len(bullets) >= 5:
                break

        if not bullets:
            bullets = ["（字幕讀得到，但沒抽到可用文字，可能字幕格式比較特別）"]

    except Exception as e:
        bullets = [f"（讀字幕失敗：{str(e)}）"]

    return jsonify({
        "ok": True,
        "video": {
            "unit": v.get("unit"),
            "title": v.get("title"),
            "video_url": video_url,
            "video_id": str(v.get("_id"))
        },
        "bullets": bullets
    })

# AI 生成學習建議
@student_bp.post("/unit/<unit>/bullets/regenerate")
def regenerate_bullets(unit):
    # 1) 找該單元最新影片（你可依你的規則：active=true, deleted=false）
    v = db.videos.find_one(
        {"unit": unit, "deleted": False, "active": True},
        sort=[("created_at", -1)]
    )
    if not v:
        return jsonify({"ok": False, "message": "找不到此單元影片"}), 404

    subtitle_path = v.get("subtitle_path")  # 例如 uploads/subtitles/xxx.srt
    if not subtitle_path:
        return jsonify({"ok": False, "message": "此影片沒有字幕檔"}), 400

    # 2) 讀字幕內容（注意你的 subtitle_path 是相對路徑）
    project_root = os.getcwd()
    full_path = os.path.join(project_root, subtitle_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        return jsonify({"ok": False, "message": "字幕檔案不存在"}), 404

    with open(full_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        subtitle_text = f.read()

    # 3) 呼叫 AI 產生重點（條列式）
    # 用 Responses API（官方推薦的新介面） :contentReference[oaicite:1]{index=1}
    prompt = f"""
你是一位程式設計助教。請根據以下影片字幕，整理「學生容易犯錯的觀念」與「本段重點」。
輸出規則：
- 只輸出 3~6 點條列
- 每點不超過 25 字
- 用繁體中文
- 不要加多餘前言，不要編號（只要每點內容）
- 請避免重複上一版內容，換另一個角度描述。
字幕如下：
{subtitle_text[:8000]}
""".strip()

    try:
        resp = client.responses.create(
            model="gpt-5",
            reasoning={"effort": "low"},
            input=prompt
        )
        text = (resp.output_text or "").strip()

        # 4) 把模型輸出的每一行整理成 bullets
        lines = [x.strip("•- \t").strip() for x in text.splitlines() if x.strip()]
        bullets = [x for x in lines if len(x) > 0][:6]

        return jsonify({"ok": True, "bullets": bullets})
    except Exception as e:
        return jsonify({"ok": False, "message": f"AI 生成失敗：{str(e)}"}), 500

# 紀錄學習開始/結束時間 
def now_utc():
    return datetime.now(timezone.utc)

# @student_bp.post("/learning/start")
# def learning_start():
#     data = request.get_json() or {}
#     participant_id = (data.get("participant_id") or "").strip()
#     unit = (data.get("unit") or "").strip()

#     if not participant_id or not unit:
#         return jsonify({"ok": False, "message": "缺少 participant_id 或 unit"}), 400

#     r = db.learning_logs.insert_one({
#         "participant_id": participant_id,
#         "unit": unit,
#         "start_at": now_utc(),
#         "end_at": None,
#         "duration_sec": None,
#         "regen_clicks": 0
#     })

#     return jsonify({"ok": True, "log_id": str(r.inserted_id)})

@student_bp.post("/learning/end")
def learning_end():
    data = request.get_json() or {}
    log_id = (data.get("log_id") or "").strip()
    duration_sec = data.get("duration_sec", None)
    regen_clicks = data.get("regen_clicks", 0)

    try:
        oid = ObjectId(log_id)
    except Exception:
        return jsonify({"ok": False, "message": "log_id 格式錯誤"}), 400

    db.learning_logs.update_one(
        {"_id": oid},
        {"$set": {
            "end_at": now_utc(),
            "duration_sec": int(duration_sec or 0),
            "regen_clicks": int(regen_clicks or 0)
        }}
    )

    return jsonify({"ok": True})


# =========================
# 1) 進入學習頁：建立 log
# POST /api/student/learning/start
# body: { participant_id, unit }
# =========================
@student_bp.post("/learning/start")
def learning_start():
    data = request.get_json() or {}
    participant_id = (data.get("participant_id") or "").strip()
    unit = (data.get("unit") or "").strip()

    if not participant_id or not unit:
        return jsonify({"ok": False, "message": "缺少 participant_id 或 unit"}), 400

    r = db.learning_logs.insert_one({
        "participant_id": participant_id,
        "unit": unit,
        "start_at": now_utc(),
        "end_at": None,
        "duration_sec": None,
        "regen_clicks": 0,
        "understood": None
    })

    return jsonify({"ok": True, "log_id": str(r.inserted_id)})

# =========================
# 2) 離開學習頁：結束 log
# POST /api/student/learning/end
# body: { log_id, duration_sec, regen_clicks, understood }
# =========================
@student_bp.post("/learning/end")
def learning_end():
    data = request.get_json() or {}
    log_id = (data.get("log_id") or "").strip()
    duration_sec = data.get("duration_sec", None)
    regen_clicks = data.get("regen_clicks", 0)
    understood = data.get("understood", None)  # true/false/null

    if not log_id:
        return jsonify({"ok": False, "message": "缺少 log_id"}), 400

    try:
        _id = ObjectId(log_id)
    except Exception:
        return jsonify({"ok": False, "message": "log_id 格式錯誤"}), 400

    update = {
        "end_at": now_utc(),
        "regen_clicks": int(regen_clicks or 0)
    }

    # duration_sec 允許缺省（例如 beforeunload 來不及算）
    if duration_sec is not None:
        update["duration_sec"] = int(duration_sec)

    # understood 只允許 True/False/None
    if understood in [True, False, None]:
        update["understood"] = understood

    db.learning_logs.update_one({"_id": _id}, {"$set": update})
    return jsonify({"ok": True})

# =========================
# 3) 取得單元學習頁資料（影片 + bullets）
# GET /api/student/unit/<unit>/learning
# =========================
@student_bp.get("/unit/<unit>/learning")
def unit_learning(unit):
    unit = (unit or "").strip()
    if not unit:
        return jsonify({"ok": False, "message": "unit 不可為空"}), 400

    # 影片：從老師端 videos 找該 unit 的「啟用中」最新一筆
    v = db.videos.find_one({"unit": unit, "deleted": False, "active": True}, sort=[("created_at", -1)])
    if not v:
        return jsonify({"ok": True, "video": None, "bullets": []})

    video = {
        "unit": v.get("unit"),
        "title": v.get("title"),
        "video_url": "/" + (v.get("path") or "").lstrip("/"),
        "subtitle_path": "/" + (v.get("subtitle_path") or "").lstrip("/"),
    }

    # bullets：從 unit_bullets 讀快取
    bdoc = db.unit_bullets.find_one({"unit": unit})
    bullets = (bdoc or {}).get("bullets") or []

    return jsonify({"ok": True, "video": video, "bullets": bullets})

# =========================
# 4) 我不懂：重新生成 bullets 並存回 DB（安全版：先用字幕規則摘要/佔位）
# POST /api/student/unit/<unit>/bullets/regenerate
# =========================
@student_bp.post("/unit/<unit>/bullets/regenerate")
def bullets_regenerate(unit):
    unit = (unit or "").strip()
    if not unit:
        return jsonify({"ok": False, "message": "unit 不可為空"}), 400

    # 先抓字幕檔（老師端上傳的字幕路徑）
    v = db.videos.find_one({"unit": unit, "deleted": False, "active": True}, sort=[("created_at", -1)])
    if not v:
        return jsonify({"ok": False, "message": "找不到該單元影片"}), 404

    # ✅ 企業安全方法：先做「非 AI」版摘要（可跑、可存、可評估）
    # 你之後再換成真的 LLM API（OpenAI/Gemini）即可
    subtitle_path = v.get("subtitle_path")  # e.g. uploads/subtitles/xxx.srt
    bullets = [
        f"本單元：{v.get('title') or unit}",
        "重點 1：請確認輸入/輸出格式是否符合題目",
        "重點 2：常見錯誤：型態轉換（int/float）",
        "重點 3：遇到錯誤先看錯誤訊息，再找出對應行數"
    ]

    db.unit_bullets.update_one(
        {"unit": unit},
        {"$set": {
            "unit": unit,
            "bullets": bullets,
            "updated_at": now_utc()
        }},
        upsert=True
    )

    return jsonify({"ok": True, "bullets": bullets})