<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api'
import { useHelmSdk } from '@/composables/useHelmSdk'
import AlertDialog from '@/components/AlertDialog.vue'
import PapFleetView from '@/views/PapFleetView.vue'
import FleetQuickView from '@/views/FleetQuickView.vue'
import MyRequestsView from '@/views/MyRequestsView.vue'
import ManageView from '@/views/ManageView.vue'
import ConfigView from '@/views/ConfigView.vue'

type TabId = 'pap' | 'fleet' | 'mine' | 'review' | 'config'

const sdk = useHelmSdk()
const ready = ref(false)
const initError = ref('')
const activeTab = ref<TabId>('mine')

const tabs = computed(() => {
  const result: { id: TabId; label: string }[] = []
  if (sdk.hasPerm('srp.submit'))   result.push({ id: 'pap',    label: '🏅 PAP 舰队补损' })
  if (sdk.fleetActionId.value)     result.push({ id: 'fleet',  label: '⚡ 舰队快速提交' })
  result.push({ id: 'mine', label: '📋 我的申请' })
  if (sdk.isOfficer.value)         result.push({ id: 'review', label: '🛡️ 补损管理' })
  if (sdk.isAdmin.value)           result.push({ id: 'config', label: '⚙️ 配置' })
  return result
})

onMounted(async () => {
  sdk.parseUrlParams()
  try {
    const me = await api.getMe()
    sdk.setUserInfo(me.permissions, me.is_admin, me.is_officer)
  } catch (e) {
    initError.value = (e as Error).message
  }
  // Determine initial tab using same priority as original
  if (sdk.fleetActionId.value)        activeTab.value = 'fleet'
  else if (sdk.hasPerm('srp.submit')) activeTab.value = 'pap'
  else if (sdk.isOfficer.value)       activeTab.value = 'review'
  else                                 activeTab.value = 'mine'
  ready.value = true
})
</script>

<template>
  <div class="app">
    <AlertDialog />

    <div v-if="!ready" class="content">
      <p class="loading">正在初始化…</p>
    </div>

    <template v-else>
      <div class="topbar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>
      <div class="content">
        <div v-if="initError" style="color:#e06060;margin-bottom:12px">权限加载失败：{{ initError }}</div>
        <PapFleetView   v-if="activeTab === 'pap'"    />
        <FleetQuickView v-else-if="activeTab === 'fleet'" />
        <MyRequestsView v-else-if="activeTab === 'mine'"  />
        <ManageView     v-else-if="activeTab === 'review'" />
        <ConfigView     v-else-if="activeTab === 'config'" />
      </div>
    </template>
  </div>
</template>
