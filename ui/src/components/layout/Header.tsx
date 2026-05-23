import { useRole } from '../../context/RoleContext';
import { LogOut, Menu, Shield, Upload } from 'lucide-react';
import '../../styles/Header.css';

interface HeaderProps {
  title?: string;
  showNav?: boolean;
  showUploadButton?: boolean;
  onUploadClick?: () => void;
}

export default function Header({
  title = 'Sentry Intelligence Platform',
  showNav = true,
  showUploadButton = false,
  onUploadClick
}: HeaderProps) {
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
        {/* Logo & Branding */}
        <div className="header-left">
          <div className="header-logo">
            <div className="logo-shield">
              <Shield size={24} />
            </div>
            <div>
              <h1 className="header-title">Sentry</h1>
              <p className="header-subtitle">Intelligence Platform</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        {showNav && (
          <nav className="header-nav">
            {role === 'cbp_officer' && (
              <>
                {showUploadButton && (
                  <button
                    onClick={onUploadClick}
                    className="nav-link nav-action-button"
                    title="Upload Manifest"
                  >
                    <Upload size={16} />
                    Upload Manifest
                  </button>
                )}
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

        {/* User Info & Logout */}
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
