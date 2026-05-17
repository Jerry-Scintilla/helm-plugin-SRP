<script setup lang="ts">
import type { SrpStatus } from '@/api'
defineProps<{ status: SrpStatus }>()
const labels: Record<SrpStatus, string> = {
  pending:  '⏳ 待审核',
  approved: '✅ 已批准',
  rejected: '❌ 已拒绝',
  paid:     '💰 已付款',
}
</script>

<template>
  <span class="badge" :class="`badge-${status}`">{{ labels[status] }}</span>
</template>
