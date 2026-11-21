const GENERIC = 'Something went wrong sending your message. Please try again.'
const NETWORK = 'Could not reach the server. Check your connection and try again.'

// The text to show when a chat request fails. The cases come from how the chat library
// builds its errors:
//  - a failed fetch (server down, offline, CORS) is a TypeError;
//  - an HTTP error (for example 422) carries the raw response body, which is JSON;
//  - an error the backend sent inside the stream ("blocked by the content filter",
//    "could not produce a fully sourced answer") carries our own plain sentence.
export function friendlyError(error: Error): string {
  if (error instanceof TypeError) return NETWORK
  const message = error.message.trim()
  if (message === '' || message.startsWith('{')) return GENERIC
  return message
}
