<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type SrpRequest } from '@/api'
import { useI18n } from '@/i18n'
import { useAlertDialog } from '@/composables/useAlertDialog'
import RequestTable from '@/components/RequestTable.vue'
import RejectDialog from '@/components/RejectDialog.vue'
import KillmailDetailModal from '@/components/KillmailDetailModal.vue'

const { t } = useI18n()
const { showAlert } = useAlertDialog()

const requests = ref<SrpRequest[]>([])
const total = ref(0)
const loading = ref(false)
const loadError = ref('')
const actionLoading = ref(false)

const statusFilter = ref('pending')
const rejectDialogVisible = ref(false)
const pendingRejectId = ref<number | null>(null)
const detailRequestId = ref<number | null>(null)

const STATUS_OPTIONS = [
  { value: '',         key: 'status.all' as const },
  { value: 'pending',  key: 'status.pending' as const },
  { value: 'approved', key: 'status.approved' as const },
  { value: 'rejected', key: 'status.rejected' as const },
  { value: 'paid',     key: 'status.paid' as const },
]

async function loadRequests() {
  loading.value = true
  loadError.value = ''
  try {
    const params: Record<string, string> = { page_size: '100' }
    if (statusFilter.value) params.status = statusFilter.value
    const data = await api.listRequests(params)
    requests.value = data.items
    total.value = data.total
  } catch (e) {
    loadError.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function onFilterChange(v: string) {
  statusFilter.value = v
  await loadRequests()
}

async function onApprove(id: number) {
  if (actionLoading.value) return
  actionLoading.value = true
  try {
    await api.approveRequest(id)
    await loadRequests()
  } catch (e) {
    await showAlert(t('common.opFailed') + (e as Error).message)
  } finally {
    actionLoading.value = false
  }
}

function onRejectOpen(id: number) {
  pendingRejectId.value = id
  rejectDialogVisible.value = true
}

async function onRejectConfirm(notes: string) {
  rejectDialogVisible.value = false
  if (!pendingRejectId.value || actionLoading.value) return
  actionLoading.value = true
  try {
    await api.rejectRequest(pendingRejectId.value, notes || null)
    pendingRejectId.value = null
    await loadRequests()
  } catch (e) {
    await showAlert(t('common.opFailed') + (e as Error).message)
  } finally {
    actionLoading.value = false
  }
}

async function onMarkPaid(id: number) {
  if (actionLoading.value) return
  actionLoading.value = true
  try {
    await api.markPaid(id)
    await loadRequests()
  } catch (e) {
    await showAlert(t('common.opFailed') + (e as Error).message)
  } finally {
    actionLoading.value = false
  }
}

onMounted(loadRequests)
</script>

<template>
  <div>
    <h2>{{ t('manage.title') }}</h2>

    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          v-for="o in STATUS_OPTIONS"
          :key="o.value"
          class="filter-tab"
          :class="{ active: statusFilter === o.value }"
          @click="onFilterChange(o.value)"
        >{{ t(o.key) }}</button>
      </div>
      <span style="font-size:.82rem;color:#5a5950;margin-left:4px">{{ t('manage.total', { n: total }) }}</span>
      <button class="btn btn-secondary btn-sm" style="margin-left:auto" @click="loadRequests">{{ t('common.refresh') }}</button>
    </div>

    <p v-if="loading" class="loading">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">{{ t('common.loadFailed') }}{{ loadError }}</p>
    <p v-else-if="total === 0" class="empty">
      {{ statusFilter === 'pending' ? t('manage.noPending') : t('manage.noMatch') }}
    </p>
    <RequestTable
      v-else
      :items="requests"
      show-char-col
      show-actions
      show-detail
      @approve="onApprove"
      @reject="onRejectOpen"
      @mark-paid="onMarkPaid"
      @view-detail="detailRequestId = $event"
    />

    <RejectDialog
      :visible="rejectDialogVisible"
      @confirm="onRejectConfirm"
      @cancel="rejectDialogVisible = false"
    />

    <KillmailDetailModal
      :visible="detailRequestId !== null"
      :request-id="detailRequestId"
      @close="detailRequestId = null"
    />
  </div>
</template>
