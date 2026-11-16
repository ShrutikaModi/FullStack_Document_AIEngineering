import { useAuth } from '@/components/auth/auth-context'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

// Placeholder landing page; replaced by the chat screen. Signing out ends the
// session and RequireAuth sends the user back to /login.
export default function HomePage() {
  const { session } = useAuth()

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold">Document Copilot</h1>
      <p className="text-muted-foreground">Signed in as {session?.user.email}</p>
      <Button variant="outline" onClick={() => supabase.auth.signOut()}>
        Sign out
      </Button>
    </main>
  )
}
