import React from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './ui/AppLayout'
import { LoginPage } from './views/LoginPage'
import { RegisterPage } from './views/RegisterPage'
import { DashboardPage } from './views/DashboardPage'
import { RoomPage } from './views/RoomPage'
import { useAuth } from './auth/AuthContext'

const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { user, loading } = useAuth()
  if (loading) return <div className="text-slate-100 p-6">Загрузка...</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        )
      },
      {
        path: 'rooms/:code',
        element: (
          <ProtectedRoute>
            <RoomPage />
          </ProtectedRoute>
        )
      }
    ]
  }
])
