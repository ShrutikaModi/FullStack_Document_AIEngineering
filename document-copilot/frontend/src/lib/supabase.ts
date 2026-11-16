import { createClient } from '@supabase/supabase-js'

import { env } from '@/lib/env'

// Browser client: anon key only. The session is stored by supabase-js and
// refreshed automatically; read the token through this client, never pass it
// around as a prop.
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey)

// The current login token, or null when signed out. The only place tokens are read.
export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
