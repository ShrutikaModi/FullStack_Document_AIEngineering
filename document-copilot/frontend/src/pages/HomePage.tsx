import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

// Placeholder landing page so sign-in has somewhere to go. Replaced by the chat
// screen; the route guard comes with the "protected routes" step.
export default function HomePage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setEmail(data.session?.user.email ?? null))
  }, [])

  async function signOut() {
    await supabase.auth.signOut()
    navigate('/login')
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold">Document Copilot</h1>
      <p className="text-muted-foreground">{email ? `Signed in as ${email}` : 'Not signed in'}</p>
      <Button variant="outline" onClick={signOut}>
        Sign out
      </Button>
    </main>
  )
}
