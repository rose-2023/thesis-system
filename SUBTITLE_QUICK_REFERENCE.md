# 字幕系統快速參考

## 用戶流程圖

```
┌─────────────────┐
│  AdminUpload.vue │  影片上傳頁面
└────────┬────────┘
         │
         ├─ 1️⃣ 上傳影片檔案
         │
         ├─ 2️⃣ 上傳 SRT 字幕檔
         │     └─ ✅ 字幕存到 uploads/subtitles/{video_id}.json
         │
         └─ 3️⃣ 點擊 [📝 字幕校正] 按鈕
                    ↓
         ┌─────────────────────────┐
         │ TeacherSubtitles.vue    │  字幕編輯頁面
         │ /admin/subtitles?...    │
         └────────┬────────────────┘
                  │
                  ├─ 4️⃣ 若需要：重新上傳字幕檔
                  │
                  ├─ 5️⃣ 編輯字幕內容
                  │     ├─ 新增/刪除/合併字幕行
                  │     ├─ 修改時間軸
                  │     ├─ 修改字幕文字
                  │     └─ 點擊 [自動校正] 修復問題
                  │
                  ├─ 6️⃣ 點擊 [儲存]
                  │     └─ ✅ 字幕被保存到資料庫
                  │
                  └─ 7️⃣ 匯出字幕
                        ├─ [匯出 SRT]  → subtitles_{video_id}.srt
                        └─ [匯出 JSON] → subtitles_{video_id}.json
```

---

## 關鍵 UI 元素

### AdminUpload.vue

```vue
<!-- 上傳 SRT 字幕檔 -->
<div class="subCard">
  <div class="subTitle">字幕 / 逐字稿校正（SRT / TXT）</div>
  <input type="file" accept=".srt,.txt" @change="onSubtitleFile" />
  <button @click="validateSubtitleOnly">檢查字幕時間軸</button>
  <button @click="upload">開始上傳</button>
</div>

<!-- 進入字幕編輯 -->
<button class="btnSmall" @click="goSubtitles(v)">📝 字幕校正</button>
```

### TeacherSubtitles.vue

```vue
<!-- 新增：上傳字幕檔區段 -->
<div class="uploadSection">
  <div class="uploadTitle">上傳字幕檔</div>
  <input type="file" accept=".srt,.txt" ref="subtitleInput" @change="onSubtitleFileChange" />
  <button @click="upload">{{ uploading ? "上傳中…" : "上傳" }}</button>
</div>

<!-- 字幕編輯工具列 -->
<button @click="addLine">新增一行</button>
<button @click="mergeSelected">合併</button>
<button @click="deleteSelected">刪除</button>
<button @click="autoFix">自動校正</button>

<!-- 保存和匯出 -->
<button @click="save">儲存</button>
<button @click="exportSrt">匯出 SRT</button>
<button @click="exportJson">匯出 JSON</button>
```

---

## 關鍵代碼片段

### 前端：獲取 Video ID
```javascript
const videoId = computed(() => route.query.video_id || "");
const resolvedVideoId = computed(() =>
  route.query.video_id ||
  route.query.id ||
  route.query.videoId ||
  route.params.video_id ||
  route.params.id ||
  ""
);

function getVideoId() {
  return videoId.value || resolvedVideoId.value || "";
}
```

### 前端：上傳字幕檔
```javascript
async function upload() {
  const vid = getVideoId();
  if (!vid || !subtitleFile.value) return;
  
  const fd = new FormData();
  fd.append("video_id", vid);
  fd.append("file", subtitleFile.value);

  const res = await fetch("http://127.0.0.1:5000/api/admin/subtitles/upload", {
    method: "POST",
    body: fd,
  });
  
  const data = await res.json();
  if (data.ok) {
    await loadSubtitles();
  }
}
```

### 前端：保存字幕
```javascript
async function save() {
  const vid = getVideoId();
  if (!vid) return;

  const res = await fetch(`${API_BASE}/api/admin/subtitles/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_id: vid,
      rows: rows.value
    })
  });
  const data = await res.json();
  if (data.ok) msg.value = "✅ 已儲存";
}
```

### 後端：上傳字幕 API
```python
@admin_subtitles_bp.post("/subtitles/upload")
def upload_subtitles():
    video_id = request.form.get("video_id", "").strip()
    f = request.files.get("file")
    
    if not f.filename.lower().endswith(".srt"):
        return jsonify({"ok": False, "message": "only .srt is supported"}), 400
    
    content = f.read().decode("utf-8-sig", errors="replace")
    rows = parse_srt_to_rows(content)
    
    with open(_json_path(video_id), "w", encoding="utf-8") as out:
        json.dump(
            {"ok": True, "video_id": video_id, "rows": rows},
            out,
            ensure_ascii=False,
            indent=2
        )
    
    return jsonify({"ok": True, "count": len(rows)})
```

### 後端：保存字幕 API
```python
@admin_subtitles_bp.post("/subtitles/save")
def save_subtitles():
    data = request.get_json(force=True) or {}
    video_id = str(data.get("video_id", "")).strip()
    rows = data.get("rows", [])
    
    with open(_json_path(video_id), "w", encoding="utf-8") as f:
        json.dump(
            {"ok": True, "video_id": video_id, "rows": rows},
            f,
            ensure_ascii=False,
            indent=2
        )
    return jsonify({"ok": True})
```

---

## 資料格式

### SRT 格式（標準）
```
1
00:00:01,570 --> 00:00:02,800
兩數總和，我們要一下朝目說明輸入，在奇兩個數字，然後計算總和並

2
00:00:11,010 --> 00:00:11,010
輸出，是一個數值練習的練習，假使說你
```

### JSON 格式（內部存儲）
```json
{
  "ok": true,
  "video_id": "697c6aab07c9dbfbed2b0a28",
  "rows": [
    {
      "id": "1",
      "start": "00:00:01,570",
      "end": "00:00:02,800",
      "text": "字幕文字"
    },
    {
      "id": "2",
      "start": "00:00:11,010",
      "end": "00:00:11,010",
      "text": "下一段文字"
    }
  ]
}
```

---

## 時間軸操作

### 格式轉換
```
正確格式：HH:MM:SS,mmm 或 HH:MM:SS.mmm
系統自動轉換：
  00:00:01.570  →  00:00:01,570
  00:00:01,570  →  (保持不變)
```

### 時間計算
```
parseTimeToMs("00:00:01,570")  →  1570 ms
msToSrtTime(1570)              →  "00:00:01,570"
```

---

## 錯誤排查

| 問題 | 可能原因 | 解決方案 |
|------|--------|--------|
| 上傳時出現 "only .srt is supported" | 上傳了 .txt 或其他格式 | 確保檔案副檔名為 .srt |
| 字幕沒有載入 | video_id 不匹配 | 檢查 URL query 參數 |
| 時間軸有問題警告 | 時間格式不正確或重疊 | 點擊 [自動校正] 或手動修改 |
| 儲存失敗 | 影片 ID 不存在 | 確保影片已上傳到系統 |
| 字幕文字顯示亂碼 | 編碼問題 | 確保 SRT 檔使用 UTF-8 編碼 |

---

## 修改記錄

### 2026-01-30

#### TeacherSubtitles.vue
- ✅ 新增上傳字幕檔 UI 區段
- ✅ 修復 `videoId` 引用 bug（改用 `getVideoId()` 函數）
- ✅ 改進 `upload()` 函數
- ✅ 改進 `save()` 和 `exportJson()` 函數
- ✅ 改進 `loadSubtitles()` 錯誤處理
- ✅ 新增樣式類別

#### AdminUpload.vue
- ✅ 修正 `goSubtitles()` 函數傳遞單元和標題

#### admin_subtitles.py（後端）
- ✅ 修正資料庫連接（改用 `from app.db import db`）
- ✅ 移除無效的 import

---

## 相關檔案

```
thesis-system/
├── frontend/src/pages/
│   ├── AdminUpload.vue          ← 影片上傳 + 字幕上傳
│   └── TeacherSubtitles.vue     ← 字幕編輯
├── app/routes/
│   ├── admin_upload.py          ← 影片 API
│   └── admin_subtitles.py       ← 字幕 API
├── uploads/
│   ├── subtitles/               ← 字幕檔案儲存位置
│   ├── videos/                  ← 影片檔案儲存位置
│   └── thumbnails/              ← 縮圖檔案儲存位置
└── app/
    └── db.py                    ← 資料庫連接
```

---

**最後更新**: 2026-01-30
**系統狀態**: ✅ 生產就緒
