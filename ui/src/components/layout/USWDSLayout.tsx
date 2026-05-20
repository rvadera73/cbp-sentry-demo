import { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRole } from '../../context/RoleContext';
import RoleSelector from '../common/RoleSelector';
import './USWDSLayout.css';

interface Props {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

export default function USWDSLayout({ children, title, subtitle }: Props) {
  const navigate = useNavigate();
  const { role } = useRole();
  const userEmail = localStorage.getItem('user_email') || 'user@cbp.dhs.gov';

  return (
    <div className="uswds-layout">
      {/* USWDS Header */}
      <header className="usa-header usa-header--basic">
        <div className="usa-navbar">
          <div className="usa-logo">
            <em className="usa-logo__text">
              <a href="/" title="Home" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
                SENTRY CBP
              </a>
            </em>
          </div>
        </div>
        <nav className="usa-nav">
          <button className="usa-nav__close">
            <img src="/assets/img/close.svg" alt="close" />
          </button>
          <ul className="usa-nav__primary usa-accordion" style={{ display: 'flex', alignItems: 'center' }}>
            <li className="usa-nav__primary-item">
              <a className="usa-nav__link" href="/" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
                <span>Dashboard</span>
              </a>
            </li>
            {(role === 'cbp_officer' || role === 'analyst') && (
              <li className="usa-nav__primary-item">
                <a className="usa-nav__link" href="/cases" onClick={(e) => { e.preventDefault(); navigate('/cases'); }}>
                  <span>Cases</span>
                </a>
              </li>
            )}
            {(role === 'analyst' || role === 'admin') && (
              <li className="usa-nav__primary-item">
                <a className="usa-nav__link" href="/ingest" onClick={(e) => { e.preventDefault(); navigate('/ingest'); }}>
                  <span>Upload Manifest</span>
                </a>
              </li>
            )}
            {role === 'admin' && (
              <li className="usa-nav__primary-item">
                <a className="usa-nav__link" href="/settings" onClick={(e) => { e.preventDefault(); navigate('/settings'); }}>
                  <span>Admin Settings</span>
                </a>
              </li>
            )}
            <li style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '1rem', paddingRight: '1rem' }}>
              <RoleSelector />
              <span style={{ fontSize: '0.875rem', color: '#666', whiteSpace: 'nowrap' }}>
                {userEmail}
              </span>
            </li>
          </ul>
        </nav>
      </header>

      {/* Page Title */}
      {title && (
        <div className="page-title-section">
          <div className="usa-container">
            <h1 className="page-title">{title}</h1>
            {subtitle && <p className="page-subtitle">{subtitle}</p>}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="main-content usa-container">
        {children}
      </main>

      {/* USWDS Footer */}
      <footer className="usa-footer usa-footer--slim">
        <div className="usa-footer__section usa-footer__section--slim">
          <div className="usa-footer__primary-section">
            <div className="usa-footer__primary-content usa-grid usa-grid--full-width">
              <div className="usa-footer__logo">
                <em className="usa-logo__text">
                  U.S. Customs and Border Protection
                </em>
              </div>
              <nav className="usa-footer__nav">
                <a href="https://cbp.gov" target="_blank" rel="noreferrer">CBP.gov</a>
              </nav>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
