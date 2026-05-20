import { useState } from 'react';
import { useRole } from '../context/RoleContext';
import { LogIn } from 'lucide-react';
import '../styles/LoginPage.css';

export default function LoginPage() {
  const { setRole } = useRole();
  const [email, setEmail] = useState('');
  const [showRoleSelect, setShowRoleSelect] = useState(false);
  const [selectedRole, setSelectedRole] = useState<'cbp_officer' | 'analyst' | 'admin'>('cbp_officer');

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      setShowRoleSelect(true);
    }
  };

  const handleRoleSelect = (role: 'cbp_officer' | 'analyst' | 'admin') => {
    setSelectedRole(role);
  };

  const handleLogin = () => {
    setRole(selectedRole);
    localStorage.setItem('user_email', email);
    localStorage.setItem('user_role', selectedRole);
    window.location.href = '/dashboard';
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <div className="login-header">
            <div className="logo">
              <LogIn size={40} />
            </div>
            <h1>SENTRY CBP</h1>
            <p className="subtitle">Illegal Transshipment Detection</p>
          </div>

          {!showRoleSelect ? (
            <form onSubmit={handleEmailSubmit} className="login-form">
              <div className="form-group">
                <label htmlFor="email">CBP Email Address</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@cbp.dhs.gov"
                  required
                />
              </div>
              <button type="submit" className="btn-next">
                Continue
              </button>
            </form>
          ) : (
            <div className="role-select">
              <h2>Select Your Role</h2>

              <div className="role-grid">
                <button
                  className={`role-card ${selectedRole === 'cbp_officer' ? 'selected' : ''}`}
                  onClick={() => handleRoleSelect('cbp_officer')}
                >
                  <div className="role-icon">📍</div>
                  <h3>CBP Officer</h3>
                  <p>Field officer investigating suspected transshipment cases</p>
                </button>

                <button
                  className={`role-card ${selectedRole === 'analyst' ? 'selected' : ''}`}
                  onClick={() => handleRoleSelect('analyst')}
                >
                  <div className="role-icon">📊</div>
                  <h3>AI Analyst</h3>
                  <p>System analyst calibrating risk models and monitoring performance</p>
                </button>

                <button
                  className={`role-card ${selectedRole === 'admin' ? 'selected' : ''}`}
                  onClick={() => handleRoleSelect('admin')}
                >
                  <div className="role-icon">⚙️</div>
                  <h3>Admin</h3>
                  <p>System administrator managing users and configuration</p>
                </button>
              </div>

              <button onClick={handleLogin} className="btn-login">
                Sign In as {selectedRole === 'cbp_officer' ? 'CBP Officer' : selectedRole === 'analyst' ? 'AI Analyst' : 'Admin'}
              </button>

              <button
                onClick={() => setShowRoleSelect(false)}
                className="btn-back"
              >
                Back
              </button>
            </div>
          )}

          <div className="login-footer">
            <p className="demo-note">Demo environment — use any email</p>
          </div>
        </div>
      </div>
    </div>
  );
}
