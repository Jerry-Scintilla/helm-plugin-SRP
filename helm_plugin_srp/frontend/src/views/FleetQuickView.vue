<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type FleetKillItem, type FleetKillsResponse, type Character } from '@/api'
import { useHelmSdk } from '@/composables/useHelmSdk'
import { useI18n } from '@/i18n'
import { useAlertDialog } from '@/composables/useAlertDialog'
import CharSelectDialog from '@/components/CharSelectDialog.vue'

const sdk = useHelmSdk()
const { t, fmtDate, isk } = useI18n()
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
  if (selectedIndices.value.size === 0) { await showAlert(t('kills.noSelection')); return }
  if (batchLoading.value) return
  characters.value = await api.getCharacters()
  if (characters.value.length === 0) { await showAlert(t('kills.noChars')); return }
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
  submitMsg.value = t('kills.submitSuccess', { ok }) + (errors.length ? '\n' + errors.join('\n') : '')
}

onMounted(loadKills)
</script>

<template>
  <div>
    <p v-if="loading" class="loading">{{ t('fleet.loading') }}</p>
    <p v-else-if="loadError" class="empty" style="color:#e06060">{{ t('common.loadFailed') }}{{ loadError }}</p>

    <template v-else-if="fleetInfo">
      <div class="fleet-header">
        <h3>⚡ {{ fleetInfo.fleet_action_name }}</h3>
        <div class="window">
          {{ t('fleet.windowTime') }}{{ fmtDate(fleetInfo.window_start) }} → {{ fmtDate(fleetInfo.window_end) }}
        </div>
      </div>

      <p v-if="kills.length === 0" class="empty">{{ t('kills.noKills') }}</p>

      <template v-else>
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button class="btn btn-secondary btn-sm" @click="selectAll">{{ t('kills.selectAll') }}</button>
          <button class="btn btn-secondary btn-sm" @click="clearAll">{{ t('kills.clearAll') }}</button>
          <span style="font-size:.85rem;color:#7a796f">
            {{ t('kills.count', { total: kills.length, submittable: submittable.length }) }}
          </span>
          <button
            class="btn btn-primary"
            style="margin-left:auto"
            :disabled="batchLoading || selectedIndices.size === 0"
            @click="onBatchSubmit"
          >{{ batchLoading ? t('kills.submitting') : t('kills.batchSubmit') }}</button>
        </div>

        <table>
          <thead>
            <tr>
              <th class="checkbox-col">
                <input type="checkbox" @change="toggleAll(($event.target as HTMLInputElement).checked)" />
              </th>
              <th>{{ t('kills.colShip') }}</th>
              <th>{{ t('kills.colTime') }}</th>
              <th>{{ t('kills.colLoss') }}</th>
              <th>{{ t('kills.colSrp') }}</th>
              <th>{{ t('kills.colStatus') }}</th>
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
                <span v-if="k.already_submitted" class="badge badge-approved">{{ t('kills.submitted') }}</span>
                <span v-else class="badge badge-pending">{{ t('kills.notSubmitted') }}</span>
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
