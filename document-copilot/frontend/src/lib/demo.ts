import { api } from '@/lib/api'

// One of the recorded sample questions anyone can open.
export type DemoQuestion = { id: string; company: string; kind: string; text: string }

export type Notice = { title: string; message: string; contact_url: string }

// `demo` is true for accounts that can only use the samples. The backend decides this from the
// verified login and enforces it; the screen only uses it to show the samples and the notice.
export type DemoInfo = { demo: boolean; questions: DemoQuestion[]; notice: Notice | null }

export const getDemoInfo = () => api.get<DemoInfo>('/demo')

// Same matching as the backend: ignore letter case and extra spaces.
const normalize = (text: string) => text.trim().replace(/\s+/g, ' ').toLowerCase()

export function isSampleQuestion(text: string, questions: DemoQuestion[]): boolean {
  const wanted = normalize(text)
  return questions.some((question) => normalize(question.text) === wanted)
}
