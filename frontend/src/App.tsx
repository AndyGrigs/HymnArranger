import { lazy, Suspense } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Navbar } from './components/Navbar'
import { Footer } from './components/Footer'
import { HowPage } from './pages/HowPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { MyWorksPage } from './pages/MyWorksPage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Spinner } from './components/ui/Spinner'
import { ErrorBoundary } from './components/ui/ErrorBoundary'

const HomePage = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })))

const variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -6 },
}

export default function App() {
  const location = useLocation()

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={location.pathname}
          variants={variants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="flex flex-1 flex-col"
        >
          <Routes location={location}>
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
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/works" element={<ProtectedRoute><MyWorksPage /></ProtectedRoute>} />
          </Routes>
          <Footer />
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
