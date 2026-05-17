<script setup lang="ts">
import { useAlertDialog } from '@/composables/useAlertDialog'
const { alertMessage, alertVisible, closeAlert } = useAlertDialog()
</script>

<template>
  <Teleport to="body">
    <div v-if="alertVisible" class="dialog-overlay" @click.self="closeAlert">
      <div class="dialog-box">
        <div class="dialog-header">提示</div>
        <div class="dialog-body">{{ alertMessage }}</div>
        <div class="dialog-footer">
          <button class="btn btn-primary" @click="closeAlert">确定</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
