import { useParams } from 'react-router-dom'

import { ChatThread } from '@/components/chat/ChatThread'
import { useChatLayout } from '@/components/chat/chat-layout-context'
import { SampleQuestions } from '@/components/chat/SampleQuestions'
import { Button } from '@/components/ui/button'

// /chat shows a start screen; /chat/:threadId shows one conversation.
export default function ChatPage() {
  const { threadId } = useParams()
  const { startNewChat, demo } = useChatLayout()

  if (threadId) return <ChatThread key={threadId} threadId={threadId} />

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-4">
      <h1 className="text-2xl font-semibold">Document Copilot</h1>
      <p className="max-w-2xl text-center text-muted-foreground">
        Ask questions about the annual reports (10-K filings) of Apple, Amazon, Alphabet, Meta,
        Microsoft, NVIDIA, JPMorgan Chase and Tesla from fiscal 2021 to 2025.
      </p>
      <Button onClick={() => void startNewChat()}>New chat</Button>
      {demo?.demo && (
        <SampleQuestions questions={demo.questions} onPick={(text) => void startNewChat(text)} />
      )}
    </div>
  )
}
