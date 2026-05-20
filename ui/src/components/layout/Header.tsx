import { useRole } from '../../context/RoleContext';
import { LogOut, Menu } from 'lucide-react';
import '../../styles/Header.css';

interface HeaderProps {
  title?: string;
  showNav?: boolean;
}

export default function Header({ title = 'SENTRY CBP', showNav = true }: HeaderProps) {
  const { role, setRole } = useRole();
  const userEmail = localStorage.getItem('user_email') || 'user@cbp.dhs.gov';

  const getRoleLabel = () => {
    switch (role) {
      case 'cbp_officer':
        return 'CBP Officer';
      case 'analyst':
        return 'AI Analyst';
      case 'admin':
        return 'Administrator';
      default:
        return 'User';
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_role');
    setRole('cbp_officer');
    window.location.href = '/login';
  };

  return (
    <header className="sentry-header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="header-title">{title}</h1>
          <p className="header-subtitle">Intelligence Platform</p>
        </div>

        {showNav && (
          <nav className="header-nav">
            {role === 'cbp_officer' && (
              <>
                <a href="/dashboard" className="nav-link">
                  Cases
                </a>
                <a href="/upload" className="nav-link">
                  Upload Manifest
                </a>
              </>
            )}
            {role === 'analyst' && (
              <>
                <a href="/dashboard/analyst" className="nav-link">
                  System Metrics
                </a>
                <a href="/scoring-calibration" className="nav-link">
                  Model Calibration
                </a>
              </>
            )}
            {role === 'admin' && (
              <>
                <a href="/admin" className="nav-link">
                  System Admin
                </a>
                <a href="/admin/users" className="nav-link">
                  Users
                </a>
              </>
            )}
          </nav>
        )}

        <div className="header-right">
          <div className="user-info">
            <span className="user-email">{userEmail}</span>
            <span className="user-role">{getRoleLabel()}</span>
          </div>
          <button onClick={handleLogout} className="btn-logout" title="Logout">
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
