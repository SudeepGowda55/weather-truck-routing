import { RISK_COLOR, RISK_LABEL, clock } from '../format'
import type { RouteOption } from '../types'

export default function CheckpointTable({ route }: { route: RouteOption }) {
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
                <td>{Math.round(c.mile)}</td>
                <td>{clock(c.eta)}</td>
                <td>{Math.round(c.wind_mph)} mph</td>
                <td>{c.rain_in_hr.toFixed(2)}"</td>
                <td>{c.snow_in_hr.toFixed(1)}"</td>
                <td>
                  <span className="pill" style={{ background: RISK_COLOR[c.risk] }}>
                    {RISK_LABEL[c.risk]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
