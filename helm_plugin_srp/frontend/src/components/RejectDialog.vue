<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ visible: boolean }>()
const emit = defineEmits<{ confirm: [notes: string]; cancel: [] }>()
const notes = ref('')

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
        <div class="dialog-header">拒绝补损申请</div>
        <div class="dialog-body">
          <div class="form-group">
            <label>拒绝理由（可选）</label>
            <textarea v-model="notes" placeholder="请输入拒绝理由…"></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="handleCancel">取消</button>
          <button class="btn btn-danger" @click="handleConfirm">确认拒绝</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
