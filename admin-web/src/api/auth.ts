import apiClient from './client'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: { id: string; phone_number: string; display_name: string | null; role: string }
}

export const authApi = {
  adminLogin: (phone_number: string, password: string) =>
    apiClient.post<LoginResponse>('/auth/admin/login', { phone_number, password }),
}
