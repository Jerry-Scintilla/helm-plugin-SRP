<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type MyPapFleetItem, type FleetKillItem, type Character } from '@/api'
import { useAlertDialog } from '@/composables/useAlertDialog'
import CharSelectDialog from '@/components/CharSelectDialog.vue'
import CustomSelect, { type SelectOption } from '@/components/CustomSelect.vue'

const { showAlert } = useAlertDialog()

const papFleets = ref<MyPapFleetItem[]>([])
const fleetsLoading = ref(false)
const fleetsError = ref('')

const selectedFleetId = ref<number | null>(null)
const kills = ref<FleetKillItem[]>([])
const killsLoading = ref(false)
const killsError = ref('')

const selectedIndices = ref(new Set<number>())
const batchLoading = ref(false)
const submitMsg = ref('')
const submitMsgOk = ref(true)

const characters = ref<Character[]>([])
const charDialogVisible = ref(false)

const selectedFleet = computed(() =>
  papFleets.value.find(f => f.fleet_action_id === selectedFleetId.value) ?? null
)

const fleetOptions = computed((): SelectOption[] => [
  { value: null, label: '— 请选择舰队 —' },
  ...papFleets.value.map(f => ({
    value: f.fleet_action_id,
    label: `${f.fleet_action_name}  (${fmtDate(f.window_start)})`,
  })),
])
const submittable = computed(() =>
  kills.value.filter(k => !k.already_submitted)
)

async function loadFleets() {
  fleetsLoading.value = true
  fleetsError.value = ''
  try {
    papFleets.value = await api.getMyPapFleets()
  } catch (e) {
    fleetsError.value = (e as Error).message
  } finally {
    fleetsLoading.value = false
  }
}

async function onFleetChange(val: string | number | boolean | null) {
  selectedFleetId.value = typeof val === 'number' ? val : null
  kills.value = []
  selectedIndices.value.clear()
  submitMsg.value = ''
  if (selectedFleetId.value) {
    await loadKills()
  }
}

async function loadKills() {
  if (!selectedFleetId.value) return
  killsLoading.value = true
  killsError.value = ''
  try {
    const data = await api.getFleetKills(selectedFleetId.value)
    kills.value = data.items
  } catch (e) {
    killsError.value = (e as Error).message
  } finally {
    killsLoading.value = false
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
        fleet_action_id: selectedFleetId.value!,
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

async function refreshFleets() {
  papFleets.value = []
  selectedFleetId.value = null
  kills.value = []
  selectedIndices.value.clear()
  await loadFleets()
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}
function isk(v: number): string {
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) + ' ISK'
}

onMounted(loadFleets)
</script>

<template>
  <div>
    <h2>PAP 舰队补损</h2>

    <p v-if="fleetsLoading" class="loading">加载 PAP 记录中…</p>
    <p v-else-if="fleetsError" class="empty" style="color:#e06060">无法加载 PAP 记录：{{ fleetsError }}</p>
    <p v-else-if="papFleets.length === 0" class="empty">未找到您的 PAP 记录</p>

    <template v-else>
      <!-- Fleet selector -->
      <div class="pap-select-bar">
        <CustomSelect
          :model-value="selectedFleetId"
          :options="fleetOptions"
          @change="onFleetChange"
        />
        <button class="btn btn-secondary btn-sm" @click="refreshFleets">刷新列表</button>
      </div>

      <!-- Selected fleet info -->
      <div v-if="selectedFleet" class="fleet-header">
        <h3>
          {{ selectedFleet.fleet_action_name }}
          <span v-if="selectedFleet.status === 'active'" class="pap-badge-active">⚡ 进行中</span>
          <span v-else class="pap-badge-ended">已结束</span>
        </h3>
        <div class="window">
          活动时间：{{ fmtDate(selectedFleet.window_start) }} →
          {{ selectedFleet.window_end ? fmtDate(selectedFleet.window_end) : '进行中' }}
        </div>
        <div class="window" style="margin-top:2px">
          PAP 获得时间：{{ fmtDate(selectedFleet.pap_issued_at) }}
        </div>
      </div>

      <!-- No fleet selected -->
      <p v-if="!selectedFleetId" class="empty" style="padding-top:32px">请从上方下拉列表选择一场舰队</p>

      <!-- Kills loading -->
      <p v-else-if="killsLoading" class="loading">正在拉取该舰队期间的损失记录…</p>
      <p v-else-if="killsError" class="empty" style="color:#e06060">加载损失记录失败：{{ killsError }}</p>
      <p v-else-if="kills.length === 0" class="empty">在此舰队活动期间未找到您的损失记录</p>

      <!-- Kills table -->
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
