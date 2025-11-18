import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import Layout from '@/components/layout/Layout'
import HomePage from '@/pages/HomePage'
import SessionPage from '@/pages/SessionPage'
import HistoryPage from '@/pages/HistoryPage'
import NotFoundPage from '@/pages/NotFoundPage'

function App() {
  return (
    <div className="min-h-screen bg-background">
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/session/:sessionId" element={<SessionPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Layout>
      <Toaster />
    </div>
  )
}

export default App