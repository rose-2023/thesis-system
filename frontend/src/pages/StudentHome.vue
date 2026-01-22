<template>
  <div style="padding:24px;">
    <h2>學生首頁</h2>
    <p>請選擇單元開始學習</p>

    <div style="margin-top:16px;">
      <button @click="startUnit('U1')">單元一</button>
      <button @click="startUnit('U2')" style="margin-left:8px;">單元二</button>
    </div>
  </div>
</template>

<script setup>
function startUnit(unit) {
  alert("之後這裡會進入單元：" + unit);
}
</script>
