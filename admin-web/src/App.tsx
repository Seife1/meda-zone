import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { FieldProvider } from './context/FieldContext'
import { ThemeProvider } from './context/ThemeContext'
import Sidebar from './components/Sidebar'
import LoginPage from './pages/LoginPage'
import OverviewPage from './pages/OverviewPage'
import CommandCenterPage from './pages/CommandCenterPage'
import FieldsPage from './pages/FieldsPage'
import FieldCreatePage from './pages/FieldCreatePage'
import SlotsPage from './pages/SlotsPage'
import BookingsPage from './pages/BookingsPage'
import CheckInPage from './pages/CheckInPage'
import SubscriptionsPage from './pages/SubscriptionsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import UserManagementPage from './pages/UserManagementPage'

function ProtectedApp() {
  const { isAuthenticated, initializing, role } = useAuth()
  const location = useLocation()
  const isSuper = role === 'SUPER_ADMIN'

  if (initializing) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div style={{ width: 40, height: 40, border: '3px solid #7DC832', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
    </div>
  )

  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />

  return (
    <FieldProvider>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar />
        <main style={{ flex: 1, backgroundColor: '#f7fafc', overflow: 'auto' }}>
          <Routes>
            {isSuper && <Route path="/" element={<OverviewPage />} />}
            {!isSuper && <Route path="/" element={<CommandCenterPage />} />}
            {!isSuper && <Route path="/overview" element={<OverviewPage />} />}
            <Route path="/fields" element={<FieldsPage />} />
            <Route path="/fields/new" element={<FieldCreatePage />} />
            <Route path="/fields/:id/edit" element={<FieldCreatePage />} />
            <Route path="/slots" element={<SlotsPage />} />
            <Route path="/bookings" element={<BookingsPage />} />
            <Route path="/checkin" element={<CheckInPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            {isSuper && <Route path="/analytics" element={<AnalyticsPage />} />}
            {isSuper && <Route path="/users" element={<UserManagementPage />} />}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </FieldProvider>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<ProtectedApp />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}
