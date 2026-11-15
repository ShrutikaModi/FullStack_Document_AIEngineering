// Single place that reads and validates environment variables. Everything else
// imports `env` from here; never read import.meta.env directly elsewhere.
// Only public, browser-safe values belong here: no service-role key, no database URL.

function required(name: keyof ImportMetaEnv): string {
  const value = import.meta.env[name]?.trim()
  if (!value) {
    throw new Error(`Missing ${name}. Set it in frontend/.env (see .env.example).`)
  }
  if (value.includes('your-')) {
    throw new Error(`${name} still has the placeholder from .env.example.`)
  }
  return value
}

function requiredUrl(name: keyof ImportMetaEnv): string {
  const value = required(name)
  try {
    new URL(value)
  } catch {
    throw new Error(`${name} is not a valid URL: ${value}`)
  }
  return value
}

export const env = {
  // Trailing slash removed so callers can append "/path" safely.
  apiBaseUrl: requiredUrl('VITE_API_BASE_URL').replace(/\/+$/, ''),
  supabaseUrl: requiredUrl('VITE_SUPABASE_URL'),
  supabaseAnonKey: required('VITE_SUPABASE_ANON_KEY'),
}
