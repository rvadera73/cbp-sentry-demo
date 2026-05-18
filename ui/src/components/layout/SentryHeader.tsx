import React from 'react'
import { useNavigate } from 'react-router-dom'

const SentryHeader: React.FC = () => {
  const navigate = useNavigate()

  return (
    <header className="bg-sentry-navy text-white shadow-md">
      <div className="px-6 py-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
        >
          <div className="w-8 h-8 bg-sentry-teal rounded flex items-center justify-center font-bold">
            S
          </div>
          <h1 className="text-2xl font-bold">Sentry CBP</h1>
        </button>
        <p className="text-sm text-sentry-light-blue mt-1">
          Customs and Border Protection Intelligent Resolution Engine
        </p>
      </div>
    </header>
  )
}

export default SentryHeader
