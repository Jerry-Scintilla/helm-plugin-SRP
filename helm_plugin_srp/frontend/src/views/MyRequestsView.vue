<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type SrpRequest, type KillmailPreview, type Character } from '@/api'
import { useHelmSdk } from '@/composables/useHelmSdk'
import { useAlertDialog } from '@/composables/useAlertDialog'
import RequestTable from '@/components/RequestTable.vue'

const sdk = useHelmSdk()
const { showAlert } = useAlertDialog()

const requests = ref<SrpRequest[]>([])
const total = ref(0)
const loading = ref(false)
const loadError = ref('')

const showForm = ref(false)
const kmUrl = ref('')
const previewData = ref<KillmailPreview | null>(null)
const previewLoading = ref(false)
const submitLoading = ref(false)

const characters = ref<Character[]>([])
const selectedCharId = ref<number | null>(null)
const notes = ref('')

async function loadRequests() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.listRequests({ page_size: '50' })
    requests.value = data.items
    total.value = data.total
  } catch (e) {
    loadError.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function loadChars() {
  characters.value = await api.getCharacters()
  if (characters.value.length > 0 && !selectedCharId.value) {
    selectedCharId.value = characters.value[0].value
  }
}

function toggleForm() {
  showForm.value = !showForm.value
  if (!showForm.value) {
    kmUrl.value = ''
    previewData.value = null
    notes.value = ''
  } else {
    loadChars()
  }
}

async function onPreview() {
  if (!kmUrl.value.trim()) { await showAlert('请填写 ESI Killmail 链接'); return }
  if (previewLoading.value) return
  previewLoading.value = true
  previewData.value = null
  try {
    previewData.value = await api.previewKillmail(kmUrl.value.trim())
  } catch (e) {
    await showAlert('预览失败：' + (e as Error).message)
  } finally {
    previewLoading.value = false
  }
}

async function onSubmit() {
  if (!previewData.value || submitLoading.value) return
  if (!selectedCharId.value) { await showAlert('请选择角色'); return }
  submitLoading.value = true
  try {
    await api.submitRequest({
      zkb_url: previewData.value.zkb_url || kmUrl.value.trim(),
      character_id: selectedCharId.value,
      notes: notes.value || null,
    })
    showForm.value = false
    kmUrl.value = ''
    previewData.value = null
    notes.value = ''
    await loadRequests()
  } catch (e) {
    await showAlert('提交失败：' + (e as Error).message)
  } finally {
    submitLoading.value = false
  }
}

function isk(v: number): string {
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) + ' ISK'
}

onMounted(loadRequests)
</script>

<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>我的补损申请</h2>
      <button v-if="sdk.hasPerm('srp.submit')" class="btn btn-primary" @click="toggleForm">
        {{ showForm ? '× 收起表单' : '＋ 提交新申请' }}
      </button>
    </div>

    <!-- Submit form -->
    <div v-if="showForm" class="preview-card" style="margin-bottom:16px">
      <h3>提交补损申请</h3>
      <div class="form-group">
        <label>ESI Killmail 链接</label>
        <input
          v-model="kmUrl"
          type="text"
          placeholder="https://esi.evetech.net/killmails/123456789/abc123def…"
          @keyup.enter="onPreview"
        />
      </div>
      <div class="form-group">
        <label>使用角色</label>
        <select v-model="selectedCharId">
          <option v-for="c in characters" :key="c.value" :value="c.value">{{ c.label }}</option>
          <option v-if="characters.length === 0" :value="null" disabled>加载角色列表…</option>
        </select>
      </div>
      <div class="form-group">
        <label>备注（可选）</label>
        <textarea v-model="notes" placeholder="如：在 X 舰队活动期间损失"></textarea>
      </div>
      <button
        class="btn btn-secondary btn-sm"
        :disabled="previewLoading"
        @click="onPreview"
      >{{ previewLoading ? '⏳ 查询中…' : '预览补损金额' }}</button>
    </div>

    <!-- Preview result -->
    <div v-if="previewData" class="preview-card" style="margin-bottom:16px">
      <div style="font-size:.9rem;color:#7a796f;margin-bottom:8px">
        {{ previewData.ship_name }} · killmail #{{ previewData.killmail_id }}
      </div>
      <div class="amount">{{ isk(previewData.calculated_value) }}</div>
      <div class="meta">
        原始损失：{{ isk(previewData.loss_value_raw) }} ·
        价格来源：{{ previewData.price_source }} ·
        系数：{{ previewData.coefficient }}
      </div>
      <div v-if="previewData.eligible" style="margin-top:12px">
        <button
          class="btn btn-primary"
          :disabled="submitLoading"
          @click="onSubmit"
        >{{ submitLoading ? '⏳ 提交中…' : '确认提交' }}</button>
      </div>
      <div v-else class="ineligible" style="margin-top:8px">
        ⚠ 不符合补损资格：{{ previewData.ineligible_reason }}
      </div>
    </div>

    <!-- List -->
    <p v-if="loading" class="loading">加载中…</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">加载失败：{{ loadError }}</p>
    <p v-else-if="total === 0 && !showForm" class="empty">暂无申请记录</p>
    <RequestTable v-else-if="total > 0" :items="requests" />
  </div>
</template>
