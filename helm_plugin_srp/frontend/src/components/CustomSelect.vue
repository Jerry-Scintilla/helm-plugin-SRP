<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

export interface SelectOption {
  value: string | number | boolean | null
  label: string
  disabled?: boolean
}

const props = defineProps<{
  modelValue?: string | number | boolean | null
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [val: string | number | boolean | null]
  'change': [val: string | number | boolean | null]
}>()

const isOpen = ref(false)
const triggerEl = ref<HTMLElement | null>(null)
const dropdownStyle = ref<Record<string, string>>({})

const displayLabel = computed(() => {
  const found = props.options.find(o => o.value === props.modelValue)
  return found?.label ?? props.placeholder ?? ''
})

const hasValue = computed(() =>
  props.modelValue !== null && props.modelValue !== undefined && props.modelValue !== ''
)

function calcPosition() {
  if (!triggerEl.value) return
  const r = triggerEl.value.getBoundingClientRect()
  const maxH = 240
  const spaceBelow = window.innerHeight - r.bottom - 4
  if (spaceBelow >= Math.min(props.options.length * 36, maxH)) {
    dropdownStyle.value = {
      position: 'fixed',
      top: r.bottom + 4 + 'px',
      left: r.left + 'px',
      width: r.width + 'px',
      maxHeight: maxH + 'px',
    }
  } else {
    dropdownStyle.value = {
      position: 'fixed',
      bottom: window.innerHeight - r.top + 4 + 'px',
      left: r.left + 'px',
      width: r.width + 'px',
      maxHeight: maxH + 'px',
    }
  }
}

function toggle() {
  if (props.disabled) return
  if (!isOpen.value) calcPosition()
  isOpen.value = !isOpen.value
}

function select(opt: SelectOption) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  isOpen.value = false
}

function onDocClick(e: MouseEvent) {
  if (!triggerEl.value?.contains(e.target as Node)) {
    isOpen.value = false
  }
}
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') isOpen.value = false
}

onMounted(() => {
  document.addEventListener('mousedown', onDocClick)
  document.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocClick)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div
    ref="triggerEl"
    class="csel"
    :class="{ 'csel--open': isOpen, 'csel--disabled': disabled }"
    @click="toggle"
  >
    <span class="csel-label" :class="{ 'csel-label--placeholder': !hasValue }">
      {{ displayLabel || placeholder }}
    </span>
    <svg class="csel-arrow" :class="{ 'csel-arrow--up': isOpen }" viewBox="0 0 10 6" width="10" height="6">
      <path d="M0 0l5 6 5-6z" fill="currentColor" />
    </svg>

    <Teleport to="body">
      <div v-if="isOpen" class="csel-dropdown" :style="dropdownStyle">
        <div
          v-for="opt in options"
          :key="String(opt.value)"
          class="csel-option"
          :class="{
            'csel-option--selected': opt.value === modelValue,
            'csel-option--disabled': opt.disabled,
          }"
          @mousedown.prevent="select(opt)"
        >{{ opt.label }}</div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.csel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 7px 10px 7px 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-body);
  font-family: var(--font-sans);
  font-size: .88rem;
  cursor: pointer;
  user-select: none;
  transition: border-color .15s;
  min-height: 36px;
}
.csel:hover { border-color: var(--text-dim); }
.csel--open { border-color: var(--focus); box-shadow: 0 0 0 3px rgba(56,152,236,.15); outline: none; }
.csel--disabled { opacity: .45; cursor: not-allowed; pointer-events: none; }

.csel-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.csel-label--placeholder { color: var(--text-dim); }

.csel-arrow {
  flex-shrink: 0;
  margin-left: 8px;
  color: var(--text-muted);
  transition: transform .18s ease;
}
.csel-arrow--up { transform: rotate(180deg); }
</style>

<!-- Dropdown: not scoped so Teleport to body works -->
<style>
.csel-dropdown {
  z-index: 2000;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, .55);
  animation: csel-fade .1s ease;
}
@keyframes csel-fade {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.csel-option {
  padding: 8px 12px;
  font-size: .88rem;
  font-family: var(--font-sans);
  color: var(--text-body);
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background .12s, color .12s;
}
.csel-option:hover {
  background: rgba(255, 255, 255, .05);
  color: var(--text-primary);
}
.csel-option--selected {
  color: var(--text-primary);
  border-left-color: var(--brand);
  background: rgba(201, 100, 66, .08);
}
.csel-option--disabled {
  color: var(--text-dim);
  cursor: default;
}
</style>
