<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type SrpConfig } from '@/api'
import { useI18n } from '@/i18n'
import { useAlertDialog } from '@/composables/useAlertDialog'
import CustomSelect from '@/components/CustomSelect.vue'

const { t } = useI18n()
const { showAlert } = useAlertDialog()

const config = ref<SrpConfig | null>(null)
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const saveMsg = ref('')
const saveMsgOk = ref(true)

async function loadConfig() {
  loading.value = true
  loadError.value = ''
  try {
    config.value = await api.getConfig()
  } catch (e) {
    loadError.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (!config.value || saving.value) return
  saving.value = true
  saveMsg.value = ''
  try {
    await api.updateConfig(config.value)
    saveMsg.value = t('config.saved')
    saveMsgOk.value = true
  } catch (e) {
    saveMsg.value = t('config.saveFailed') + (e as Error).message
    saveMsgOk.value = false
    await showAlert(saveMsg.value)
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <div>
    <h2>{{ t('config.title') }}</h2>

    <p v-if="loading" class="loading">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">{{ t('common.loadFailed') }}{{ loadError }}</p>

    <template v-else-if="config">
      <div class="config-grid">
        <div class="form-group">
          <label>{{ t('config.regionId') }}</label>
          <input v-model.number="config.price_region_id" type="number" />
          <div style="font-size:.78rem;color:#5a5950;margin-top:4px">{{ t('config.regionHint') }}</div>
        </div>

        <div class="form-group">
          <label>{{ t('config.orderType') }}</label>
          <CustomSelect
            v-model="config.price_order_type"
            :options="[
              { value: 'buy',  label: t('config.orderTypeBuy') },
              { value: 'sell', label: t('config.orderTypeSell') },
            ]"
          />
        </div>

        <div class="form-group">
          <label>{{ t('config.coefficient') }}</label>
          <input v-model.number="config.coefficient" type="number" step="0.01" min="0" max="2" />
        </div>

        <div class="form-group">
          <label>{{ t('config.minLoss') }}</label>
          <input v-model.number="config.min_loss_value" type="number" step="1000000" min="0" />
        </div>

        <div class="form-group">
          <label>{{ t('config.sysStatus') }}</label>
          <CustomSelect
            v-model="config.enabled"
            :options="[
              { value: true,  label: t('config.enabled') },
              { value: false, label: t('config.disabled') },
            ]"
          />
        </div>
      </div>

      <button class="btn btn-primary" :disabled="saving" @click="onSave">
        {{ saving ? t('common.saving') : t('common.save') }}
      </button>
      <div v-if="saveMsg" style="margin-top:12px;font-size:.88rem" :style="{ color: saveMsgOk ? '#4caf50' : '#e06060' }">
        {{ saveMsg }}
      </div>
    </template>
  </div>
</template>
