import { ref, readonly } from 'vue'

const permissions = ref<string[]>([])
const isAdmin = ref(false)
const isOfficer = ref(false)
const fleetActionId = ref<number | null>(null)

export function useHelmSdk() {
  function hasPerm(p: string): boolean {
    return isAdmin.value || permissions.value.includes(p)
  }

  function setUserInfo(perms: string[], admin: boolean, officer: boolean) {
    permissions.value = perms
    isAdmin.value = admin
    isOfficer.value = officer
  }

  function parseUrlParams() {
    const params = new URLSearchParams(window.location.search)
    const raw = params.get('fleet_action')
    fleetActionId.value = raw ? parseInt(raw) : null
  }

  return {
    permissions: readonly(permissions),
    isAdmin: readonly(isAdmin),
    isOfficer: readonly(isOfficer),
    fleetActionId: readonly(fleetActionId),
    hasPerm,
    setUserInfo,
    parseUrlParams,
  }
}
