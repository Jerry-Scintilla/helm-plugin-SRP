<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type SrpRequest, type KillmailPreview, type Character } from '@/api'
import { useHelmSdk } from '@/composables/useHelmSdk'
import { useAlertDialog } from '@/composables/useAlertDialog'
import { useI18n } from '@/i18n'
import RequestTable from '@/components/RequestTable.vue'
import KillmailDetailModal from '@/components/KillmailDetailModal.vue'
import CustomSelect, { type SelectOption } from '@/components/CustomSelect.vue'

const sdk = useHelmSdk()
const { showAlert } = useAlertDialog()
const { t, isk } = useI18n()

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

const charOptions = computed((): SelectOption[] =>
  characters.value.map(c => ({ value: c.value, label: c.label }))
)

const detailRequestId = ref<number | null>(null)

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
  if (!kmUrl.value.trim()) { await showAlert(t('myreq.noUrl')); return }
  if (previewLoading.value) return
  previewLoading.value = true
  previewData.value = null
  try {
    previewData.value = await api.previewKillmail(kmUrl.value.trim())
  } catch (e) {
    await showAlert(t('myreq.previewFailed') + (e as Error).message)
  } finally {
    previewLoading.value = false
  }
}

async function onSubmit() {
  if (!previewData.value || submitLoading.value) return
  if (!selectedCharId.value) { await showAlert(t('myreq.noChar')); return }
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
    await showAlert(t('myreq.submitFailed') + (e as Error).message)
  } finally {
    submitLoading.value = false
  }
}

onMounted(loadRequests)
</script>

<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>{{ t('myreq.title') }}</h2>
      <button v-if="sdk.hasPerm('srp.submit')" class="btn btn-primary" @click="toggleForm">
        {{ showForm ? t('myreq.hideForm') : t('myreq.newRequest') }}
      </button>
    </div>

    <!-- Submit form -->
    <div v-if="showForm" class="preview-card" style="margin-bottom:16px">
      <h3>{{ t('myreq.formTitle') }}</h3>
      <div class="form-group">
        <label>{{ t('myreq.esiUrl') }}</label>
        <input
          v-model="kmUrl"
          type="text"
          :placeholder="t('myreq.esiUrlPh')"
          @keyup.enter="onPreview"
        />
      </div>
      <div class="form-group">
        <label>{{ t('myreq.character') }}</label>
        <CustomSelect
          v-model="selectedCharId"
          :options="charOptions"
          :placeholder="charOptions.length === 0 ? t('myreq.charLoading') : t('myreq.charPlaceholder')"
        />
      </div>
      <div class="form-group">
        <label>{{ t('myreq.notes') }}</label>
        <textarea v-model="notes" :placeholder="t('myreq.notesPh')"></textarea>
      </div>
      <button
        class="btn btn-secondary btn-sm"
        :disabled="previewLoading"
        @click="onPreview"
      >{{ previewLoading ? t('myreq.previewing') : t('myreq.preview') }}</button>
    </div>

    <!-- Preview result -->
    <div v-if="previewData" class="preview-card" style="margin-bottom:16px">
      <!-- 舰船信息头 -->
      <div class="detail-ship-header">
        <div class="ship-icon-wrap">
          <img
            v-if="previewData.ship_icon_url"
            :src="previewData.ship_icon_url"
            class="ship-icon"
            @error="(e) => ((e.target as HTMLImageElement).style.visibility = 'hidden')"
          />
        </div>
        <div>
          <div class="ship-name">{{ previewData.ship_name }}</div>
          <div class="km-meta">killmail #{{ previewData.killmail_id }}</div>
        </div>
      </div>

      <div class="amount">{{ isk(previewData.calculated_value) }}</div>
      <div class="meta">
        {{ t('myreq.lossRaw') }}{{ isk(previewData.loss_value_raw) }} ·
        {{ t('myreq.priceSource') }}{{ previewData.price_source }} ·
        {{ t('myreq.coefficient') }}{{ previewData.coefficient }}
      </div>

      <!-- 物品列表 -->
      <div v-if="previewData.items.length" class="items-section">
        <div class="items-header">{{ t('myreq.items', { n: previewData.items.length }) }}</div>
        <div v-for="item in previewData.items" :key="item.type_id" class="item-row">
          <div class="item-icon-wrap">
            <img
              v-if="item.icon_url"
              :src="item.icon_url"
              class="item-icon"
              @error="(e) => ((e.target as HTMLImageElement).style.visibility = 'hidden')"
            />
          </div>
          <span class="item-name">{{ item.name }}</span>
          <span class="item-qty">
            <span v-if="item.qty_destroyed">{{ t('myreq.destroyed', { n: item.qty_destroyed }) }}</span>
            <span v-if="item.qty_dropped" class="dropped"> {{ t('myreq.dropped', { n: item.qty_dropped }) }}</span>
          </span>
        </div>
      </div>

      <div v-if="previewData.eligible" style="margin-top:12px">
        <button
          class="btn btn-primary"
          :disabled="submitLoading"
          @click="onSubmit"
        >{{ submitLoading ? t('myreq.submitting') : t('myreq.submit') }}</button>
      </div>
      <div v-else class="ineligible" style="margin-top:8px">
        {{ t('myreq.ineligible') }}{{ previewData.ineligible_reason }}
      </div>
    </div>

    <!-- List -->
    <p v-if="loading" class="loading">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">{{ t('common.loadFailed') }}{{ loadError }}</p>
    <p v-else-if="total === 0 && !showForm" class="empty">{{ t('myreq.noRequests') }}</p>
    <RequestTable
      v-else-if="total > 0"
      :items="requests"
      show-detail
      @view-detail="detailRequestId = $event"
    />

    <KillmailDetailModal
      :visible="detailRequestId !== null"
      :request-id="detailRequestId"
      @close="detailRequestId = null"
    />
  </div>
</template>
