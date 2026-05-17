<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Character } from '@/api'

const props = defineProps<{ visible: boolean; characters: Character[] }>()
const emit = defineEmits<{ confirm: [charId: number]; cancel: [] }>()
const selected = ref<number | null>(null)

watch(() => props.visible, (v) => {
  if (v && props.characters.length > 0) {
    selected.value = props.characters[0].value
  }
})

function handleConfirm() {
  if (!selected.value) return
  emit('confirm', selected.value)
}
function handleCancel() {
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="handleCancel">
      <div class="dialog-box" style="min-width:340px;max-width:480px">
        <div class="dialog-header">选择提交角色</div>
        <div class="dialog-body">
          <div class="form-group">
            <label>角色</label>
            <select v-model="selected">
              <option v-for="c in characters" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="handleCancel">取消</button>
          <button class="btn btn-primary" :disabled="!selected" @click="handleConfirm">确认</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
