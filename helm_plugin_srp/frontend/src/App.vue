<script setup lang="ts">
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { api } from '@/api'
import { useHelmSdk } from '@/composables/useHelmSdk'
import { useI18n } from '@/i18n'
import AlertDialog from '@/components/AlertDialog.vue'
import PapFleetView from '@/views/PapFleetView.vue'
import FleetQuickView from '@/views/FleetQuickView.vue'
import MyRequestsView from '@/views/MyRequestsView.vue'
import ManageView from '@/views/ManageView.vue'
import ConfigView from '@/views/ConfigView.vue'

// 看板依赖较大的 ECharts，按需懒加载，独立成 chunk
const DashboardView = defineAsyncComponent(() => import('@/views/DashboardView.vue'))

type TabId = 'pap' | 'fleet' | 'mine' | 'review' | 'dashboard' | 'config'

const sdk = useHelmSdk()
const { t } = useI18n()
const ready = ref(false)
const initError = ref('')
const activeTab = ref<TabId>('mine')

const tabs = computed(() => {
  const result: { id: TabId; label: string }[] = []
  if (sdk.hasPerm('srp.submit'))   result.push({ id: 'pap',    label: t('app.tab.pap') })
  if (sdk.fleetActionId.value)     result.push({ id: 'fleet',  label: t('app.tab.fleet') })
  result.push({ id: 'mine', label: t('app.tab.mine') })
  if (sdk.isOfficer.value)         result.push({ id: 'review', label: t('app.tab.review') })
  if (sdk.isOfficer.value)         result.push({ id: 'dashboard', label: t('app.tab.dashboard') })
  if (sdk.isAdmin.value)           result.push({ id: 'config', label: t('app.tab.config') })
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
      <p class="loading">{{ t('app.initializing') }}</p>
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
        <div v-if="initError" style="color:#e06060;margin-bottom:12px">{{ t('app.permLoadFailed') }}{{ initError }}</div>
        <PapFleetView   v-if="activeTab === 'pap'"    />
        <FleetQuickView v-else-if="activeTab === 'fleet'" />
        <MyRequestsView v-else-if="activeTab === 'mine'"  />
        <ManageView     v-else-if="activeTab === 'review'" />
        <DashboardView  v-else-if="activeTab === 'dashboard'" />
        <ConfigView     v-else-if="activeTab === 'config'" />
      </div>
    </template>
  </div>
</template>
