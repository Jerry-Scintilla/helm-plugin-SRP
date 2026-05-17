<script setup lang="ts">
import type { SrpStatus } from '@/api'
import { useI18n } from '@/i18n'
defineProps<{ status: SrpStatus }>()
const { t } = useI18n()
</script>

<template>
  <span class="badge" :class="`badge-${status}`">{{
    status === 'pending'  ? t('status.pending')  :
    status === 'approved' ? t('status.approved') :
    status === 'rejected' ? t('status.rejected') :
                            t('status.paid')
  }}</span>
</template>
