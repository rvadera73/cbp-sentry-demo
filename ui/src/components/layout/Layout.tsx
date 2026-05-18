import React from 'react'
import { Outlet } from 'react-router-dom'
import SentryHeader from './SentryHeader'
import DemoStepper from './DemoStepper'

const Layout: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen bg-sentry-light-blue">
      <SentryHeader />
      <div className="flex-1 flex">
        <DemoStepper />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
