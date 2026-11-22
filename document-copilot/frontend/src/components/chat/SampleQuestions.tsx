import { Button } from '@/components/ui/button'
import type { DemoQuestion } from '@/lib/demo'

// The sample questions a demo account can open: one card each, naming the company and the
// kind of question.
export function SampleQuestions({
  questions,
  onPick,
}: {
  questions: DemoQuestion[]
  onPick: (text: string) => void
}) {
  if (questions.length === 0) return null
  return (
    <div className="w-full max-w-3xl">
      <p className="mb-2 text-sm font-medium">Try a sample question</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {questions.map((question) => (
          <Button
            key={question.id}
            variant="outline"
            onClick={() => onPick(question.text)}
            className="h-auto justify-start p-3 text-left font-normal whitespace-normal"
          >
            {question.text}
          </Button>
        ))}
      </div>
    </div>
  )
}
