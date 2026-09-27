<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

interface GapEvent {
  stop_name: string
  earlier_trip: string
  later_trip: string
  gap_min: number
  planned_headway_min: number
  status: string
  suggestion: string
}
interface ReportRow {
  id: number
  line_id: number
  stop_name: string
  created_at: string
  events: GapEvent[]
}

const liveEvents = ref<GapEvent[]>([])
const reports = ref<ReportRow[]>([])
const loading = ref(false)

// 当前栏只展示当前异常，没有当前异常时为空。
// 间隔恰好等于阈值时由后端引擎统一判为正常（现网边界规则），前端不另设口径。
const currentEvents = computed(() => liveEvents.value.filter(e => e.status !== 'normal'))

async function loadLive() {
  liveEvents.value = (await api('/reports/live?line_id=1')).events || []
}
async function loadReports() {
  reports.value = await api('/reports')
}
async function run() {
  loading.value = true
  try {
    await api('/reports/run?line_id=1', { method: 'POST' })
    await Promise.all([loadLive(), loadReports()])
  } finally { loading.value = false }
}
onMounted(() => {
  loadLive()
  loadReports()
})

function stripClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function label(s: string) {
  return s === 'bunching' ? '串车' : s === 'large_gap' ? '大间隔' : '正常'
}
function fmtTime(iso: string) {
  return iso.replace('T', ' ').slice(0, 16)
}
function abnormalOf(r: ReportRow) {
  return r.events.filter(e => e.status !== 'normal')
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">左栏按当前班次与到站即时算出 · 右栏为历史检测存档，不参与当前时间轴画点</p>
  <button class="btn" :disabled="loading" @click="run">重新检测并存档</button>
  <div class="bg-split bg-split-even" style="margin-top:1rem">
    <section>
      <h2 class="bg-col-title">当前间隔事件</h2>
      <p class="sub">每条异常对应的班次点均可在时间轴对应站点找到</p>
      <div v-if="currentEvents.length" class="bg-strip-col">
        <article
          v-for="(e, i) in currentEvents"
          :key="i"
          class="bg-gap-strip"
          :class="stripClass(e.status)"
        >
          <header>{{ e.stop_name }}</header>
          <div class="bg-gap-body">
            <div class="bg-gap-val">{{ e.gap_min }}′</div>
            <div>计划 {{ e.planned_headway_min }}′</div>
            <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
            <span class="badge" :class="e.status === 'bunching' ? 'badge-bad' : 'badge-warn'">
              {{ label(e.status) }}
            </span>
          </div>
        </article>
      </div>
      <p v-else class="bg-empty">当前无串车或大间隔异常</p>
    </section>
    <aside class="bg-trip-col">
      <h2>历史检测报告</h2>
      <p v-if="!reports.length" class="bg-empty">暂无历史检测记录</p>
      <div v-for="r in reports" :key="r.id" class="bg-report-row">
        <div class="bg-report-head">
          <span>#{{ r.id }} · {{ r.stop_name === '*' ? '全部站点' : r.stop_name }}</span>
          <span class="bg-trip-meta">{{ fmtTime(r.created_at) }}</span>
        </div>
        <div class="bg-report-events">
          <span v-if="!abnormalOf(r).length">无异常事件</span>
          <span v-for="(e, i) in abnormalOf(r)" :key="i">
            {{ e.stop_name }} · {{ e.earlier_trip }} → {{ e.later_trip }} · {{ e.gap_min }}′ · {{ label(e.status) }}
          </span>
        </div>
      </div>
    </aside>
  </div>
</template>
