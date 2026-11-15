/// <reference types="vite/client" />

// Typed names for the variables read in src/lib/env.ts.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_SUPABASE_ANON_KEY?: string
}
