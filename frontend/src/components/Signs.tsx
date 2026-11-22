import { RISK_COLOR, RISK_LABEL } from '../format'
import type { RiskKey } from '../types'

// interstate-style shield with the route letter
export function Shield({ letter, color }: { letter: string; color: string }) {
  return (
    <svg className="shield" viewBox="0 0 40 44" width="34" height="38" aria-hidden="true">
      <path d="M20 2c6 3 11 3 17 1 2 9 2 17-1 24-3 7-9 11-16 15C13 38 7 34 4 27 1 20 1 12 3 3c6 2 11 2 17-1z" fill="#fff" />
      <path d="M20 4.5c5.5 2.6 10 2.7 15 1.2 1.6 8 1.4 15-1.2 21-2.7 6.2-8 9.8-13.8 13.2C14.2 36.5 8.9 32.9 6.2 26.7 3.6 20.7 3.4 13.7 5 5.7c5 1.5 9.5 1.4 15-1.2z" fill={color} />
      <path d="M5.6 13h28.8c.1-2.5-.1-4.9-.6-7.3-4.8 1.3-9.2 1.2-13.8-1.1-4.6 2.3-9 2.4-13.8 1.1-.5 2.4-.7 4.8-.6 7.3z" fill="#c8102e" />
      <text x="20" y="31" textAnchor="middle" fontSize="15" fontWeight="800" fill="#fff" fontFamily="Overpass, sans-serif">
        {letter}
      </text>
    </svg>
  )
}

// road warning diamond, one per risk level
export function Diamond({ risk, size = 14 }: { risk: RiskKey; size?: number }) {
  return (
    <span className="diamond" style={{ width: size, height: size, background: RISK_COLOR[risk] }} title={RISK_LABEL[risk]} aria-hidden="true">
      {risk === 'no_travel' && <i />}
    </span>
  )
}

export function RiskTag({ risk }: { risk: RiskKey }) {
  return (
    <span className={`risk-tag ${risk}`}>
      <Diamond risk={risk} size={10} />
      {RISK_LABEL[risk]}
    </span>
  )
}
