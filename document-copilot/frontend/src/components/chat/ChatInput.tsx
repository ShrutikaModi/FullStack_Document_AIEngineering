import { useState, type FormEvent, type KeyboardEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export function ChatInput({
  disabled,
  onSend,
}: {
  disabled: boolean
  onSend: (text: string) => void
}) {
  const [text, setText] = useState('')

  function submit() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    submit()
  }

  // Enter sends; Shift+Enter adds a new line.
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex items-end gap-2">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask a question about the filings…"
        rows={2}
        className="min-h-0 resize-none"
      />
      <Button type="submit" disabled={disabled || !text.trim()}>
        Send
      </Button>
    </form>
  )
}
