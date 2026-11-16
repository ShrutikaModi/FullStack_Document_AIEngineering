import { DefaultChatTransport } from 'ai'

import { env } from '@/lib/env'
import { getAccessToken, supabase } from '@/lib/supabase'

// The chat hook makes its own requests, so it can't use the `api` client. This
// gives it the same behavior: backend address, bearer token, and sign-out on 401.
export function createChatTransport() {
  return new DefaultChatTransport({
    api: `${env.apiBaseUrl}/chat/stream`,
    // The backend expects { threadId, messages }; the SDK's chat `id` is the thread id.
    prepareSendMessagesRequest: async ({ id, messages }) => ({
      body: { threadId: id, messages },
      headers: { Authorization: `Bearer ${await getAccessToken()}` },
    }),
    fetch: async (input, init) => {
      const response = await fetch(input, init)
      if (response.status === 401) await supabase.auth.signOut()
      return response
    },
  })
}
