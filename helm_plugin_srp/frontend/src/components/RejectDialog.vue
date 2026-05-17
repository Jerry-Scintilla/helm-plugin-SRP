<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from '@/i18n'
defineProps<{ visible: boolean }>()
const emit = defineEmits<{ confirm: [notes: string]; cancel: [] }>()
const notes = ref('')
const { t } = useI18n()

function handleConfirm() {
  emit('confirm', notes.value)
  notes.value = ''
}
function handleCancel() {
  notes.value = ''
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="handleCancel">
      <div class="dialog-box" style="min-width:340px;max-width:480px">
        <div class="dialog-header">{{ t('reject.title') }}</div>
        <div class="dialog-body">
          <div class="form-group">
            <label>{{ t('reject.reason') }}</label>
            <textarea v-model="notes" :placeholder="t('reject.reasonPh')"></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="handleCancel">{{ t('common.cancel') }}</button>
          <button class="btn btn-danger" @click="handleConfirm">{{ t('reject.confirm') }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
