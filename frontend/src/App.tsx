import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { HowPage } from './pages/HowPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { MyWorksPage } from './pages/MyWorksPage'
import { Spinner } from './components/ui/Spinner'
import { ErrorBoundary } from './components/ui/ErrorBoundary'

const HomePage = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })))

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Routes>
        <Route
          path="/"
          element={
            <ErrorBoundary label="Головна сторінка">
              <Suspense fallback={<div className="flex justify-center py-24"><Spinner /></div>}>
                <HomePage />
              </Suspense>
            </ErrorBoundary>
          }
        />
        <Route path="/how" element={<HowPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/works" element={<MyWorksPage />} />
      </Routes>
    </div>
  )
}
