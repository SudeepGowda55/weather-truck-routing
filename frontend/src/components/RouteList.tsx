import { memo } from 'react'
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS, ROUTE_COLOR, clock, duration, miles } from '../format'
import type { Plan } from '../types'

interface Props {
  plan: Plan
  selected: number
  onSelect: (id: number) => void
}

function RouteList({ plan, selected, onSelect }: Props) {
  const ordered = [...plan.routes].sort((a, b) => a.rank - b.rank)
  return (
    <section className="routes">
      <p className="reason">
        <strong>Why {plan.routes[plan.recommended].name}:</strong> {plan.reason}
      </p>
      {ordered.map((r) => {
        const total = r.distance_mi || 1
        const m = r.summary.miles_by_risk
        return (
          <button
            key={r.id}
            className={`route-card${r.id === selected ? ' selected' : ''}`}
            onClick={() => onSelect(r.id)}
            style={{ '--route': ROUTE_COLOR[r.id % ROUTE_COLOR.length] } as React.CSSProperties}
          >
            <div className="route-head">
              <span className="swatch" />
              <span className="route-name">{r.name}</span>
              <span className="via">{r.via}</span>
              {r.recommended && <span className="badge">Recommended</span>}
            </div>
            <div className="route-stats">
              <span>{miles(r.distance_mi)}</span>
              <span>{duration(r.duration_s)}</span>
              <span>arrive {clock(r.arrival)}</span>
            </div>
            <div className="riskbar" aria-label="Miles at each risk level">
              {RISK_LEVELS.map((k) =>
                m[k] > 0 ? <span key={k} style={{ flexGrow: m[k] / total, background: RISK_COLOR[k] }} title={`${RISK_LABEL[k]}: ${miles(m[k])}`} /> : null,
              )}
            </div>
            <div className="route-risk">
              <span>Severe {miles(m.severe)}</span>
              <span>High {miles(m.high)}</span>
              <span>Avg risk {r.summary.average_risk.toFixed(2)}</span>
            </div>
            {m.no_travel > 0 && <p className="warn">{miles(m.no_travel)} at No Travel for this load</p>}
          </button>
        )
      })}
    </section>
  )
}

export default memo(RouteList)
