import { memo } from 'react'
import { clock } from '../format'
import type { RouteOption } from '../types'
import { RiskTag } from './Signs'

function CheckpointTable({ route }: { route: RouteOption }) {
  return (
    <section className="checkpoints">
      <h3>
        {route.name} checkpoints <span>{route.checkpoints.length} stops · weather at the truck's ETA</span>
      </h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Mile</th>
              <th>ETA</th>
              <th>Wind</th>
              <th>Rain</th>
              <th>Snow</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((c) => (
              <tr key={c.mile} title={c.reasons.join(', ')}>
                <td>
                  <span className="milepost">{Math.round(c.mile)}</span>
                </td>
                <td>{clock(c.eta)}</td>
                <td>{Math.round(c.wind_mph)} mph</td>
                <td>{c.rain_in_hr.toFixed(2)}"</td>
                <td>{c.snow_in_hr.toFixed(1)}"</td>
                <td>
                  <RiskTag risk={c.risk} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default memo(CheckpointTable)
