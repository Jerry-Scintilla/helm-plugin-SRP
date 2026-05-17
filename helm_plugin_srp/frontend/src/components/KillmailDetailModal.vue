<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type SrpRequestDetail } from '@/api'
import { useI18n } from '@/i18n'

const props = defineProps<{ visible: boolean; requestId: number | null }>()
const emit = defineEmits<{ close: [] }>()
const { t, isk } = useI18n()

const detail = ref<SrpRequestDetail | null>(null)
const loading = ref(false)
const error = ref('')

watch(() => props.requestId, async (id) => {
  if (!id) { detail.value = null; return }
  loading.value = true
  error.value = ''
  detail.value = null
  try {
    detail.value = await api.getRequestDetail(id)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}, { immediate: true })

function onImgError(e: Event) {
  ;(e.target as HTMLImageElement).style.visibility = 'hidden'
}

const zkbUrl = (d: SrpRequestDetail) =>
  `https://zkillboard.com/kill/${d.killmail_id}/`
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="emit('close')">
      <div class="dialog-box detail-modal">
        <div class="dialog-header">
          <span>{{ t('detail.title') }}</span>
          <button class="btn-close" @click="emit('close')">×</button>
        </div>

        <div class="dialog-body">
          <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
          <div v-else-if="error" style="color:#e06060">{{ t('detail.loadFailed') }}{{ error }}</div>

          <template v-else-if="detail">
            <!-- 舰船信息头 -->
            <div class="detail-ship-header">
              <div class="ship-icon-wrap">
                <img
                  v-if="detail.ship_icon_url"
                  :src="detail.ship_icon_url"
                  class="ship-icon"
                  @error="onImgError"
                />
              </div>
              <div>
                <div class="ship-name">{{ detail.ship_name }}</div>
                <div class="km-meta">
                  {{ detail.character_name }} ·
                  <a :href="zkbUrl(detail)" target="_blank" rel="noopener" class="zkb-link">
                    killmail #{{ detail.killmail_id }}
                  </a>
                </div>
              </div>
            </div>

            <!-- 补损金额 -->
            <div class="detail-section">
              <div class="detail-row">
                <span class="detail-label">{{ t('detail.srpAmount') }}</span>
                <span class="isk detail-value-main">{{ isk(detail.calculated_value) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('detail.lossRaw') }}</span>
                <span class="isk">{{ isk(detail.loss_value_raw) }}</span>
              </div>
              <div class="detail-row" v-if="detail.notes">
                <span class="detail-label">{{ t('detail.notes') }}</span>
                <span>{{ detail.notes }}</span>
              </div>
              <div class="detail-row" v-if="detail.officer_notes">
                <span class="detail-label">{{ t('detail.officerNotes') }}</span>
                <span>{{ detail.officer_notes }}</span>
              </div>
            </div>

            <!-- 损毁物品 -->
            <div v-if="detail.items.length" class="items-section">
              <div class="items-header">{{ t('detail.items', { n: detail.items.length }) }}</div>
              <div
                v-for="item in detail.items"
                :key="item.type_id"
                class="item-row"
              >
                <div class="item-icon-wrap">
                  <img
                    v-if="item.icon_url"
                    :src="item.icon_url"
                    class="item-icon"
                    @error="onImgError"
                  />
                </div>
                <span class="item-name">{{ item.name }}</span>
                <span class="item-qty">
                  <span v-if="item.qty_destroyed">{{ t('detail.destroyed', { n: item.qty_destroyed }) }}</span>
                  <span v-if="item.qty_dropped" class="dropped"> {{ t('detail.dropped', { n: item.qty_dropped }) }}</span>
                </span>
              </div>
            </div>
            <div v-else class="items-section">
              <div class="items-header">{{ t('detail.itemsHeader') }}</div>
              <p style="color:#5a5950;font-size:.85rem;margin:4px 0">{{ t('detail.noItems') }}</p>
            </div>
          </template>
        </div>

        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="emit('close')">{{ t('common.close') }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
