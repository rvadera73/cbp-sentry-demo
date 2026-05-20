import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../context/WorkflowContext'
import { AlertTriangle, BarChart3, Shield, Upload, Zap, Lock, CheckCircle, MapPin } from 'lucide-react'

const DashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const { state } = useWorkflow()

  return (
    <div className="min-h-screen bg-gradient-to-br from-sentry-navy via-blue-900 to-sentry-dark-teal">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-sentry-teal rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-sentry-orange rounded-full blur-3xl"></div>
        </div>

        <div className="relative z-10 px-8 py-16 text-white">
          <div className="max-w-6xl mx-auto">
            <div className="flex justify-between items-start mb-12">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Shield className="w-12 h-12 text-sentry-teal animate-pulse" />
                  <h1 className="text-5xl font-black tracking-tight">
                    SENTRY<span className="text-sentry-teal">•CBP</span>
                  </h1>
                </div>
                <p className="text-xl text-blue-100 max-w-2xl leading-relaxed font-semibold">
                  AI-Powered Customs Compliance & Transshipment Detection
                  <br />
                  <span className="text-sentry-teal">Real-time intelligence for mission-critical enforcement</span>
                </p>
              </div>
              <button
                onClick={() => navigate('/ingest')}
                className="flex items-center gap-3 px-8 py-4 bg-sentry-teal hover:bg-sentry-orange text-sentry-navy font-black rounded-xl shadow-2xl transition-all transform hover:scale-105 text-lg"
              >
                <Upload className="w-6 h-6" />
                Upload Manifest
              </button>
            </div>

            {/* Key Metrics Row */}
            <div className="grid grid-cols-4 gap-4 mt-12">
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-xl p-6 text-center hover:bg-white/15 transition">
                <p className="text-blue-200 text-sm font-black uppercase tracking-wider">Detection Accuracy</p>
                <p className="text-4xl font-black text-sentry-teal mt-3">97.3%</p>
              </div>
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-xl p-6 text-center hover:bg-white/15 transition">
                <p className="text-blue-200 text-sm font-black uppercase tracking-wider">Cases Analyzed</p>
                <p className="text-4xl font-black text-sentry-orange mt-3">12,847</p>
              </div>
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-xl p-6 text-center hover:bg-white/15 transition">
                <p className="text-blue-200 text-sm font-black uppercase tracking-wider">Fraud Prevented</p>
                <p className="text-4xl font-black text-green-400 mt-3">$847M</p>
              </div>
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-xl p-6 text-center hover:bg-white/15 transition">
                <p className="text-blue-200 text-sm font-black uppercase tracking-wider">Avg Processing</p>
                <p className="text-4xl font-black text-sentry-teal mt-3">2.3s</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Three Horizons Intelligence */}
      <div className="relative z-10 px-8 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="mb-12">
            <h2 className="text-4xl font-black text-white flex items-center gap-3">
              <Zap className="w-10 h-10 text-sentry-teal" />
              Three Horizons Intelligence
            </h2>
            <p className="text-blue-200 mt-3 text-lg">Real-time corridor, pre-manifest, and full assessment scoring</p>
          </div>

          <div className="grid grid-cols-3 gap-6">
            {/* H1 Corridor Risk */}
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-r from-sentry-navy to-sentry-dark-teal rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition duration-300"></div>
              <div className="relative bg-white/95 backdrop-blur rounded-2xl p-8 border border-white/30 h-full hover:shadow-2xl transition">
                <div className="flex items-center gap-3 mb-8">
                  <div className="w-14 h-14 bg-sentry-navy/10 rounded-xl flex items-center justify-center">
                    <Shield className="w-7 h-7 text-sentry-navy" />
                  </div>
                  <div>
                    <p className="text-xs font-black text-sentry-navy uppercase tracking-wider">Horizon 1</p>
                    <h3 className="text-xl font-black text-sentry-navy">Corridor Risk</h3>
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="border-b-2 pb-6">
                    <p className="text-xs text-gray-600 font-black uppercase tracking-wider">Route Analysis</p>
                    <p className="text-3xl font-black text-sentry-navy mt-3">Vietnam → USA</p>
                  </div>

                  <div className="bg-gradient-to-r from-sentry-orange/10 to-red-100 rounded-xl p-4 border border-sentry-orange/30">
                    <p className="text-xs text-gray-700 font-black uppercase tracking-wider">AD/CVD Rate</p>
                    <p className="text-3xl font-black text-sentry-orange mt-2">374.15%</p>
                    <p className="text-xs text-gray-600 mt-2 font-semibold">HTS 7604.10 Aluminum Extrusions</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-4 border-t-2">
                    <div className="bg-red-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 font-black">RISK LEVEL</p>
                      <p className="font-black text-red-600 text-lg mt-2">🔴 CRITICAL</p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 font-black">PRIOR CASES</p>
                      <p className="font-black text-sentry-navy text-lg mt-2">24 Filed</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* H2 Pre-Intelligence */}
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-r from-sentry-orange to-red-600 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition duration-300"></div>
              <div className="relative bg-white/95 backdrop-blur rounded-2xl p-8 border border-white/30 h-full hover:shadow-2xl transition">
                <div className="flex items-center gap-3 mb-8">
                  <div className="w-14 h-14 bg-sentry-orange/10 rounded-xl flex items-center justify-center">
                    <AlertTriangle className="w-7 h-7 text-sentry-orange" />
                  </div>
                  <div>
                    <p className="text-xs font-black text-sentry-orange uppercase tracking-wider">Horizon 2</p>
                    <h3 className="text-xl font-black text-sentry-navy">Pre-Intelligence</h3>
                  </div>
                </div>

                <div className="space-y-5">
                  <div className="bg-red-50 rounded-xl p-4 border-2 border-red-300">
                    <p className="text-xs font-black text-red-700 uppercase tracking-wider">⚠️ ISF Element 9 Mismatch</p>
                    <p className="text-lg font-black text-sentry-navy mt-3">China ≠ Vietnam</p>
                    <p className="text-xs text-gray-700 mt-2 font-semibold">Container stuffing location contradicts declared origin</p>
                  </div>

                  <div className="bg-orange-50 rounded-xl p-4 border-2 border-orange-300">
                    <p className="text-xs text-gray-700 font-black uppercase tracking-wider">AIS Dwell Anomaly</p>
                    <p className="text-2xl font-black text-sentry-orange mt-2">11.2 days</p>
                    <p className="text-xs text-gray-700 mt-2 font-semibold">5.3× baseline | 99th percentile</p>
                  </div>

                  <div className="bg-yellow-50 rounded-lg p-3 border-2 border-yellow-300">
                    <p className="text-xs text-gray-700 font-black">STATUS</p>
                    <p className="font-black text-orange-600 text-lg mt-2">🟠 HIGH ALERT</p>
                  </div>
                </div>
              </div>
            </div>

            {/* H3 Full Assessment */}
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-r from-sentry-teal to-green-500 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition duration-300"></div>
              <div className="relative bg-gradient-to-br from-sentry-navy to-sentry-dark-teal rounded-2xl p-8 border border-white/30 h-full text-white hover:shadow-2xl transition">
                <div className="flex items-center gap-3 mb-8">
                  <div className="w-14 h-14 bg-white/10 rounded-xl flex items-center justify-center">
                    <BarChart3 className="w-7 h-7 text-sentry-teal" />
                  </div>
                  <div>
                    <p className="text-xs font-black text-sentry-teal uppercase tracking-wider">Horizon 3</p>
                    <h3 className="text-xl font-black">Full Assessment</h3>
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="border-b-2 border-white/20 pb-6">
                    <p className="text-xs text-blue-200 font-black uppercase tracking-wider">ML Risk Score</p>
                    <div className="flex items-baseline gap-3 mt-3">
                      <p className="text-5xl font-black text-sentry-teal">91</p>
                      <p className="text-2xl text-blue-200">/100</p>
                    </div>
                  </div>

                  <div className="bg-white/10 rounded-xl p-4 backdrop-blur border border-white/20">
                    <p className="text-xs text-sentry-teal font-black uppercase tracking-wider">Recommendation</p>
                    <p className="text-2xl font-black text-sentry-orange mt-3">🚨 EXAMINE</p>
                    <p className="text-xs text-blue-100 mt-2 font-semibold">Confidence: 96.7%</p>
                  </div>

                  <div className="bg-green-500/20 rounded-xl p-4 border border-green-400/50">
                    <p className="text-xs text-green-100 font-black uppercase tracking-wider">Financial Impact</p>
                    <p className="text-3xl font-black text-green-300 mt-3">$2.1M</p>
                    <p className="text-xs text-green-100 mt-2 font-semibold">Estimated Revenue at Risk</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Example Section */}
      <div className="relative z-10 px-8 py-16 border-t border-white/10">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-black text-white mb-8 flex items-center gap-3">
            <CheckCircle className="w-8 h-8 text-green-400" />
            Live Demo Case: Greenfield Aluminum
          </h2>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white/10 backdrop-blur rounded-xl p-6 border border-white/20">
              <p className="text-blue-200 text-sm font-black uppercase mb-4">Shipment Details</p>
              <div className="space-y-3 text-white">
                <div className="flex justify-between"><span className="text-blue-200">Shipper</span><span className="font-semibold">Greenfield Industrial Trading (VN)</span></div>
                <div className="flex justify-between"><span className="text-blue-200">Destination</span><span className="font-semibold">SunPath Energy (New Jersey, USA)</span></div>
                <div className="flex justify-between"><span className="text-blue-200">Commodity</span><span className="font-semibold">Aluminum Extrusions (HTS 7604.10)</span></div>
                <div className="flex justify-between"><span className="text-blue-200">Declared Value</span><span className="font-semibold text-green-400">$847,500</span></div>
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur rounded-xl p-6 border border-white/20">
              <p className="text-blue-200 text-sm font-black uppercase mb-4">Risk Signals</p>
              <div className="space-y-2 text-white">
                <div className="flex items-center gap-2"><span className="text-sentry-orange">●</span><span>Owner-linked to Guangdong manufacturer (98% Senzing confidence)</span></div>
                <div className="flex items-center gap-2"><span className="text-sentry-orange">●</span><span>Container stuffed in China (ISF Element 9 mismatch)</span></div>
                <div className="flex items-center gap-2"><span className="text-sentry-orange">●</span><span>11.2-day Guangzhou port dwell (5.3× baseline anomaly)</span></div>
                <div className="flex items-center gap-2"><span className="text-sentry-orange">●</span><span>AD/CVD duty 374.15% on aluminum from China</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative z-10 px-8 py-12">
        <div className="max-w-6xl mx-auto grid grid-cols-2 gap-6">
          <div className="bg-gradient-to-r from-sentry-teal/20 to-green-500/20 backdrop-blur rounded-2xl p-12 text-center border border-white/20 hover:border-white/40 transition">
            <Lock className="w-12 h-12 text-sentry-teal mx-auto mb-6" />
            <h2 className="text-3xl font-black text-white mb-4">
              {state.manifestId ? '✓ Manifest Loaded' : 'Start Mission'}
            </h2>
            <p className="text-blue-100 text-lg mb-8 max-w-2xl mx-auto font-semibold">
              {state.manifestId
                ? 'Proceed to entity resolution and risk scoring.'
                : 'Upload a CBP manifest to begin comprehensive customs compliance analysis in seconds.'}
            </p>
            <button
              onClick={() => navigate(state.manifestId ? '/entity-resolution' : '/ingest')}
              className="px-12 py-4 bg-sentry-teal hover:bg-sentry-orange text-sentry-navy font-black rounded-xl shadow-2xl transition-all transform hover:scale-105 text-lg"
            >
              {state.manifestId ? 'Analyze Entities →' : 'Upload Manifest →'}
            </button>
          </div>

          <div className="bg-gradient-to-r from-orange-500/20 to-red-500/20 backdrop-blur rounded-2xl p-12 text-center border border-white/20 hover:border-white/40 transition">
            <MapPin className="w-12 h-12 text-sentry-orange mx-auto mb-6" />
            <h2 className="text-3xl font-black text-white mb-4">Explore Network</h2>
            <p className="text-blue-100 text-lg mb-8 max-w-2xl mx-auto font-semibold">
              Monitor 15+ active shipments with real-time risk assessment and geographic visualization.
            </p>
            <button
              onClick={() => navigate('/shipments')}
              className="px-12 py-4 bg-sentry-orange hover:bg-sentry-teal text-white font-black rounded-xl shadow-2xl transition-all transform hover:scale-105 text-lg"
            >
              View Shipments Hub →
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10 px-8 py-8 border-t border-white/10">
        <div className="max-w-6xl mx-auto text-center text-blue-300 text-xs font-semibold">
          <p>SENTRY CBP Intelligence Platform • Powered by Senzing + Advanced ML • Classification: Demo</p>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
