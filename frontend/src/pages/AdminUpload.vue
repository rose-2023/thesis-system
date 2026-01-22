<template>
  <div class="page">
    <div class="card">
      <h2>老師端：上傳影片</h2>

      <div class="row">
        <label>單元（unit）</label>
        <input v-model="unit" placeholder="例如：U1" />
      </div>

      <div class="row">
        <label>標題</label>
        <input v-model="title" placeholder="例如：單元一：迴圈基礎" />
      </div>

      <div class="row">
        <label>描述（可選）</label>
        <textarea v-model="description" rows="3" placeholder="簡短描述"></textarea>
      </div>

      <div class="row">
        <label>選擇影片（建議 mp4）</label>
        <input type="file" accept="video/*" @change="onFile" />
      </div>

      <button class="btn" :disabled="loading" @click="upload">
        {{ loading ? "上傳中…" : "開始上傳" }}
      </button>

      <p v-if="msg" class="msg">{{ msg }}</p>
      <p v-if="err" class="err">{{ err }}</p>

      <hr />

      <button class="btn2" @click="loadList">刷新影片清單</button>
      <div v-if="videos.length" class="list">
        <div class="item" v-for="v in videos" :key="v._id">
            <div class="t">
            {{ v.unit }}｜{{ v.title }}
            <span class="tag" :class="(v.active ?? true) ? 'on' : 'off'">
                {{ (v.active ?? true) ? "啟用中" : "已停用" }}
            </span>
            </div>

            <div class="s">{{ v.filename }}</div>
            <div class="s">上傳時間：{{ v.created_at }}</div>

            <div class="actions">
            <button class="btnSmall" @click="toggleActive(v)">
                {{ v.active ? "停用" : "啟用" }}
            </button>

            <button class="btnSmall danger" @click="removeVideo(v)">
                刪除
            </button>
            </div>
        </div>
        </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { api } from "../api";

const unit = ref("U1");
const title = ref("");
const description = ref("");
const file = ref(null);

const loading = ref(false);
const msg = ref("");
const err = ref("");

const videos = ref([]);

function onFile(e) {
  file.value = e.target.files?.[0] || null;
}

async function upload() {
  msg.value = "";
  err.value = "";

  if (!unit.value || !title.value) {
    err.value = "unit 與 title 必填";
    return;
  }
  if (!file.value) {
    err.value = "請選擇影片檔案";
    return;
  }

  loading.value = true;
  try {
    const form = new FormData();
    form.append("unit", unit.value);
    form.append("title", title.value);
    form.append("description", description.value);

    // 先用 localStorage 的 participant_id 當作 uploaded_by
    form.append("uploaded_by", localStorage.getItem("participant_id") || "admin");

    form.append("file", file.value);

    const res = await api.post("/api/admin/video", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });

    if (!res.data?.ok) {
      err.value = res.data?.message || "上傳失敗";
      return;
    }

    msg.value = `✅ 上傳成功：${res.data.filename}`;
    await loadList();
  } catch (e) {
    err.value = e?.response?.data?.message || e.message || "上傳失敗";
  } finally {
    loading.value = false;
  }
}

// async function loadList() {
//   err.value = "";
//   const res = await api.get("/api/admin/videos");
//   if (res.data?.ok) videos.value = res.data.videos || [];
// }


// 切換影片啟用狀態
async function toggleActive(v) {
  err.value = "";
  try {
    const nowActive = v.active ?? true;
    const res = await api.patch(`/api/admin/video/${v._id}/active`, {
      active: !nowActive
    });
    v.active = res.data.active;

    if (!res.data?.ok) {
      err.value = res.data?.message || "切換失敗";
      return;
    }

    // 直接更新本地狀態，或重抓列表
    v.active = res.data.active;
  } catch (e) {
    err.value = e?.response?.data?.message || e.message || "切換失敗";
  }
}
// 錯誤載入影片列表
async function loadList() {
  err.value = "";
  try {
    const res = await api.get("/api/admin/videos");
    if (res.data?.ok) videos.value = res.data.videos || [];
    else err.value = res.data?.message || "讀取失敗";
  } catch (e) {
    err.value = e?.response?.data?.message || e.message || "讀取失敗";
  }
}


// 刪除影片
async function removeVideo(v) {
  err.value = "";
  const ok = confirm(`確定要刪除影片：\n${v.title}\n（會同時刪除檔案）`);
  if (!ok) return;

  try {
    const res = await api.delete(`/api/admin/video/${v._id}`);
    if (!res.data?.ok) {
      err.value = res.data?.message || "刪除失敗";
      return;
    }
    msg.value = `✅ 已刪除：${v.title}（檔案刪除：${res.data.file_deleted ? "成功" : "失敗"}）`;
    await loadList();
  } catch (e) {
    err.value = e?.response?.data?.message || e.message || "刪除失敗";
  }
}

</script>

<style scoped>
.page{ min-height:100vh; display:grid; place-items:center; padding:24px; }
.card{ width:100%; max-width:720px; border:1px solid #ddd; border-radius:14px; padding:18px; background:#fff; }
.row{ margin:12px 0; display:flex; flex-direction:column; gap:6px; }
input, textarea{ padding:10px; border:1px solid #ddd; border-radius:10px; }
.btn{ width:100%; padding:10px; border:0; border-radius:10px; cursor:pointer; }
.btn2{ width:100%; padding:10px; border:1px solid #ddd; border-radius:10px; cursor:pointer; background:#fafafa; }
.msg{ color:#065f46; font-weight:600; margin-top:10px; }
.err{ color:#b91c1c; font-weight:600; margin-top:10px; }
.list{ margin-top:12px; display:flex; flex-direction:column; gap:10px; }
.item{ padding:10px; border:1px solid #eee; border-radius:12px; }
.t{ font-weight:700; }
.s{ font-size:12px; color:#555; }
.actions{ display:flex; gap:10px; margin-top:10px; }
.btnSmall{ padding:8px 10px; border-radius:10px; border:1px solid #ddd; cursor:pointer; background:#fafafa; }
.btnSmall.danger{ border-color: rgba(185,28,28,.35); color:#b91c1c; background: rgba(185,28,28,.06); }
.tag{ margin-left:10px; padding:3px 8px; border-radius:999px; font-size:12px; }
.tag.on{ background: rgba(5,150,105,.12); color:#065f46; border:1px solid rgba(5,150,105,.22); }
.tag.off{ background: rgba(185,28,28,.10); color:#991b1b; border:1px solid rgba(185,28,28,.22); }

</style>
