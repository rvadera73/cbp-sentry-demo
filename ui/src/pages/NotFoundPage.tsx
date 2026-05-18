import React from 'react'
import { useNavigate } from 'react-router-dom'

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-6xl font-bold text-sentry-navy mb-4">404</h1>
      <p className="text-2xl text-sentry-slate mb-8">Page Not Found</p>
      <button
        onClick={() => navigate('/')}
        className="px-6 py-2 bg-sentry-teal text-white rounded font-semibold hover:bg-sentry-dark-teal"
      >
        Return Home
      </button>
    </div>
  )
}

export default NotFoundPage
