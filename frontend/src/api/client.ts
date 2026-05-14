import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      const { refresh, logout } = useAuthStore.getState()
      const ok = await refresh()
      if (ok) {
        // Retry once with new token
        const token = useAuthStore.getState().accessToken
        err.config.headers.Authorization = `Bearer ${token}`
        return api.request(err.config)
      }
      logout()
    }
    return Promise.reject(err)
  },
)

export default api
