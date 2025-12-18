import React, { useState } from 'react'
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  useParams,
  useLocation,
} from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { DashboardPage } from './views/DashboardPage'
import { RoomPage } from './views/RoomPage'
import { LoginPage } from './views/LoginPage'
import { RegisterPage } from './views/RegisterPage'
import { AdminNodesPage } from './views/AdminNodesPage'

// укажи свой админский email, если делаешь админку, иначе можно оставить как есть
const ADMIN_EMAIL = 'you@example.com'

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth()
  if (loading) return <div className="text-slate-200 p-4">Загрузка...</div>
  if (!user) return <Navigate to="/auth/login" replace />
  return <>{children}</>
}

const RequireAdmin: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth()
  if (loading) return <div className="text-slate-200 p-4">Загрузка...</div>
  if (!user) return <Navigate to="/auth/login" replace />
  if (user.email !== ADMIN_EMAIL) {
    return <div className="text-slate-300 text-sm">Страница не найдена</div>
  }
  return <>{children}</>
}

// Обёртка для гостевого входа по ссылке /g/:code
const GuestRoomWrapper: React.FC = () => {
  const { code } = useParams<{ code: string }>()
  const location = useLocation()
  const [name, setName] = useState('')
  const [confirmed, setConfirmed] = useState(false)

  const searchParams = new URLSearchParams(location.search)
  const nodeParam = searchParams.get('node') || ''

  if (!code || !nodeParam) {
    return (
      <div className="max-w-md mx-auto mt-10 bg-slate-900 border border-slate-800 rounded-2xl p-4 text-sm">
        <div className="text-slate-200 mb-2">Ссылка недействительна</div>
        <div className="text-slate-500 text-xs">
          Похоже, эта ссылка приглашения повреждена или устарела. Попросите ведущего
          отправить новую ссылку.
        </div>
      </div>
    )
  }

  if (!confirmed) {
    return (
      <div className="max-w-md mx-auto mt-10 bg-slate-900 border border-slate-800 rounded-2xl p-4 text-sm">
        <h1 className="text-lg font-semibold mb-2 text-slate-100">
          Вход в тихую комнату
        </h1>
        <p className="text-xs text-slate-400 mb-3">
          Для подключения к комнате укажите, как вас называть. Можно просто имя или имя +
          первая буква фамилии.
        </p>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Ваше имя</label>
            <input
              className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500 text-slate-100"
              placeholder="Например: Мария, Алекс, Анна К."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <button
            disabled={!name.trim()}
            onClick={() => setConfirmed(true)}
            className="w-full px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-sm font-medium disabled:opacity-50"
          >
            Войти в комнату
          </button>
          <p className="text-[11px] text-slate-500">
            Регистрация не требуется. Ведущий увидит только указанное вами имя.
          </p>
        </div>
      </div>
    )
  }

  // После подтверждения имени — открываем ту же RoomPage,
  // но передаём ей адрес ноды и имя гостя
  return (
    <RoomPage
      forceNodeBaseUrl={nodeParam}
      guestDisplayNameOverride={name.trim()}
    />
  )
}

const AppLayout: React.FC = () => {
  const { user, logout } = useAuth()
  const isAdmin = user?.email === ADMIN_EMAIL

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <Link to="/dashboard" className="text-sm font-semibold text-slate-100">
              Quiet Rooms
            </Link>
            <span className="text-[11px] text-slate-500">тихие цифровые комнаты</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            {user && (
              <>
                <Link
                  to="/dashboard"
                  className="text-slate-300 hover:text-sky-300"
                >
                  Панель
                </Link>
                {isAdmin && (
                  <Link
                    to="/admin/nodes"
                    className="text-slate-300 hover:text-sky-300"
                  >
                    Админка
                  </Link>
                )}
                <span className="text-slate-500 hidden sm:inline">
                  {user.email}
                </span>
                <button
                  onClick={logout}
                  className="px-3 py-1 rounded-full border border-slate-700 hover:border-red-500 hover:text-red-300"
                >
                  Выйти
                </button>
              </>
            )}
            {!user && (
              <>
                <Link
                  to="/auth/login"
                  className="text-slate-300 hover:text-sky-300"
                >
                  Войти
                </Link>
                <Link
                  to="/auth/register"
                  className="text-slate-400 hover:text-sky-300"
                >
                  Регистрация
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto py-6 px-4">
        <Routes>
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          {/* Преподаватель и авторизованные — через этот маршрут */}
          <Route
            path="/rooms/:code"
            element={
              <RequireAuth>
                <RoomPage />
              </RequireAuth>
            }
          />
          {/* Гости — сюда по ссылке без регистрации */}
          <Route path="/g/:code" element={<GuestRoomWrapper />} />
          <Route
            path="/admin/nodes"
            element={
              <RequireAdmin>
                <AdminNodesPage />
              </RequireAdmin>
            }
          />
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register" element={<RegisterPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<div className="text-slate-300">Страница не найдена</div>} />
        </Routes>
      </main>
    </div>
  )
}

export const App: React.FC = () => (
  <BrowserRouter>
    <AuthProvider>
      <AppLayout />
    </AuthProvider>
  </BrowserRouter>
)
