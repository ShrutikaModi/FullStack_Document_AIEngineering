import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/components/auth/auth-context'

// Wraps private routes: waits for the saved session, then lets the user in or
// sends them to /login.
export function RequireAuth() {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </main>
    )
  }
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}
