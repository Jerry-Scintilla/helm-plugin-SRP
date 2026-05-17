/// <reference types="vite/client" />

declare const HelmSDK: {
  init(callback: (ctx: { token: string; apiBase: string }) => void): void
  getToken(): string
}
