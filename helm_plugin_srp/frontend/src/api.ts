import { getLocale } from './i18n'

let _token = ''
let _apiBase = ''
const SRP_BASE = '/api/v1/plugins/srp'

export function initSDK(token: string, apiBase: string) {
  _token = token
  _apiBase = apiBase
}

export function updateToken(token: string) {
  _token = token
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(_apiBase + SRP_BASE + path, {
    method,
    headers: {
      'Authorization': 'Bearer ' + _token,
      'Content-Type': 'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) {
    let detail = ''
    try { detail = (await r.json()).detail } catch { detail = r.statusText }
    throw new Error(detail || `请求失败 ${r.status}`)
  }
  if (r.status === 204) return null as T
  return r.json() as Promise<T>
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface MeResponse {
  permissions: string[]
  is_admin: boolean
  is_officer: boolean
}

export interface SrpConfig {
  // 共用配置
  price_region_id: number
  price_order_type: 'buy' | 'sell'
  // 常规补损
  coefficient: number
  enabled: boolean
  min_loss_value: number
  full_loss: boolean
  // PAP 舰队补损
  pap_coefficient: number
  pap_enabled: boolean
  pap_min_loss_value: number
  pap_full_loss: boolean
}

export interface KillmailItem {
  type_id: number
  name: string
  icon_url: string | null
  qty_destroyed: number
  qty_dropped: number
}

export interface KillmailPreview {
  killmail_id: number
  ship_type_id: number
  ship_name: string
  ship_icon_url: string | null
  items: KillmailItem[]
  loss_value_raw: number
  calculated_value: number
  price_source: string
  coefficient: number
  eligible: boolean
  ineligible_reason?: string
  zkb_url?: string
}

export type SrpStatus = 'pending' | 'approved' | 'rejected' | 'paid'

export interface SrpRequest {
  id: number
  character_name: string
  ship_type_id: number
  ship_name: string
  loss_value_raw: number
  calculated_value: number
  status: SrpStatus
  created_at: string
  killmail_id: number
  zkb_url: string
  notes?: string | null
  officer_notes?: string | null
}

export interface SrpRequestDetail extends SrpRequest {
  killmail_hash: string
  ship_icon_url: string | null
  items: KillmailItem[]
}

export interface SrpRequestPage {
  items: SrpRequest[]
  total: number
}

export interface FleetKillItem {
  killmail_id: number
  zkb_url: string
  ship_name: string
  killed_at: string
  loss_value_raw: number
  calculated_value: number
  already_submitted: boolean
}

export interface FleetKillsResponse {
  fleet_action_id: number
  fleet_action_name: string
  window_start: string
  window_end: string
  items: FleetKillItem[]
}

export interface MyPapFleetItem {
  fleet_action_id: number
  fleet_action_name: string
  status: 'active' | 'ended'
  window_start: string
  window_end?: string
  pap_issued_at: string
}

export interface Character {
  label: string
  value: number
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export type DashboardPeriod = 'week' | 'month' | 'quarter' | 'year'

export interface DashboardSummary {
  period: DashboardPeriod
  window_start: string
  window_end: string
  total_requests: number
  total_loss_raw: number
  total_srp_amount: number
  paid_amount: number
  approved_amount: number
  pending_count: number
  approved_count: number
  rejected_count: number
  paid_count: number
}

export interface DashboardShipStat {
  ship_type_id: number
  ship_name: string
  icon_url: string | null
  count: number
  total_amount: number
}

export interface DashboardCharStat {
  character_id: number
  character_name: string
  count: number
  total_amount: number
}

export interface DashboardTrendPoint {
  bucket: string
  count: number
  total_amount: number
}

export interface DashboardResponse {
  summary: DashboardSummary
  granularity: 'day' | 'month'
  trend: DashboardTrendPoint[]
  ships: DashboardShipStat[]
  characters: DashboardCharStat[]
}

// ── API methods ───────────────────────────────────────────────────────────────

export const api = {
  getMe: () => request<MeResponse>('GET', '/me'),

  getConfig: () => request<SrpConfig>('GET', '/config'),
  updateConfig: (body: Partial<SrpConfig>) => request<SrpConfig>('PUT', '/config', body),

  previewKillmail: (url: string) =>
    request<KillmailPreview>('GET', `/killmail/preview?url=${encodeURIComponent(url)}&lang=${getLocale()}`),

  submitRequest: (body: {
    zkb_url: string
    character_id: number
    fleet_action_id?: number
    notes?: string | null
  }) => request<SrpRequest>('POST', '/requests', body),

  listRequests: (params: Record<string, string>) =>
    request<SrpRequestPage>('GET', '/requests?' + new URLSearchParams(params)),

  approveRequest: (id: number) => request('POST', `/requests/${id}/approve`, {}),

  rejectRequest: (id: number, officer_notes?: string | null) =>
    request('POST', `/requests/${id}/reject`, { officer_notes }),

  markPaid: (id: number) => request('POST', `/requests/${id}/mark_paid`, {}),

  getFleetKills: (fleetActionId: number) =>
    request<FleetKillsResponse>('GET', `/fleet/${fleetActionId}/kills`),

  getRequestDetail: (id: number) => request<SrpRequestDetail>('GET', `/requests/${id}/detail?lang=${getLocale()}`),

  getMyPapFleets: () => request<MyPapFleetItem[]>('GET', '/my-pap-fleets'),

  getDashboard: (period: DashboardPeriod) =>
    request<DashboardResponse>('GET', `/dashboard/stats?period=${period}&lang=${getLocale()}`),

  async getCharacters(): Promise<Character[]> {
    try {
      const r = await fetch(_apiBase + '/api/v1/plugins/fleet-action/characters', {
        headers: { 'Authorization': 'Bearer ' + _token, 'Content-Type': 'application/json' },
      })
      if (r.ok) return r.json() as Promise<Character[]>
    } catch { /* fleet-action not installed */ }
    return []
  },
}
