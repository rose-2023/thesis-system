<template>
  <div class="page">
    <div class="bar">
      <div class="barTitle">單元列表</div>
      <div class="barMid">{{ unit }}：{{ videoTitle || "載入中…" }}</div>
    </div>

    <div class="grid">
      <!-- 左：影片 -->
      <div class="leftCard">
        <video v-if="videoUrl" class="player" controls :src="videoUrl"></video>
        <div v-else class="placeholder">
          {{ loading ? "載入影片中…" : (err || "找不到影片") }}
        </div>
      </div>

      <!-- 右：AI 重點 -->
      <div class="rightCard">
        <div class="rightHeader">AI 重點回饋（依據影片字幕）</div>

        <ul class="bullets" v-if="bullets.length">
          <li v-for="(b,i) in bullets" :key="i">{{ b }}</li>
        </ul>
        <div v-else class="muted">目前沒有重點</div>

        <div class="actions">
            <button class="btnGhost" type="button" @click="understand">我看懂了</button>

            <button
                class="btnDanger"
                type="button"
                @click="notUnderstand"
                :disabled="regenLoading"
            >
                {{ regenLoading ? "AI 生成中…" : "我不懂（再生成）" }}
            </button>
        </div>


        <button class="btnNext" @click="goParsons">
          下一步：開始練習 Parsons
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";

const route = useRoute();

// ✅ 只宣告一次
const unit = ref(route.params.unit || "U1");



const loading = ref(false);
const err = ref("");
const videoUrl = ref("");
const videoTitle = ref("");
const bullets = ref([]);
const regenLoading = ref(false);

const learnLogId = ref("");            // 後端回來的一筆紀錄 id
const startAt = ref(0);
const regenClicks = ref(0);

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const res = await api.get(`/api/student/unit/${unit.value}/learning`);
    if (!res.data?.ok) throw new Error(res.data?.message || "讀取失敗");

    const BACKEND = "http://127.0.0.1:5000";
    videoUrl.value = BACKEND + res.data.video.video_url;
    videoTitle.value = res.data.video.title || "";
    bullets.value = res.data.bullets || [];
  } catch (e) {
    err.value = e?.response?.data?.message || e.message || "讀取失敗";
  } finally {
    loading.value = false;
  }
}

function understand() {
  alert("已記錄：我看懂了（之後可存到後端）");
}

// function notUnderstand() {
//   alert("下一步我帶你做：重新生成右側重點（先用字幕規則摘要，之後可接真正AI）");
// }

function goParsons() {
  router.push("/parsons"); // 你之後可改成 /parsons/:unit
}

// 重新生成重點
// async function notUnderstand() {
//   regenLoading.value = true;
//   try {
//     const res = await api.post(`/api/student/unit/${unit.value}/bullets/regenerate`);
//     if (!res.data?.ok) throw new Error(res.data?.message || "重新生成失敗");
//     bullets.value = res.data.bullets || [];
//   } catch (e) {
//     alert(e?.response?.data?.message || e.message || "重新生成失敗");
//   } finally {
//     regenLoading.value = false;
//   }
// }

// 進入頁面：開始計時 + 建立一筆 log
async function startLearning() {
  startAt.value = Date.now();
  const participantId = localStorage.getItem("participant_id") || "unknown";

  const res = await api.post("/api/student/learning/start", {
    participant_id: participantId,
    unit: unit.value
  });

  if (res.data?.ok) learnLogId.value = res.data.log_id;
}

// 離開頁面：結束計時 + 更新那筆 log
async function endLearning() {
  if (!learnLogId.value) return;

  const durationSec = Math.floor((Date.now() - startAt.value) / 1000);

  try {
    await api.post("/api/student/learning/end", {
      log_id: learnLogId.value,
      duration_sec: durationSec,
      regen_clicks: regenClicks.value
    });
  } catch (e) {
    // 離開時失敗很常見，不要卡住使用者
    console.warn("endLearning failed", e);
  }
}

async function notUnderstand() {
  regenClicks.value += 1;
  regenLoading.value = true;

  try {
    const res = await api.post(
      `/api/student/unit/${unit.value}/bullets/regenerate`
    );

    if (!res.data?.ok) {
      throw new Error(res.data?.message || "重新生成失敗");
    }

    bullets.value = res.data.bullets || [];
  } catch (e) {
    alert(e?.response?.data?.message || e.message || "重新生成失敗");
  } finally {
    regenLoading.value = false;
  }
}

onMounted(startLearning);
onBeforeUnmount(endLearning);

// ⚠️ 使用者直接關分頁/重整：也要補一次
window.addEventListener("beforeunload", endLearning);




onMounted(load);
</script>

<style scoped>
.page { padding: 18px 20px; background:#fff; min-height:100vh; }
.bar { display:flex; align-items:center; gap:16px; padding: 10px 12px; border-bottom:1px solid #eee; }
.barTitle { font-weight:1000; font-size:22px; }
.barMid { margin-left:auto; font-weight:900; }

.grid { display:grid; grid-template-columns: 1.2fr 1fr; gap:16px; margin-top:16px; }

.leftCard { border:1px solid #e5e7eb; border-radius:14px; overflow:hidden; background:#111; min-height:420px; display:flex; }
.player { width:100%; height:100%; }
.placeholder { color:#fff; margin:auto; padding:24px; }

.rightCard { border:1px solid #e5e7eb; border-radius:14px; background:#fff; overflow:hidden; display:flex; flex-direction:column; }
.rightHeader { padding:10px 12px; font-weight:1000; background:#4f8f63; color:#fff; }
.bullets { padding:14px 18px; margin:0; }
.bullets li { margin:8px 0; line-height:1.6; }
.muted { padding:14px 18px; color:#6b7280; }

.actions { display:flex; justify-content:flex-end; gap:10px; padding: 0 12px 12px; margin-top:auto; }
.btnGhost { border:0; padding:10px 14px; border-radius:999px; font-weight:900; cursor:pointer; background:#6aa377; color:#fff; }
.btnDanger { border:2px solid #ef4444; padding:10px 14px; border-radius:999px; font-weight:900; cursor:pointer; background:#fff; color:#ef4444; }

.btnNext { border:0; padding:14px 12px; font-weight:1000; cursor:pointer; background:#0b5d8c; color:#fff; border-radius: 0 0 14px 14px; }

@media (max-width: 980px) {
  .grid { grid-template-columns:1fr; }
  .leftCard { min-height:300px; }
}
</style>
