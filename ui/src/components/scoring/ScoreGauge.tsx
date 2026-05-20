import React, { useEffect, useState } from 'react'

interface ScoreGaugeProps {
  score: number
}

/**
 * ScoreGauge — SVG radial gauge with animated needle
 * Shows 0-100 score with risk level label
 */
const ScoreGauge: React.FC<ScoreGaugeProps> = ({ score }) => {
  const [animatedScore, setAnimatedScore] = useState(0)

  // Animate score from 0 to final value
  useEffect(() => {
    let animationFrame: number
    const startTime = Date.now()
    const duration = 1000 // 1 second animation

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      setAnimatedScore(Math.round(score * progress))

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate)
      }
    }

    animationFrame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationFrame)
  }, [score])

  const getRiskLevel = (s: number): string => {
    if (s >= 80) return 'CRITICAL'
    if (s >= 60) return 'HIGH'
    if (s >= 40) return 'MEDIUM'
    return 'LOW'
  }

  const getRiskColor = (s: number): string => {
    if (s >= 80) return '#DC2626'
    if (s >= 60) return '#F97316'
    if (s >= 40) return '#EAB308'
    return '#22C55E'
  }

  const getRiskBgColor = (s: number): string => {
    if (s >= 80) return 'bg-red-50'
    if (s >= 60) return 'bg-orange-50'
    if (s >= 40) return 'bg-yellow-50'
    return 'bg-green-50'
  }

  const riskLevel = getRiskLevel(animatedScore)
  const riskColor = getRiskColor(animatedScore)

  // Calculate needle rotation (0-100 maps to 0-180 degrees, centered at bottom)
  const needleRotation = (animatedScore / 100) * 180 - 90

  return (
    <div className="flex flex-col items-center gap-6">
      {/* SVG Gauge */}
      <svg viewBox="0 0 240 180" className="w-80 h-auto" xmlns="http://www.w3.org/2000/svg">
        {/* Background arc */}
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22C55E" />
            <stop offset="33%" stopColor="#EAB308" />
            <stop offset="66%" stopColor="#F97316" />
            <stop offset="100%" stopColor="#DC2626" />
          </linearGradient>
        </defs>

        {/* Outer arc (gradient) */}
        <path
          d="M 30 150 A 100 100 0 0 1 210 150"
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="20"
          strokeLinecap="round"
        />

        {/* Inner arc (background) */}
        <path
          d="M 40 150 A 90 90 0 0 1 200 150"
          fill="none"
          stroke="#E5E7EB"
          strokeWidth="2"
        />

        {/* Scale markers */}
        {[0, 25, 50, 75, 100].map((marker) => {
          const angle = (marker / 100) * 180 - 90
          const rad = (angle * Math.PI) / 180
          const x1 = 120 + 95 * Math.cos(rad)
          const y1 = 150 + 95 * Math.sin(rad)
          const x2 = 120 + 85 * Math.cos(rad)
          const y2 = 150 + 85 * Math.sin(rad)
          return (
            <line
              key={marker}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#6B7280"
              strokeWidth="2"
              strokeLinecap="round"
            />
          )
        })}

        {/* Needle pivot circle */}
        <circle cx="120" cy="150" r="8" fill="#1F2937" />

        {/* Needle (animated) */}
        <line
          x1="120"
          y1="150"
          x2="120"
          y2="50"
          stroke={riskColor}
          strokeWidth="4"
          strokeLinecap="round"
          style={{
            transformOrigin: '120px 150px',
            transform: `rotate(${needleRotation}deg)`,
            transition: 'transform 0.05s ease-out',
          }}
        />

        {/* Score text at center */}
        <text x="120" y="160" textAnchor="middle" fontSize="24" fontWeight="bold" fill={riskColor}>
          {animatedScore}
        </text>
        <text x="120" y="177" textAnchor="middle" fontSize="12" fill="#6B7280">
          / 100
        </text>
      </svg>

      {/* Risk Level and Details */}
      <div className={`w-full p-4 rounded-lg text-center ${getRiskBgColor(animatedScore)}`}>
        <p className="text-sm text-gray-600 mb-1">Risk Level</p>
        <p className="text-2xl font-bold" style={{ color: riskColor }}>
          {riskLevel}
        </p>
        <p className="text-xs text-gray-500 mt-2">
          {riskLevel === 'CRITICAL'
            ? 'Immediate examination recommended'
            : riskLevel === 'HIGH'
              ? 'Likely examination candidate'
              : riskLevel === 'MEDIUM'
                ? 'Routine screening recommended'
                : 'Low risk, routine clearance'}
        </p>
      </div>
    </div>
  )
}

export default ScoreGauge
