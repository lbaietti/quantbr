import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function LoginPage() {
  const { login }  = useAuth()
  const navigate   = useNavigate()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Credenciais inválidas.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <div className="bg-panel border border-border rounded p-8 w-80">
        <h1 className="text-white font-bold text-lg tracking-widest mb-6 text-center">QUANTBR</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="bg-surface border border-border rounded px-3 py-2 text-sm text-white placeholder-neutral focus:outline-none focus:border-accent"
          />
          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="bg-surface border border-border rounded px-3 py-2 text-sm text-white placeholder-neutral focus:outline-none focus:border-accent"
          />
          {error && <p className="text-down text-xs">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-accent hover:bg-accent/80 disabled:opacity-50 text-white rounded py-2 text-sm font-semibold transition-colors"
          >
            {loading ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
