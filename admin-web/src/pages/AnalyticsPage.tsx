import { useQuery } from 'react-query'
import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts'
import { adminApi } from '../api/admin'
import { subscriptionsApi } from '../api/subscriptions'

const GREEN = '#7DC832'
const NAVY = '#1A1F3A'
const COLORS = [GREEN, '#1A5C2A', '#2b6cb0', '#805ad5', '#d69e2e']

export default function AnalyticsPage() {
  const { data: analytics } = useQuery('analytics', () => adminApi.getAnalytics().then(r => r.data), { staleTime: 300_000 })
  const { data: subStats } = useQuery('subStats', () => subscriptionsApi.stats().then(r => r.data), { staleTime: 300_000 })

  const tierData = subStats ? Object.entries(subStats.by_tier as Record<string, number>).map(([name, value]) => ({
    name: name.replace('_', ' '), value,
  })) : []

  const fieldData = (subStats?.by_field ?? []) as Array<{ field_name: string; active_count: number }>

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: NAVY, marginBottom: 24 }}>Analytics</h1>

      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        {/* Subscriptions by tier */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', flex: '0 0 340px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, color: NAVY }}>Active Subscriptions by Tier</h3>
          {tierData.length === 0 ? <p style={{ color: '#718096' }}>No data</p> : (
            <PieChart width={280} height={220}>
              <Pie data={tierData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {tierData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          )}
        </div>

        {/* Subscriptions by field */}
        <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', flex: 1, minWidth: 300 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, color: NAVY }}>Active Subscriptions by Field</h3>
          {fieldData.length === 0 ? <p style={{ color: '#718096' }}>No data</p> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={fieldData} margin={{ left: 0, right: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="field_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="active_count" fill={GREEN} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Table */}
      {fieldData.length > 0 && (
        <div style={{ background: '#fff', borderRadius: 12, marginTop: 24, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f7fafc' }}>
                <th style={th}>Field</th>
                <th style={th}>Active Subscriptions</th>
              </tr>
            </thead>
            <tbody>
              {fieldData.map((row, i) => (
                <tr key={i} style={{ borderTop: '1px solid #e2e8f0' }}>
                  <td style={td}>{row.field_name}</td>
                  <td style={{ ...td, fontWeight: 700, color: GREEN }}>{row.active_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: '11px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#4a5568', textTransform: 'uppercase' }
const td: React.CSSProperties = { padding: '11px 16px', fontSize: 14, color: '#1A1F3A' }
