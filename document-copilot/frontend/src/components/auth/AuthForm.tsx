import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, ApiError } from '@/lib/api'
import { supabase } from '@/lib/supabase'

type Mode = 'login' | 'signup'

const COPY = {
  login: {
    title: 'Sign in',
    description: 'Use your Driftwood email address.',
    submit: 'Sign in',
    switchText: "Don't have an account?",
    switchLink: 'Sign up',
    switchTo: '/signup',
  },
  signup: {
    title: 'Create account',
    description: 'Use your Driftwood email address.',
    submit: 'Sign up',
    switchText: 'Already have an account?',
    switchLink: 'Sign in',
    switchTo: '/login',
  },
} as const

export function AuthForm({ mode }: { mode: Mode }) {
  const copy = COPY[mode]
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  // /me creates the analyst's profile row on first sign-in.
  async function finish() {
    await api.get('/me')
    navigate('/')
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const email = String(form.get('email')).trim()
    const password = String(form.get('password'))

    setError(null)
    setNotice(null)
    setPending(true)
    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) return setError(error.message)
        await finish()
      } else {
        const { data, error } = await supabase.auth.signUp({ email, password })
        if (error) return setError(error.message)
        if (data.session) await finish()
        else setNotice('Check your email to confirm your account, then sign in.')
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong. Please try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{copy.title}</CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" name="email" type="email" autoComplete="email" required />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={mode === 'signup' ? 8 : undefined}
                required
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            {notice && <p className="text-sm text-muted-foreground">{notice}</p>}
            <Button type="submit" disabled={pending}>
              {pending ? 'Please wait…' : copy.submit}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              {copy.switchText}{' '}
              <Link to={copy.switchTo} className="underline">
                {copy.switchLink}
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
