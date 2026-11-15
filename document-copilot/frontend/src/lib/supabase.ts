import { createClient } from '@supabase/supabase-js'

import { env } from '@/lib/env'

// Browser client: anon key only. The session is stored by supabase-js and
// refreshed automatically; read the token through this client, never pass it
// around as a prop.
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey)
