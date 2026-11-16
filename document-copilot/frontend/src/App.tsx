import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '@/components/auth/AuthProvider'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { ChatLayout } from '@/components/chat/ChatLayout'
import ChatPage from '@/pages/ChatPage'
import LoginPage from '@/pages/LoginPage'
import SignUpPage from '@/pages/SignUpPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route element={<ChatLayout />}>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:threadId" element={<ChatPage />} />
            </Route>
          </Route>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
