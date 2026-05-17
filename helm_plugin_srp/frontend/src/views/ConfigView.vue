<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type SrpConfig } from '@/api'
import { useAlertDialog } from '@/composables/useAlertDialog'

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
    saveMsg.value = '✅ 配置已保存'
    saveMsgOk.value = true
  } catch (e) {
    saveMsg.value = '保存失败：' + (e as Error).message
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
    <h2>补损配置</h2>

    <p v-if="loading" class="loading">加载中…</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">加载失败：{{ loadError }}</p>

    <template v-else-if="config">
      <div class="config-grid">
        <div class="form-group">
          <label>价格星域 ID（Region ID）</label>
          <input v-model.number="config.price_region_id" type="number" />
          <div style="font-size:.78rem;color:#5a5950;margin-top:4px">10000002=Jita / 10000043=Amarr</div>
        </div>

        <div class="form-group">
          <label>订单类型</label>
          <select v-model="config.price_order_type">
            <option value="buy">买单价（Buy Order）</option>
            <option value="sell">卖单价（Sell Order）</option>
          </select>
        </div>

        <div class="form-group">
          <label>价值系数（0.0 ~ 2.0）</label>
          <input v-model.number="config.coefficient" type="number" step="0.01" min="0" max="2" />
        </div>

        <div class="form-group">
          <label>最低损失（ISK）</label>
          <input v-model.number="config.min_loss_value" type="number" step="1000000" min="0" />
        </div>

        <div class="form-group">
          <label>系统状态</label>
          <select v-model="config.enabled">
            <option :value="true">开启（接受申请）</option>
            <option :value="false">关闭（暂停受理）</option>
          </select>
        </div>
      </div>

      <button class="btn btn-primary" :disabled="saving" @click="onSave">
        {{ saving ? '⏳ 保存中…' : '保存配置' }}
      </button>
      <div v-if="saveMsg" style="margin-top:12px;font-size:.88rem" :style="{ color: saveMsgOk ? '#4caf50' : '#e06060' }">
        {{ saveMsg }}
      </div>
    </template>
  </div>
</template>
