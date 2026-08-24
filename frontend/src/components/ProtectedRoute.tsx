import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Spinner } from './ui/Spinner'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}
