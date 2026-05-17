import { createApp, nextTick } from 'vue'
import App from './App.vue'
import { initSDK, updateToken } from './api'
import './style.css'

declare const HelmSDK: any

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const el = document.createElement('script')
    el.src = src
    el.onload = () => resolve()
    el.onerror = () => reject(new Error(`Failed to load ${src}`))
    document.head.appendChild(el)
  })
}

loadScript('/plugin-sdk/helm-sdk.js').then(() => {
  HelmSDK.init((ctx: { token: string; apiBase: string }) => {
    initSDK(ctx.token, ctx.apiBase)

    window.addEventListener('message', (e: MessageEvent) => {
      if (e.data?.type === 'helm:token:refreshed') {
        updateToken(e.data.token as string)
      }
    })

    // Guard against double-mount when token refresh re-fires the callback
    if (!document.getElementById('app')?.children.length) {
      nextTick(() => createApp(App).mount('#app'))
    }
  })
})
