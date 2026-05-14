import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  login: (email: string, password: string) => Promise<void>
  refresh: () => Promise<boolean>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,

      login: async (email, password) => {
        const res = await axios.post('/api/v1/auth/login', { email, password })
        set({ accessToken: res.data.access_token, refreshToken: res.data.refresh_token })
      },

      refresh: async () => {
        const rt = get().refreshToken
        if (!rt) return false
        try {
          const res = await axios.post('/api/v1/auth/refresh', { refresh_token: rt })
          set({ accessToken: res.data.access_token, refreshToken: res.data.refresh_token })
          return true
        } catch {
          set({ accessToken: null, refreshToken: null })
          return false
        }
      },

      logout: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: 'quantbr-auth', partialize: (s) => ({ refreshToken: s.refreshToken }) },
  ),
)
