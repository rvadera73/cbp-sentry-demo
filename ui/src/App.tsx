import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useRole } from './context/RoleContext'
import { WorkflowProvider } from './context/WorkflowContext'
import Header from './components/layout/Header'
import LoginPage from './pages/LoginPage'
import ManifestRiskQueuePage from './pages/ManifestRiskQueuePage'
import CaseViewerPage from './pages/CaseViewerPage'
import ScoringCalibrationPage from './pages/ScoringCalibrationPage'
import NotFoundPage from './pages/NotFoundPage'

function AnalystDashboard() {
  return (
    <div style={{ padding: '2rem' }}>
      <Header title="System Metrics" />
      <div style={{ marginTop: '2rem' }}>
        <h2>AI Analyst Dashboard</h2>
        <p>System layers, API status, model performance metrics</p>
        <p style={{ color: '#999', fontSize: '0.9rem' }}>Coming soon</p>
      </div>
    </div>
  )
}

function AdminDashboard() {
  return (
    <div style={{ padding: '2rem' }}>
      <Header title="System Administration" />
      <div style={{ marginTop: '2rem' }}>
        <h2>Admin Dashboard</h2>
        <p>User management, system configuration, audit logs</p>
        <p style={{ color: '#999', fontSize: '0.9rem' }}>Coming soon</p>
      </div>
    </div>
  )
}

interface ProtectedRouteProps {
  element: React.ReactNode;
  allowedRoles?: ('cbp_officer' | 'analyst' | 'admin')[];
}

function ProtectedRoute({ element, allowedRoles }: ProtectedRouteProps) {
  const { role } = useRole();
  const userEmail = localStorage.getItem('user_email');

  if (!userEmail) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <NotFoundPage />
  }

  return element
}

function App() {
  return (
    <WorkflowProvider>
      <Router>
        <Routes>
          {/* Auth Routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes - Role-Based Dashboards */}
          <Route
            path="/dashboard"
            element={<ManifestRiskQueuePage />}
          />

          <Route
            path="/dashboard/analyst"
            element={<ProtectedRoute element={<AnalystDashboard />} allowedRoles={['analyst']} />}
          />

          <Route
            path="/admin"
            element={<ProtectedRoute element={<AdminDashboard />} allowedRoles={['admin']} />}
          />

          {/* Case Viewer - Accessible by CBP Officers & Analysts */}
          <Route
            path="/cases/:shipmentId"
            element={<ProtectedRoute element={<CaseViewerPage />} allowedRoles={['cbp_officer', 'analyst']} />}
          />

          {/* Scoring Calibration - Analyst only */}
          <Route
            path="/scoring-calibration"
            element={<ProtectedRoute element={<ScoringCalibrationPage />} allowedRoles={['analyst']} />}
          />

          {/* Root redirect to dashboard or login */}
          <Route path="/" element={<RootRedirect />} />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Router>
    </WorkflowProvider>
  )
}

function RootRedirect() {
  const userEmail = localStorage.getItem('user_email');
  const userRole = localStorage.getItem('user_role') as 'cbp_officer' | 'analyst' | 'admin' | null;

  if (!userEmail) {
    return <Navigate to="/login" replace />
  }

  if (userRole === 'cbp_officer') {
    return <Navigate to="/dashboard" replace />
  } else if (userRole === 'analyst') {
    return <Navigate to="/dashboard/analyst" replace />
  } else if (userRole === 'admin') {
    return <Navigate to="/admin" replace />
  }

  return <Navigate to="/login" replace />
}

export default App
