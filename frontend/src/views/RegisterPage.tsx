import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export const RegisterPage: React.FC = () => {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await register(email, password)
      navigate('/dashboard')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-12 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <h1 className="text-xl font-semibold mb-2">Регистрация</h1>
      <p className="text-sm text-slate-400 mb-4">
        Создайте аккаунт и получите свою первую комнату.
      </p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-xs mb-1 text-slate-300">Email</label>
          <input
            className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-xs mb-1 text-slate-300">Пароль</label>
          <input
            className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <div className="text-xs text-red-400">{error}</div>}
        <button
          type="submit"
          disabled={loading}
          className="w-full mt-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-60 rounded-lg py-2 text-sm font-medium"
        >
          {loading ? 'Создаём...' : 'Зарегистрироваться'}
        </button>
      </form>
      <div className="text-xs text-slate-400 mt-4">
        Уже есть аккаунт?{' '}
        <Link to="/login" className="text-sky-400 hover:underline">
          войдите
        </Link>
      </div>
    </div>
  )
}
