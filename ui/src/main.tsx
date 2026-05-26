import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { RoleProvider } from './context/RoleContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <RoleProvider>
    <App />
  </RoleProvider>,
)
