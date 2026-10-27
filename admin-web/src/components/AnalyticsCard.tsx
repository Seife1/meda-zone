interface Props {
  color: 'blue' | 'green' | 'red' | 'orange' | 'purple'
  icon: string
  label: string
  value: number | string
  delta: string | null
}

export default function AnalyticsCard({ color, icon, label, value, delta }: Props) {
  return (
    <div className={`stat-card ${color}`}>
      <div className={`stat-icon ${color}`}>{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {delta && <div className={`stat-delta ${delta.startsWith('+') ? 'up' : 'down'}`}>{delta}</div>}
    </div>
  )
}
