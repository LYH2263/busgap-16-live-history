<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

const currentEvents = ref<any[]>([])
const history = ref<any[]>([])
const loading = ref(false)

// 异常判定只认后端 classify_gap 返回的 status（现网边界规则：间隔等于阈值判正常），
// 前端不自行用 gap_min 与阈值比较，保证当前栏与历史栏不各算各的。
const isAbnormal = (e: any) => e.status !== 'normal'

async function loadCurrent() {
  const data = await api('/reports/current?line_id=1')
  currentEvents.value = (data.events || []).filter(isAbnormal)
}
async function loadHistory() {
  history.value = await api('/reports')
}
async function run() {
  loading.value = true
  try {
    await api('/reports/run?line_id=1', { method: 'POST' })
    await Promise.all([loadCurrent(), loadHistory()])
  } finally { loading.value = false }
}
onMounted(async () => { await Promise.all([loadCurrent(), loadHistory()]) })

function label(s: string) {
  return s === 'bunching' ? '串车' : s === 'large_gap' ? '大间隔' : '正常'
}
function badgeClass(s: string) {
  return s === 'bunching' ? 'badge-bad' : s === 'large_gap' ? 'badge-warn' : 'badge-ok'
}
function fmtTime(iso: string) {
  return (iso || '').replace('T', ' ').slice(5, 16)
}
function abnormalEvents(r: any) {
  return (r.events || []).filter(isAbnormal)
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">当前栏按当前班次与到站即时算出（班次号可在顶部时间轴找到对应点）；历史栏为过去检测存档，不参与当前时间轴画点</p>
  <button class="btn" :disabled="loading" @click="run">重新检测</button>
  <div class="bg-split bg-split-reports" style="margin-top:1rem">
    <aside class="bg-trip-col">
      <h2>当前间隔异常</h2>
      <div v-if="!currentEvents.length" class="bg-empty">当前无串车 / 大间隔异常</div>
      <div v-for="(e, i) in currentEvents" :key="i" class="bg-trip-row">
        <div>
          <div>{{ e.stop_name }} · {{ e.gap_min }}′ <span class="bg-trip-meta">/ 计划 {{ e.planned_headway_min }}′</span></div>
          <div class="bg-trip-meta">{{ e.earlier_trip }} → {{ e.later_trip }}</div>
        </div>
        <span class="badge" :class="badgeClass(e.status)">{{ label(e.status) }}</span>
      </div>
    </aside>
    <aside class="bg-trip-col">
      <h2>历史检测报告 <span class="bg-hist-note">仅存档 · 不参与当前时间轴画点</span></h2>
      <div v-if="!history.length" class="bg-empty">暂无历史检测记录</div>
      <div v-for="r in history" :key="r.id" class="bg-history-report">
        <div class="bg-history-head">
          <span>#{{ r.id }} · {{ fmtTime(r.created_at) }}</span>
          <span class="bg-trip-meta">站点 {{ r.stop_name }} · 异常 {{ abnormalEvents(r).length }}/{{ r.events.length }}</span>
        </div>
        <div v-if="!abnormalEvents(r).length" class="bg-empty">该次检测无异常</div>
        <div v-for="(e, i) in abnormalEvents(r)" :key="i" class="bg-trip-row">
          <div>
            <div>{{ e.stop_name }} · {{ e.gap_min }}′ <span class="bg-trip-meta">/ 计划 {{ e.planned_headway_min }}′</span></div>
            <div class="bg-trip-meta">{{ e.earlier_trip }} → {{ e.later_trip }}</div>
          </div>
          <span class="badge" :class="badgeClass(e.status)">{{ label(e.status) }}</span>
        </div>
      </div>
    </aside>
  </div>
</template>
