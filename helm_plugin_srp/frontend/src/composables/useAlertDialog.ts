import { ref } from 'vue'

const message = ref('')
const visible = ref(false)
let _resolve: (() => void) | null = null

export function useAlertDialog() {
  function showAlert(msg: string): Promise<void> {
    message.value = msg
    visible.value = true
    return new Promise(r => { _resolve = r })
  }

  function closeAlert() {
    visible.value = false
    message.value = ''
    _resolve?.()
    _resolve = null
  }

  return { alertMessage: message, alertVisible: visible, showAlert, closeAlert }
}
