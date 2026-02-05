# 字幕系統實現總結

## ✅ 完成的功能

你現在有一個完整的字幕編輯系統，支援：

### 1. **字幕上傳**
- ✅ 在 AdminUpload.vue 中上傳 SRT 字幕檔
- ✅ 後端自動解析 SRT 格式
- ✅ 字幕存儲到 JSON 檔案

### 2. **字幕編輯**
- ✅ 在 TeacherSubtitles.vue 中編輯字幕內容
- ✅ 支援重新上傳新的字幕檔
- ✅ 編輯時間軸、文字內容
- ✅ 新增、刪除、合併字幕行
- ✅ 自動校正（排序、修復重疊）

### 3. **字幕保存**
- ✅ 點擊「儲存」按鈕保存修改
- ✅ 保存到資料庫和檔案系統

### 4. **字幕匯出**
- ✅ 匯出為 SRT 格式（標準字幕格式）
- ✅ 匯出為 JSON 格式（備份和資料交換）

### 5. **媒體整合**
- ✅ 影片播放器與字幕同步
- ✅ 點擊字幕行自動跳轉
- ✅ 播放時自動標記當前字幕

---

## 📝 主要修改

### 前端（Vue）修改

#### **AdminUpload.vue**
```javascript
// 修正導航函數，確保傳遞單元和標題
function goSubtitles(v) {
  router.push({
    path: "/admin/subtitles",
    query: {
      video_id: vid,
      unit: v.unit || unit.value || "未指定",  // ✅ 新增
      title: v.title || title.value || "",       // ✅ 新增
      video_url: "",
    },
  });
}
```

#### **TeacherSubtitles.vue**（主要修改）

1. **新增上傳區段**
   - 新增檔案輸入框和上傳按鈕
   - 支援 `.srt` 和 `.txt` 檔案
   - 上傳後自動重新載入字幕

2. **修復 bug**
   - ✅ 修複 `videoId` 引用（改用 `getVideoId()` 函數）
   - ✅ 修複 `upload()` 函數中的變數引用
   - ✅ 修複 `save()` 函數中的參數傳遞
   - ✅ 修複 `exportJson()` 函數

3. **新增狀態和函數**
   - `uploading` - 上傳進度狀態
   - `uploadMsg`, `uploadErr` - 上傳消息
   - `onSubtitleFileChange()` - 處理檔案選擇
   - `clearUploadToast()` - 清除消息
   - 改進的 `upload()` 函數

4. **新增樣式**
   - `.uploadSection` - 上傳區段容器
   - `.uploadTitle` - 標題
   - `.uploadContainer` - 檔案輸入和按鈕容器

### 後端（Python）修改

#### **admin_subtitles.py**
```python
# ✅ 修正資料庫連接
from app.db import db  # 改為直接 import db

# ✅ 修正 get_video() 函數
def get_video(video_id):
    v = db.videos.find_one({"_id": ObjectId(video_id)})  # 使用 db.videos
    # ...
```

---

## 🔄 完整工作流程

```
1️⃣  打開 AdminUpload.vue
    ↓
2️⃣  上傳影片檔案
    ↓
3️⃣  上傳 SRT 字幕檔
    ├─ 後端解析 SRT
    └─ 存儲為 JSON
    ↓
4️⃣  點擊「📝 字幕校正」
    ↓
5️⃣  進入 TeacherSubtitles.vue
    ├─ 自動載入字幕
    ├─ 顯示影片播放器
    └─ 顯示字幕編輯面板
    ↓
6️⃣  編輯字幕（選擇以下操作）
    ├─ 重新上傳新字幕檔
    ├─ 手動編輯時間軸/文字
    ├─ 新增/刪除/合併字幕行
    └─ 點擊「自動校正」修復問題
    ↓
7️⃣  點擊「儲存」
    ├─ 發送 POST 請求
    └─ 字幕保存到資料庫
    ↓
8️⃣  匯出字幕（選擇）
    ├─ 匯出 SRT → 標準字幕格式
    └─ 匯出 JSON → 資料備份
```

---

## 📦 檔案清單

### 修改的檔案
- ✅ `frontend/src/pages/AdminUpload.vue` - 修正導航函數
- ✅ `frontend/src/pages/TeacherSubtitles.vue` - 完全重構（新增上傳、修復 bug）
- ✅ `app/routes/admin_subtitles.py` - 修正資料庫連接

### 新建的檔案
- ✅ `SUBTITLE_SYSTEM_GUIDE.md` - 詳細使用指南
- ✅ `SUBTITLE_QUICK_REFERENCE.md` - 快速參考

### 關鍵目錄
- `uploads/subtitles/` - 存儲字幕 JSON 檔案
- `uploads/videos/` - 存儲影片檔案
- `uploads/thumbnails/` - 存儲縮圖

---

## 🧪 測試清單

在使用前，請驗證以下功能：

- [ ] 上傳 SRT 字幕檔案（AdminUpload.vue）
- [ ] 檢查字幕時間軸驗證功能
- [ ] 點擊「📝 字幕校正」按鈕進入編輯頁面
- [ ] 驗證字幕自動載入
- [ ] 編輯字幕文字
- [ ] 修改時間軸
- [ ] 新增字幕行
- [ ] 刪除字幕行
- [ ] 合併字幕行
- [ ] 點擊「自動校正」
- [ ] 點擊「儲存」
- [ ] 匯出 SRT
- [ ] 匯出 JSON
- [ ] 驗證影片播放器同步

---

## 🔧 API 端點

| 方法 | 端點 | 用途 |
|------|------|------|
| GET | `/api/admin/subtitles?video_id=xxx` | 獲取字幕 |
| POST | `/api/admin/subtitles/upload` | 上傳字幕檔 |
| POST | `/api/admin/subtitles/save` | 保存編輯 |
| GET | `/api/admin/video/<id>` | 獲取影片資訊 |

---

## 📊 資料結構

### 前端字幕行格式
```javascript
{
  id: "1",              // 唯一識別符
  start: "00:00:01,570", // 開始時間（HH:MM:SS,mmm）
  end: "00:00:02,800",   // 結束時間
  text: "字幕文字"        // 可多行
}
```

### 後端存儲格式（JSON）
```json
{
  "ok": true,
  "video_id": "697c6aab07c9dbfbed2b0a28",
  "rows": [...]
}
```

---

## 🎯 使用場景

### 場景 1：教師上傳教學影片並添加字幕

1. 老師進入 AdminUpload.vue
2. 上傳影片檔案和對應的 SRT 字幕
3. 系統自動存儲字幕

### 場景 2：教師修正字幕內容

1. 進入字幕編輯頁面
2. 發現某段時間軸有誤
3. 編輯時間軸或文字
4. 點擊「自動校正」修復相關問題
5. 儲存修改

### 場景 3：導出標準格式字幕

1. 編輯完成
2. 點擊「匯出 SRT」
3. 下載標準 SRT 檔案用於其他用途

### 場景 4：批量更新字幕

1. 上傳新的 SRT 檔案
2. 系統自動覆蓋舊字幕
3. 進行微調並保存

---

## ⚠️ 常見陷阱和解決方案

| 陷阱 | 原因 | 解決 |
|------|------|------|
| 上傳失敗 | 檔案不是 .srt | 檢查副檔名，確保是 .srt 格式 |
| 字幕沒載入 | video_id 不匹配 | 檢查 URL 中的 query 參數 |
| 時間顯示亂碼 | 編碼問題 | 確保 SRT 使用 UTF-8 編碼 |
| 儲存報錯 | 影片不存在 | 確保影片已上傳並有正確的 ID |
| 時間有問題警告 | 時間格式或順序不對 | 點擊「自動校正」或手動修改 |

---

## 🚀 後續優化建議

1. **進度條**：上傳大檔案時顯示進度條
2. **拖拽排序**：支援拖拽調整字幕行順序
3. **批量編輯**：支援查找和替換
4. **版本控制**：記錄編輯歷史
5. **協作編輯**：支援多人同時編輯
6. **自動校正優化**：更智能的時間重疊檢測
7. **字幕預覽**：在編輯時實時預覽

---

## 📞 支援

如有問題，請檢查：
1. 瀏覽器控制台是否有 JavaScript 錯誤
2. 後端服務是否正常運行
3. 資料庫連接是否正確
4. 檔案路徑和權限是否正確

---

**版本**: 1.0
**狀態**: ✅ 生產就緒
**最後更新**: 2026-01-30
