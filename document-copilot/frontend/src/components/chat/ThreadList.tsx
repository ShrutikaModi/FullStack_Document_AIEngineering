import { Link } from 'react-router-dom'

import { useAuth } from '@/components/auth/auth-context'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import type { Thread } from '@/lib/threads'
import { cn } from '@/lib/utils'

export function ThreadList({
  threads,
  activeId,
  error,
  onNewChat,
}: {
  threads: Thread[]
  activeId: string | undefined
  error: string | null
  onNewChat: () => void
}) {
  const { session } = useAuth()

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r">
      <div className="p-3">
        <Button className="w-full" onClick={onNewChat}>
          New chat
        </Button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2">
        {error && <p className="p-2 text-sm text-destructive">{error}</p>}
        {threads.length === 0 && !error && (
          <p className="p-2 text-sm text-muted-foreground">No conversations yet</p>
        )}
        {threads.map((thread) => (
          <Link
            key={thread.id}
            to={`/chat/${thread.id}`}
            className={cn(
              'block truncate rounded-md px-3 py-2 text-sm hover:bg-muted',
              thread.id === activeId && 'bg-muted font-medium',
            )}
          >
            {thread.title ?? 'New conversation'}
          </Link>
        ))}
      </nav>
      <div className="border-t p-3 text-sm">
        <p className="truncate text-muted-foreground">{session?.user.email}</p>
        <Button
          variant="outline"
          size="sm"
          className="mt-2 w-full"
          onClick={() => supabase.auth.signOut()}
        >
          Sign out
        </Button>
      </div>
    </aside>
  )
}
