import apiClient from './client'

export interface Field {
  id: string
  name: string
  address: string
  neighborhood: string | null
  lat: number
  lng: number
  surface_type: string
  field_size: string | null
  amenities: Record<string, boolean>
  price_per_hour: number
  operating_hours: Record<string, unknown>
  photo_urls: string[]
  average_rating: number
  review_count: number
  is_active: boolean
  is_sponsored: boolean
  sponsorship_start: string | null
  sponsorship_end: string | null
  distance_km: number | null
}

export interface FieldAnalytics {
  total_bookings_30d: number
  total_revenue_30d: number
  daily_bookings: { date: string; count: number }[]
}

export interface TodaySlotSummary {
  id: string
  start_time: string
  end_time: string
  status: string
  booking_id: string | null
  player_name: string | null
}

export interface FieldCreate {
  name: string; address: string; neighborhood?: string
  lat: number; lng: number; surface_type: string; field_size?: string
  amenities?: Record<string, boolean>; price_per_hour: number
  operating_hours?: Record<string, unknown>; photo_urls?: string[]
}

export const fieldsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get<Field[]>('/fields', { params }),
  get: (id: string) => apiClient.get<Field>(`/fields/${id}`),
  create: (data: FieldCreate) => apiClient.post<Field>('/fields', data),
  update: (id: string, data: Partial<FieldCreate>) =>
    apiClient.put<Field>(`/fields/${id}`, data),
  setStatus: (id: string, is_active: boolean) =>
    apiClient.patch<Field>(`/fields/${id}/status`, null, { params: { is_active } }),
  setSponsor: (id: string, start: string, end: string) =>
    apiClient.patch<Field>(`/fields/${id}/sponsor`, {
      sponsorship_start: start, sponsorship_end: end,
    }),
  getAnalytics: (id: string) => apiClient.get<FieldAnalytics>(`/fields/${id}/analytics`),
  getTodaySlots: (id: string) => apiClient.get<TodaySlotSummary[]>(`/fields/${id}/today`),
}
