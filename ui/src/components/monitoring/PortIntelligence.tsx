import React, { useMemo } from 'react'
import { TrendingUp } from 'lucide-react'

interface PortIntelligenceProps {
  shipments: any[]
}

const PortIntelligence: React.FC<PortIntelligenceProps> = ({ shipments }) => {
  const portStats = useMemo(() => {
    const ports: { [key: string]: { name: string; total: number; high: number; medium: number; low: number } } = {
      US: { name: 'Newark, US', total: 0, high: 0, medium: 0, low: 0 },
      CA: { name: 'Toronto, CA', total: 0, high: 0, medium: 0, low: 0 },
    }

    shipments.forEach((s) => {
      const portCode = s.consignee_country
      if (ports[portCode]) {
        ports[portCode].total++
        if (s.risk_score >= 70) ports[portCode].high++
        else if (s.risk_score >= 50) ports[portCode].medium++
        else ports[portCode].low++
      }
    })

    return Object.values(ports).filter((p) => p.total > 0)
  }, [shipments])

  return (
    <div className="p-6 bg-sentry-navy/80">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4 text-sentry-teal" />
        <p className="text-xs text-sentry-light-blue uppercase font-semibold">Port Intelligence</p>
      </div>

      <div className="space-y-4">
        {portStats.map((port) => (
          <div key={port.name} className="p-3 rounded-lg bg-sentry-navy border border-sentry-teal/10">
            <div className="flex justify-between items-start mb-2">
              <div>
                <p className="font-semibold text-white text-sm">{port.name}</p>
                <p className="text-xs text-sentry-light-blue">{port.total} shipments</p>
              </div>
              <span className="px-2 py-1 rounded bg-sentry-teal/20 text-sentry-teal text-xs font-semibold">
                {port.total}
              </span>
            </div>

            {/* Mini bars */}
            <div className="flex gap-1 text-xs">
              {port.high > 0 && (
                <div
                  title={`${port.high} HIGH`}
                  className="flex-1 h-1.5 bg-red-500 rounded opacity-80"
                  style={{ flex: port.high }}
                ></div>
              )}
              {port.medium > 0 && (
                <div
                  title={`${port.medium} MEDIUM`}
                  className="flex-1 h-1.5 bg-yellow-500 rounded opacity-80"
                  style={{ flex: port.medium }}
                ></div>
              )}
              {port.low > 0 && (
                <div
                  title={`${port.low} LOW`}
                  className="flex-1 h-1.5 bg-green-500 rounded opacity-80"
                  style={{ flex: port.low }}
                ></div>
              )}
            </div>

            {/* Legend */}
            <div className="flex gap-3 text-xs mt-2 text-sentry-light-blue">
              {port.high > 0 && <span>🔴 {port.high} HIGH</span>}
              {port.medium > 0 && <span>🟠 {port.medium} MED</span>}
              {port.low > 0 && <span>🟢 {port.low} LOW</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PortIntelligence
