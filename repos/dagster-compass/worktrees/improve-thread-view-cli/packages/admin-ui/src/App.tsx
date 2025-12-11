import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AdminLayout } from './layouts/AdminLayout'
import { OrganizationsPage } from './pages/OrganizationsPage'
import { TokensPage } from './pages/TokensPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { ThreadsPage } from './pages/ThreadsPage'
import { ThreadDetailPage } from './pages/ThreadDetailPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AdminLayout />}>
          <Route index element={<Navigate to="/organizations" replace />} />
          <Route path="organizations" element={<OrganizationsPage />} />
          <Route path="tokens" element={<TokensPage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="threads" element={<ThreadsPage />} />
          <Route path="thread/:teamId/:channelId/:threadTs" element={<ThreadDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
