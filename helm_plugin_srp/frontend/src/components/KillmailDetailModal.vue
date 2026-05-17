<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type SrpRequestDetail } from '@/api'

const props = defineProps<{ visible: boolean; requestId: number | null }>()
const emit = defineEmits<{ close: [] }>()

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

function isk(v: number): string {
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) + ' ISK'
}

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
          <span>击杀详情</span>
          <button class="btn-close" @click="emit('close')">×</button>
        </div>

        <div class="dialog-body">
          <div v-if="loading" class="loading">加载中…</div>
          <div v-else-if="error" style="color:#e06060">加载失败：{{ error }}</div>

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
                <span class="detail-label">补损金额</span>
                <span class="isk detail-value-main">{{ isk(detail.calculated_value) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">原始损失</span>
                <span class="isk">{{ isk(detail.loss_value_raw) }}</span>
              </div>
              <div class="detail-row" v-if="detail.notes">
                <span class="detail-label">备注</span>
                <span>{{ detail.notes }}</span>
              </div>
              <div class="detail-row" v-if="detail.officer_notes">
                <span class="detail-label">审核备注</span>
                <span>{{ detail.officer_notes }}</span>
              </div>
            </div>

            <!-- 损毁物品 -->
            <div v-if="detail.items.length" class="items-section">
              <div class="items-header">损毁物品 ({{ detail.items.length }})</div>
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
                  <span v-if="item.qty_destroyed">×{{ item.qty_destroyed }} 损毁</span>
                  <span v-if="item.qty_dropped" class="dropped"> ×{{ item.qty_dropped }} 掉落</span>
                </span>
              </div>
            </div>
            <div v-else class="items-section">
              <div class="items-header">损毁物品</div>
              <p style="color:#5a5950;font-size:.85rem;margin:4px 0">暂无物品数据</p>
            </div>
          </template>
        </div>

        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="emit('close')">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
