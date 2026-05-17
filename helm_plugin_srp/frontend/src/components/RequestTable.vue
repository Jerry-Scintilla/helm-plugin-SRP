<script setup lang="ts">
import type { SrpRequest } from '@/api'
import { useI18n } from '@/i18n'
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

const { t, fmtDate, isk } = useI18n()
</script>

<template>
  <table>
    <thead>
      <tr>
        <th v-if="showCharCol">{{ t('table.character') }}</th>
        <th>{{ t('table.ship') }}</th>
        <th>{{ t('table.loss') }}</th>
        <th>{{ t('table.srpAmount') }}</th>
        <th>{{ t('table.status') }}</th>
        <th>{{ t('table.submitTime') }}</th>
        <th v-if="showActions || showDetail">{{ t('table.actions') }}</th>
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
                <button class="btn btn-success btn-sm" @click="emit('approve', r.id)">{{ t('table.approve') }}</button>
                <button class="btn btn-danger btn-sm" @click="emit('reject', r.id)">{{ t('table.reject') }}</button>
              </template>
              <template v-else-if="r.status === 'approved'">
                <button class="btn btn-primary btn-sm" @click="emit('markPaid', r.id)">{{ t('table.markPaid') }}</button>
              </template>
            </template>
            <button
              v-if="showDetail"
              class="btn btn-secondary btn-sm"
              @click="emit('viewDetail', r.id)"
            >{{ t('table.detail') }}</button>
            <template v-if="showActions && r.status !== 'pending' && r.status !== 'approved'">
              <span style="color:#5a5950;font-size:.8rem">—</span>
            </template>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
