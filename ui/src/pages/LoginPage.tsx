import { useState } from 'react';
import { useRole } from '../context/RoleContext';
import { Shield } from 'lucide-react';
import '../styles/LoginPage.css';

export default function LoginPage() {
  const { setRole } = useRole();
  const [email, setEmail] = useState('');
  const [selectedRole, setSelectedRole] = useState<'cbp_officer' | 'analyst' | 'admin'>('cbp_officer');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      setRole(selectedRole);
      localStorage.setItem('user_email', email);
      localStorage.setItem('user_role', selectedRole);
      window.location.href = '/dashboard';
    }
  };

  return (
    <div className="login-page">
      {/* Government Banner */}
      <div className="gov-banner">
        An official website of the United States government
      </div>

      {/* Site Header */}
      <div className="login-header">
        <Shield size={32} className="login-header__icon" />
        <div className="login-header__text">
          <h1>SENTRY CBP</h1>
          <p>Illegal Transshipment Detection System</p>
        </div>
      </div>

      {/* Login Container */}
      <div className="login-container">
        <div className="login-card">
          <form onSubmit={handleSubmit}>
            {/* Email Field */}
            <div className="form-group">
              <label className="form-label" htmlFor="email">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@cbp.dhs.gov"
                required
              />
            </div>

            {/* Role Selection */}
            <fieldset className="form-group">
              <legend className="form-label">Access Level</legend>

              <div className="role-options">
                <div className="radio-option">
                  <input
                    id="role-officer"
                    type="radio"
                    name="role"
                    value="cbp_officer"
                    checked={selectedRole === 'cbp_officer'}
                    onChange={(e) => setSelectedRole(e.target.value as 'cbp_officer' | 'analyst' | 'admin')}
                  />
                  <label htmlFor="role-officer">
                    <span className="radio-title">CBP Officer</span>
                    <span className="radio-desc">Field investigation and case management</span>
                  </label>
                </div>

                <div className="radio-option">
                  <input
                    id="role-analyst"
                    type="radio"
                    name="role"
                    value="analyst"
                    checked={selectedRole === 'analyst'}
                    onChange={(e) => setSelectedRole(e.target.value as 'cbp_officer' | 'analyst' | 'admin')}
                  />
                  <label htmlFor="role-analyst">
                    <span className="radio-title">AI Analyst</span>
                    <span className="radio-desc">Scoring calibration and model monitoring</span>
                  </label>
                </div>

                <div className="radio-option">
                  <input
                    id="role-admin"
                    type="radio"
                    name="role"
                    value="admin"
                    checked={selectedRole === 'admin'}
                    onChange={(e) => setSelectedRole(e.target.value as 'cbp_officer' | 'analyst' | 'admin')}
                  />
                  <label htmlFor="role-admin">
                    <span className="radio-title">Administrator</span>
                    <span className="radio-desc">System administration and configuration</span>
                  </label>
                </div>
              </div>
            </fieldset>

            {/* Submit Button */}
            <button type="submit" className="usa-button usa-button--full">
              Sign In
            </button>
          </form>

          {/* Legal Disclaimer */}
          <div className="login-disclaimer">
            <p>
              Official use only. Unauthorized access is prohibited under 18 U.S.C. § 1030.
              <br />
              <small>(Demo: use any email to continue)</small>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
