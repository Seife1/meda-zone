import apiClient from './client'

export interface Booking {
  id: string
  reference: string
  player_id: string
  field_id: string
  slot_id: string
  subscription_id: string | null
  slot_date: string
  slot_start_time: string
  slot_end_time: string
  status: 'confirmed' | 'checked_in' | 'cancelled'
  cancellation_reason: string | null
  checked_in_at: string | null
  created_at: string
}

export const bookingsApi = {
  listForField: (fieldId: string) =>
    apiClient.get<Booking[]>('/bookings/me', { params: { field_id: fieldId } }),
  verify: (reference: string) =>
    apiClient.get(`/bookings/verify/${reference}`),
  checkIn: (bookingId: string) =>
    apiClient.post(`/bookings/${bookingId}/checkin`),
}
