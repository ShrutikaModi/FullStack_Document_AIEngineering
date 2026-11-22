import { ExternalLink } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { Notice } from '@/lib/demo'

// The message shown after a sample answer, and when someone types their own question. The
// wording comes from the backend so it is written in one place.
export function ContactDialog({
  notice,
  open,
  onOpenChange,
}: {
  notice: Notice
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{notice.title}</DialogTitle>
          <DialogDescription>{notice.message}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Got it</DialogClose>
          <Button
            render={<a href={notice.contact_url} target="_blank" rel="noopener noreferrer" />}
          >
            Contact Shrutika Modi on LinkedIn
            <ExternalLink data-icon="inline-end" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
