import React from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login')
  }

  const isAuthPage = location.pathname === '/login' || location.pathname === '/register'

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold">Тихие комнаты</span>
          <span className="text-xs text-slate-400">beta</span>
        </div>
        {!isAuthPage && (
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/dashboard" className="hover:text-sky-400">
              Панель
            </Link>
            {user && (
              <>
                <span className="text-slate-400 text-xs hidden sm:inline">
                  {user.email} · комнат: {user.max_rooms}
                </span>
                <button
                  onClick={onLogout}
                  className="text-xs px-3 py-1 rounded-full border border-slate-700 hover:border-sky-500"
                >
                  Выйти
                </button>
              </>
            )}
          </nav>
        )}
      </header>
      <main className="flex-1 flex justify-center">
        <div className="w-full max-w-4xl px-4 py-6">
          <Outlet />
        </div>
      </main>
      <footer className="text-xs text-slate-500 px-4 py-3 border-t border-slate-900">
        Тихие цифровые комнаты · приватные встречи до 20 человек
      </footer>
    </div>
  )
}
