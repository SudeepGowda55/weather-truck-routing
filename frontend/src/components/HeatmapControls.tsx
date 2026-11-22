import { useEffect } from 'react'
import { clock } from '../format'

export type Metric = 'risk' | 'wind' | 'precip'

interface Props {
  hours: string[]
  hour: number
  onHour: (h: number) => void
  metric: Metric
  onMetric: (m: Metric) => void
  playing: boolean
  onPlaying: (p: boolean) => void
}

const METRICS: { key: Metric; label: string }[] = [
  { key: 'risk', label: 'Risk' },
  { key: 'wind', label: 'Wind' },
  { key: 'precip', label: 'Rain + snow' },
]

export default function HeatmapControls({ hours, hour, onHour, metric, onMetric, playing, onPlaying }: Props) {
  const last = hours.length - 1

  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => onHour(hour >= last ? 0 : hour + 1), 350)
    return () => window.clearInterval(id)
  }, [playing, hour, last, onHour])

  return (
    <div className="heat-controls">
      <div className="heat-top">
        <button className="play" onClick={() => onPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play forecast'}>
          {playing ? '❚❚' : '▶'}
        </button>
        <div className="heat-time">
          <strong>+{hour} h</strong> <span>{clock(hours[hour])}</span>
        </div>
        <div className="segmented small" role="radiogroup" aria-label="Heatmap layer">
          {METRICS.map((m) => (
            <button key={m.key} role="radio" aria-checked={metric === m.key} className={metric === m.key ? 'on' : ''} onClick={() => onMetric(m.key)}>
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <input
        type="range"
        min={0}
        max={last}
        step={1}
        value={hour}
        onChange={(e) => onHour(Number(e.target.value))}
        aria-label="Forecast hour after departure"
      />
      <div className="ticks">
        {[0, 12, 24, 36, 48].map((h) => (
          <span key={h}>{h} h</span>
        ))}
      </div>
    </div>
  )
}
