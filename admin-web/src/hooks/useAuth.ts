import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '../api/client'

function saveSession(user: { id: string; role: string; display_name: string | null }) {
  localStorage.setItem('user_id', user.id)
  localStorage.setItem('role', user.role)
  localStorage.setItem('display_name', user.display_name ?? '')
}

function clearSession() {
  ;['access_token', 'refresh_token', 'user_id', 'role', 'display_name'].forEach(k =>
    localStorage.removeItem(k)
  )
}

export function useAuth() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [initializing, setInitializing] = useState(true)

  useEffect(() => {
    // Just check if token exists on mount
    setInitializing(false)
  }, [])

  const login = async (phone: string, password: string) => {
    setLoading(true)
    try {
      const { data } = await apiClient.post('/auth/admin/login', {
        phone_number: phone,
        password,
      })

      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      saveSession(data.user)

      const role = data.user.role as string
      if (!['FIELD_OWNER', 'SUPER_ADMIN'].includes(role)) {
        clearSession()
        throw new Error('This account does not have admin access.')
      }

      navigate('/')
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.error?.message
        || err?.response?.data?.detail
        || err?.message
        || 'Login failed'
      throw new Error(msg)
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    clearSession()
    navigate('/login')
  }

  return {
    login,
    logout,
    loading,
    initializing,
    isAuthenticated: !!localStorage.getItem('access_token'),
    role: localStorage.getItem('role') ?? '',
    displayName: localStorage.getItem('display_name') ?? '',
  }
}
