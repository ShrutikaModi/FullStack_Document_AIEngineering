import type { Session } from '@supabase/supabase-js'
import { useEffect, useState, type ReactNode } from 'react'

import { AuthContext } from '@/components/auth/auth-context'
import { supabase } from '@/lib/supabase'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fires once with the saved session (INITIAL_SESSION), then on every sign-in,
    // sign-out, token refresh, and sign-out from another tab.
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      setLoading(false)
    })
    return () => data.subscription.unsubscribe()
  }, [])

  return <AuthContext value={{ session, loading }}>{children}</AuthContext>
}
