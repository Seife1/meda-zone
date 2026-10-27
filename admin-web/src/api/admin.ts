import apiClient from './client'

export interface AdminUser {
  id: string; phone_number: string; display_name: string | null
  role: string; is_active: boolean; created_at: string
  temp_password?: string
}
export interface Analytics {
  total_active_fields: number; total_bookings_30d: number
  daily_bookings: { date: string; count: number }[]
}

export const adminApi = {
  listUsers: (role?: string) =>
    apiClient.get<AdminUser[]>('/admin/users', { params: role ? { role } : {} }),
  createUser: (data: { phone_number: string; display_name?: string; role: string }) =>
    apiClient.post<AdminUser>('/admin/users', data),
  updateUser: (id: string, data: Partial<AdminUser>) =>
    apiClient.patch<AdminUser>(`/admin/users/${id}`, data),
  getAnalytics: () => apiClient.get<Analytics>('/admin/analytics'),
  getSubStats: () => apiClient.get('/admin/analytics/subscriptions'),
}
