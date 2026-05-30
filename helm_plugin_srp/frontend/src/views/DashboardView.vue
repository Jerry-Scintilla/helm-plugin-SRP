<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { CHART, TOOLTIP_STYLE } from '@/charts/echarts'
import { api, type DashboardResponse, type DashboardPeriod } from '@/api'
import { useI18n } from '@/i18n'

const { t, fmtDate, isk } = useI18n()

const data = ref<DashboardResponse | null>(null)
const loading = ref(false)
const loadError = ref('')
const period = ref<DashboardPeriod>('month')

const PERIODS: { value: DashboardPeriod; key: 'dash.period.week' | 'dash.period.month' | 'dash.period.quarter' | 'dash.period.year' }[] = [
  { value: 'week',    key: 'dash.period.week' },
  { value: 'month',   key: 'dash.period.month' },
  { value: 'quarter', key: 'dash.period.quarter' },
  { value: 'year',    key: 'dash.period.year' },
]

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    data.value = await api.getDashboard(period.value)
  } catch (e) {
    loadError.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function onPeriodChange(p: DashboardPeriod) {
  if (p === period.value) return
  period.value = p
  await load()
}

/** 紧凑 ISK 格式：1.2B / 340M / 12K */
function iskShort(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 1e12) return (v / 1e12).toFixed(2) + 'T'
  if (abs >= 1e9)  return (v / 1e9).toFixed(2) + 'B'
  if (abs >= 1e6)  return (v / 1e6).toFixed(2) + 'M'
  if (abs >= 1e3)  return (v / 1e3).toFixed(1) + 'K'
  return v.toFixed(0)
}

const summary = computed(() => data.value?.summary ?? null)
const isEmpty = computed(() => !!summary.value && summary.value.total_requests === 0)

const amountLabel = computed(() => t('dash.col.amount'))
const countLabel = computed(() => t('dash.col.count'))

// ── 趋势：金额(柱) + 数量(线) 双轴组合 ────────────────────────────────────────
const trendOption = computed(() => {
  const pts = data.value?.trend ?? []
  return {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_STYLE,
      axisPointer: { type: 'cross', crossStyle: { color: CHART.textDim }, lineStyle: { color: CHART.textDim } },
      formatter: (params: any[]) => {
        const name = params[0]?.axisValue ?? ''
        let s = `<div style="font-size:11px;color:${CHART.textMuted};margin-bottom:2px">${name}</div>`
        for (const p of params) {
          const val = p.seriesName === amountLabel.value ? isk(p.value) : p.value
          s += `<div>${p.marker}${p.seriesName}：<b style="color:${CHART.textBody}">${val}</b></div>`
        }
        return s
      },
    },
    legend: { data: [amountLabel.value, countLabel.value], textStyle: { color: CHART.textMuted }, top: 0, icon: 'roundRect' },
    grid: { left: 8, right: 8, bottom: 6, top: 38, containLabel: true },
    xAxis: {
      type: 'category',
      data: pts.map(p => p.bucket),
      axisLabel: { color: CHART.textDim, fontSize: 10 },
      axisLine: { lineStyle: { color: CHART.border } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        axisLabel: { color: CHART.textDim, fontSize: 10, formatter: (v: number) => iskShort(v) },
        splitLine: { lineStyle: { color: CHART.border, opacity: 0.4 } },
      },
      {
        type: 'value',
        axisLabel: { color: CHART.textDim, fontSize: 10 },
        splitLine: { show: false },
        minInterval: 1,
      },
    ],
    series: [
      {
        name: amountLabel.value,
        type: 'bar',
        yAxisIndex: 0,
        data: pts.map(p => p.total_amount),
        barMaxWidth: 40,
        itemStyle: {
          borderRadius: [3, 3, 0, 0],
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: CHART.brandLight }, { offset: 1, color: CHART.brand }] },
        },
      },
      {
        name: countLabel.value,
        type: 'line',
        yAxisIndex: 1,
        data: pts.map(p => p.count),
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: CHART.textBody },
        lineStyle: { color: CHART.textBody, width: 2 },
      },
    ],
  }
})

// ── 状态分布：环形图 ─────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  pending: CHART.textMuted,
  approved: CHART.brand,
  paid: '#6a9a78',
  rejected: CHART.error,
}
const statusOption = computed(() => {
  const s = summary.value
  if (!s) return {}
  const rows = [
    { key: 'pending',  name: t('status.pending'),  value: s.pending_count },
    { key: 'approved', name: t('status.approved'), value: s.approved_count },
    { key: 'paid',     name: t('status.paid'),     value: s.paid_count },
    { key: 'rejected', name: t('status.rejected'), value: s.rejected_count },
  ]
  return {
    tooltip: { trigger: 'item', ...TOOLTIP_STYLE, formatter: '{b}：{c} ({d}%)' },
    legend: { orient: 'vertical', right: '4%', top: 'center', textStyle: { color: CHART.textMuted, fontSize: 12 } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['34%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: CHART.bg, borderWidth: 2 },
        label: { show: true, color: CHART.textBody, fontSize: 11, formatter: '{c}' },
        labelLine: { lineStyle: { color: CHART.textDim }, length: 8, length2: 8 },
        data: rows.map(r => ({ name: r.name, value: r.value, itemStyle: { color: STATUS_COLORS[r.key] } })),
      },
    ],
  }
})

// ── 横向条形排行通用构造 ───────────────────────────────────────────────────────
function rankBarOption(
  items: { name: string; count: number; amount: number }[],
  barColor: string,
) {
  // echarts 类目轴自下而上，反转使第 1 名显示在顶部
  const rev = [...items].reverse()
  return {
    tooltip: {
      trigger: 'axis',
      ...TOOLTIP_STYLE,
      axisPointer: { type: 'shadow' },
      formatter: (params: any[]) => {
        const p = params[0]
        const it = rev[p.dataIndex]
        return `<div style="font-size:11px;color:${CHART.textMuted};margin-bottom:2px">${p.name}</div>`
          + `<div>${amountLabel.value}：<b style="color:${CHART.textBody}">${isk(it.amount)}</b></div>`
          + `<div>${countLabel.value}：<b style="color:${CHART.textBody}">${it.count}</b></div>`
      },
    },
    grid: { left: 8, right: 56, bottom: 6, top: 8, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { color: CHART.textDim, fontSize: 10, formatter: (v: number) => iskShort(v) },
      splitLine: { lineStyle: { color: CHART.border, opacity: 0.4 } },
    },
    yAxis: {
      type: 'category',
      data: rev.map(i => i.name),
      axisLabel: { color: CHART.textBody, fontSize: 11 },
      axisLine: { lineStyle: { color: CHART.border } },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: rev.map(i => i.amount),
        barMaxWidth: 18,
        itemStyle: { color: barColor, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: CHART.textMuted, fontSize: 10, formatter: (p: any) => iskShort(p.value) },
      },
    ],
  }
}

const shipsOption = computed(() =>
  rankBarOption(
    (data.value?.ships ?? []).map(s => ({ name: s.ship_name, count: s.count, amount: s.total_amount })),
    CHART.brand,
  ),
)
const charsOption = computed(() =>
  rankBarOption(
    (data.value?.characters ?? []).map(c => ({ name: c.character_name, count: c.count, amount: c.total_amount })),
    CHART.brandLight,
  ),
)

// 横向条形图高度随条数自适应
function rankHeight(n: number): string {
  return Math.max(160, n * 30 + 30) + 'px'
}

onMounted(load)
</script>

<template>
  <div>
    <h2>{{ t('dash.title') }}</h2>

    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          v-for="p in PERIODS"
          :key="p.value"
          class="filter-tab"
          :class="{ active: period === p.value }"
          @click="onPeriodChange(p.value)"
        >{{ t(p.key) }}</button>
      </div>
      <span v-if="summary" style="font-size:.8rem;color:var(--text-muted);margin-left:4px">
        {{ t('dash.window') }}{{ fmtDate(summary.window_start) }} → {{ fmtDate(summary.window_end) }}
      </span>
      <button class="btn btn-secondary btn-sm" style="margin-left:auto" @click="load">{{ t('common.refresh') }}</button>
    </div>

    <p v-if="loading" class="loading">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="empty" style="color:var(--error-text)">{{ t('common.loadFailed') }}{{ loadError }}</p>

    <template v-else-if="summary">
      <!-- 汇总卡片 -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('dash.card.totalRequests') }}</div>
          <div class="stat-value">{{ summary.total_requests }}<span class="stat-unit">{{ t('dash.card.requestsUnit') }}</span></div>
        </div>
        <div class="stat-card accent">
          <div class="stat-label">{{ t('dash.card.totalAmount') }}</div>
          <div class="stat-value isk">{{ iskShort(summary.total_srp_amount) }}</div>
          <div class="stat-sub">{{ isk(summary.total_srp_amount) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('dash.card.paidAmount') }}</div>
          <div class="stat-value isk">{{ iskShort(summary.paid_amount) }}</div>
          <div class="stat-sub">{{ isk(summary.paid_amount) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('dash.card.approvedAmount') }}</div>
          <div class="stat-value isk">{{ iskShort(summary.approved_amount) }}</div>
          <div class="stat-sub">{{ isk(summary.approved_amount) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('dash.card.totalLoss') }}</div>
          <div class="stat-value isk">{{ iskShort(summary.total_loss_raw) }}</div>
          <div class="stat-sub">{{ isk(summary.total_loss_raw) }}</div>
        </div>
      </div>

      <p v-if="isEmpty" class="empty">{{ t('dash.empty') }}</p>

      <template v-else>
        <!-- 趋势 -->
        <div class="chart-card">
          <h3>{{ t('dash.trend.title') }}</h3>
          <VChart class="echart" :option="trendOption" autoresize style="height:300px" />
        </div>

        <!-- 状态分布 + 舰船排行 -->
        <div class="chart-grid">
          <div class="chart-card">
            <h3>{{ t('dash.statusBreakdown') }}</h3>
            <VChart class="echart" :option="statusOption" autoresize style="height:280px" />
          </div>
          <div class="chart-card">
            <h3>{{ t('dash.ships.title', { n: data!.ships.length }) }}</h3>
            <p v-if="data!.ships.length === 0" class="empty">{{ t('dash.noShips') }}</p>
            <VChart v-else class="echart" :option="shipsOption" autoresize :style="{ height: rankHeight(data!.ships.length) }" />
          </div>
        </div>

        <!-- 角色排行 -->
        <div class="chart-card">
          <h3>{{ t('dash.chars.title', { n: data!.characters.length }) }}</h3>
          <p v-if="data!.characters.length === 0" class="empty">{{ t('dash.noChars') }}</p>
          <VChart v-else class="echart" :option="charsOption" autoresize :style="{ height: rankHeight(data!.characters.length) }" />
        </div>
      </template>
    </template>
  </div>
</template>
