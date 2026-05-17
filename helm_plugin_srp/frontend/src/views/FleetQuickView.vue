<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type FleetKillItem, type FleetKillsResponse, type Character } from '@/api'
import { useHelmSdk } from '@/composables/useHelmSdk'
import { useAlertDialog } from '@/composables/useAlertDialog'
import CharSelectDialog from '@/components/CharSelectDialog.vue'

const sdk = useHelmSdk()
const { showAlert } = useAlertDialog()

const fleetInfo = ref<Omit<FleetKillsResponse, 'items'> | null>(null)
const kills = ref<FleetKillItem[]>([])
const loading = ref(false)
const loadError = ref('')
const selectedIndices = ref(new Set<number>())
const batchLoading = ref(false)
const submitMsg = ref('')
const submitMsgOk = ref(true)

const characters = ref<Character[]>([])
const charDialogVisible = ref(false)

const submittable = computed(() =>
  kills.value.filter(k => !k.already_submitted)
)

async function loadKills() {
  if (!sdk.fleetActionId.value) return
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.getFleetKills(sdk.fleetActionId.value)
    fleetInfo.value = { fleet_action_id: data.fleet_action_id, fleet_action_name: data.fleet_action_name, window_start: data.window_start, window_end: data.window_end }
    kills.value = data.items
    selectedIndices.value.clear()
  } catch (e) {
    loadError.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

function toggleKill(i: number, checked: boolean) {
  if (checked) selectedIndices.value.add(i)
  else selectedIndices.value.delete(i)
}

function selectAll() {
  kills.value.forEach((k, i) => { if (!k.already_submitted) selectedIndices.value.add(i) })
}

function clearAll() {
  selectedIndices.value.clear()
}

function toggleAll(checked: boolean) {
  if (checked) selectAll()
  else clearAll()
}

async function onBatchSubmit() {
  if (selectedIndices.value.size === 0) { await showAlert('请先选择要提交的损失记录'); return }
  if (batchLoading.value) return
  characters.value = await api.getCharacters()
  if (characters.value.length === 0) { await showAlert('未找到可用角色，请联系管理员绑定角色'); return }
  if (characters.value.length === 1) {
    await doSubmit(characters.value[0].value)
  } else {
    charDialogVisible.value = true
  }
}

async function onCharSelected(charId: number) {
  charDialogVisible.value = false
  await doSubmit(charId)
}

async function doSubmit(charId: number) {
  batchLoading.value = true
  submitMsg.value = ''
  let ok = 0
  const errors: string[] = []
  for (const i of selectedIndices.value) {
    const k = kills.value[i]
    try {
      await api.submitRequest({
        zkb_url: k.zkb_url,
        character_id: charId,
        fleet_action_id: sdk.fleetActionId.value!,
      })
      ok++
      k.already_submitted = true
    } catch (e) {
      errors.push(k.ship_name + '：' + (e as Error).message)
    }
  }
  selectedIndices.value.clear()
  batchLoading.value = false
  submitMsgOk.value = errors.length === 0
  submitMsg.value = `✅ 成功提交 ${ok} 条` + (errors.length ? '\n' + errors.join('\n') : '')
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}
function isk(v: number): string {
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) + ' ISK'
}

onMounted(loadKills)
</script>

<template>
  <div>
    <p v-if="loading" class="loading">正在拉取舰队期间的损失记录，请稍候…</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">加载失败：{{ loadError }}</p>

    <template v-else-if="fleetInfo">
      <div class="fleet-header">
        <h3>⚡ {{ fleetInfo.fleet_action_name }}</h3>
        <div class="window">
          活动时间：{{ fmtDate(fleetInfo.window_start) }} → {{ fmtDate(fleetInfo.window_end) }}
        </div>
      </div>

      <p v-if="kills.length === 0" class="empty">在此舰队活动期间未找到您的损失记录</p>

      <template v-else>
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button class="btn btn-secondary btn-sm" @click="selectAll">全选</button>
          <button class="btn btn-secondary btn-sm" @click="clearAll">取消全选</button>
          <span style="font-size:.85rem;color:#7a796f">
            共 {{ kills.length }} 条，其中 {{ submittable.length }} 条未提交
          </span>
          <button
            class="btn btn-primary"
            style="margin-left:auto"
            :disabled="batchLoading || selectedIndices.size === 0"
            @click="onBatchSubmit"
          >{{ batchLoading ? '⏳ 提交中…' : '批量提交所选' }}</button>
        </div>

        <table>
          <thead>
            <tr>
              <th class="checkbox-col">
                <input type="checkbox" @change="toggleAll(($event.target as HTMLInputElement).checked)" />
              </th>
              <th>舰船</th><th>损失时间</th><th>损失价值</th><th>预计补损</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(k, i) in kills"
              :key="k.killmail_id"
              class="kill-row"
              :class="{ selected: selectedIndices.has(i) }"
            >
              <td>
                <input
                  type="checkbox"
                  :disabled="k.already_submitted"
                  :checked="selectedIndices.has(i)"
                  @change="toggleKill(i, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td>{{ k.ship_name }}</td>
              <td>{{ fmtDate(k.killed_at) }}</td>
              <td class="isk">{{ isk(k.loss_value_raw) }}</td>
              <td class="isk"><strong>{{ isk(k.calculated_value) }}</strong></td>
              <td>
                <span v-if="k.already_submitted" class="badge badge-approved">已提交</span>
                <span v-else class="badge badge-pending">未提交</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div
          v-if="submitMsg"
          style="margin-top:12px;font-size:.88rem;white-space:pre-line"
          :style="{ color: submitMsgOk ? '#4caf50' : '#e06060' }"
        >{{ submitMsg }}</div>
      </template>
    </template>

    <CharSelectDialog
      :visible="charDialogVisible"
      :characters="characters"
      @confirm="onCharSelected"
      @cancel="charDialogVisible = false"
    />
  </div>
</template>
