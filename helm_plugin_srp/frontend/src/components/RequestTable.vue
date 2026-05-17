<script setup lang="ts">
import type { SrpRequest } from '@/api'
import StatusBadge from './StatusBadge.vue'

defineProps<{
  items: SrpRequest[]
  showCharCol?: boolean
  showActions?: boolean
  showDetail?: boolean
}>()
const emit = defineEmits<{
  approve: [id: number]
  reject: [id: number]
  markPaid: [id: number]
  viewDetail: [id: number]
}>()

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}
function isk(v: number): string {
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) + ' ISK'
}
</script>

<template>
  <table>
    <thead>
      <tr>
        <th v-if="showCharCol">角色</th>
        <th>舰船</th>
        <th>损失</th>
        <th>补损金额</th>
        <th>状态</th>
        <th>提交时间</th>
        <th v-if="showActions || showDetail">操作</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="r in items" :key="r.id">
        <td v-if="showCharCol">{{ r.character_name }}</td>
        <td>{{ r.ship_name }}</td>
        <td class="isk">{{ isk(r.loss_value_raw) }}</td>
        <td class="isk"><strong>{{ isk(r.calculated_value) }}</strong></td>
        <td><StatusBadge :status="r.status" /></td>
        <td>{{ fmtDate(r.created_at) }}</td>
        <td v-if="showActions || showDetail">
          <div class="action-row">
            <template v-if="showActions">
              <template v-if="r.status === 'pending'">
                <button class="btn btn-success btn-sm" @click="emit('approve', r.id)">批准</button>
                <button class="btn btn-danger btn-sm" @click="emit('reject', r.id)">拒绝</button>
              </template>
              <template v-else-if="r.status === 'approved'">
                <button class="btn btn-primary btn-sm" @click="emit('markPaid', r.id)">标记已付款</button>
              </template>
            </template>
            <button
              v-if="showDetail"
              class="btn btn-secondary btn-sm"
              @click="emit('viewDetail', r.id)"
            >详情</button>
            <template v-if="showActions && r.status !== 'pending' && r.status !== 'approved'">
              <span style="color:#5a5950;font-size:.8rem">—</span>
            </template>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
