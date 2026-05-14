import { useAuthStore } from '@/store/authStore'

export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const login       = useAuthStore((s) => s.login)
  const logout      = useAuthStore((s) => s.logout)
  return { isAuthenticated: !!accessToken, login, logout }
}
