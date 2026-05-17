<script setup lang="ts">
import { useAlertDialog } from '@/composables/useAlertDialog'
import { useI18n } from '@/i18n'
const { alertMessage, alertVisible, closeAlert } = useAlertDialog()
const { t } = useI18n()
</script>

<template>
  <Teleport to="body">
    <div v-if="alertVisible" class="dialog-overlay" @click.self="closeAlert">
      <div class="dialog-box">
        <div class="dialog-header">{{ t('alert.title') }}</div>
        <div class="dialog-body">{{ alertMessage }}</div>
        <div class="dialog-footer">
          <button class="btn btn-primary" @click="closeAlert">{{ t('alert.ok') }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
