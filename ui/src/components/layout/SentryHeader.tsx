import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { MapPin } from 'lucide-react'

const SentryHeader: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="bg-sentry-navy text-white shadow-md">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 bg-sentry-teal rounded flex items-center justify-center font-bold">
              S
            </div>
            <div>
              <h1 className="text-2xl font-bold">Sentry CBP</h1>
              <p className="text-xs text-sentry-light-blue">
                Customs and Border Protection Intelligent Resolution Engine
              </p>
            </div>
          </button>

          <nav className="flex gap-6">
            <button
              onClick={() => navigate('/')}
              className={`text-sm font-semibold transition-colors ${
                isActive('/') ? 'text-sentry-teal' : 'text-sentry-light-blue hover:text-white'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => navigate('/shipments')}
              className={`flex items-center gap-2 text-sm font-semibold transition-colors ${
                isActive('/shipments') ? 'text-sentry-teal' : 'text-sentry-light-blue hover:text-white'
              }`}
            >
              <MapPin className="w-4 h-4" />
              Shipments Hub
            </button>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default SentryHeader
