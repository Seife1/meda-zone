import apiClient from './client'

export interface Subscription {
  id: string
  player_id: string
  field_id: string
  proposed_by: string
  recurring_days: string[]
  session_start_time: string
  session_duration_hours: number
  tier: '1_month' | '2_months' | '3_months'
  total_sessions: number
  total_price: number
  status: string
  start_date: string | null
  expiry_date: string | null
  payment_provider: string | null
  created_at: string
}

export interface SubscriptionCreate {
  player_id: string; field_id: string
  recurring_days: string[]
  session_start_time: string
  session_duration_hours: number
  tier: '1_month' | '2_months' | '3_months'
}

export const subscriptionsApi = {
  propose: (data: SubscriptionCreate) =>
    apiClient.post<Subscription>('/subscriptions', data),
  listForField: (fieldId: string) =>
    apiClient.get<Subscription[]>('/subscriptions/player/me', { params: { field_id: fieldId } }),
  stats: () => apiClient.get('/subscriptions/stats'),
  proposeSlotChange: (subId: string, data: unknown) =>
    apiClient.post(`/subscriptions/${subId}/slot-change`, data),
}
