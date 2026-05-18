import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import IngestPage from './pages/IngestPage'
import EntityResolutionPage from './pages/EntityResolutionPage'
import ScoringPage from './pages/ScoringPage'
import GraphPage from './pages/GraphPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/ingest" replace />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/entity-resolution" element={<EntityResolutionPage />} />
          <Route path="/scoring" element={<ScoringPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
