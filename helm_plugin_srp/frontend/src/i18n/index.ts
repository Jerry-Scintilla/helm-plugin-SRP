import { ref } from 'vue'
import zh from './zh'
import en from './en'

type MessageKey = keyof typeof zh
type Locale = 'zh' | 'en'

const MESSAGES: Record<Locale, Record<MessageKey, string>> = { zh, en }

const locale = ref<Locale>('zh')

export function setLocale(l: string): void {
  locale.value = (l in MESSAGES ? l : 'zh') as Locale
}

export function getLocale(): string {
  return locale.value
}

export function useI18n() {
  function t(key: MessageKey, params?: Record<string, string | number>): string {
    const msgs: Record<MessageKey, string> = MESSAGES[locale.value]
    let str: string = msgs[key]
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, String(v))
      }
    }
    return str
  }

  // locale-aware number/date formatters
  function fmtDate(s: string | null | undefined): string {
    if (!s) return '—'
    const lc = locale.value === 'zh' ? 'zh-CN' : 'en-US'
    return new Date(s).toLocaleString(lc, { hour12: false })
  }

  function isk(v: number): string {
    const lc = locale.value === 'zh' ? 'zh-CN' : 'en-US'
    return v.toLocaleString(lc, { maximumFractionDigits: 0 }) + ' ISK'
  }

  return { t, fmtDate, isk }
}
