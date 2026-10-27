import apiClient from './client'

export interface Slot {
  id: string
  field_id: string
  slot_date: string
  start_time: string
  end_time: string
  duration_minutes: number
  status: 'available' | 'pending' | 'booked' | 'closed'
}

export interface SlotGenerateRequest {
  start_date: string; end_date: string
  slot_duration_minutes: 30 | 60 | 90
  open_time: string; close_time: string
}

export const slotsApi = {
  list: (fieldId: string) =>
    apiClient.get<Slot[]>(`/fields/${fieldId}/slots`),
  generate: (fieldId: string, data: SlotGenerateRequest) =>
    apiClient.post<{ created_count: number; skipped_count: number }>(
      `/fields/${fieldId}/slots/generate`, data),
  setStatus: (slotId: string, status: 'available' | 'closed') =>
    apiClient.patch<Slot>(`/slots/${slotId}/status`, { status }),
}
