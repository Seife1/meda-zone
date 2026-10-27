import { useQuery } from 'react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { adminApi } from '../api/admin'
import { fieldsApi } from '../api/fields'
import { useAuth } from '../hooks/useAuth'
import { useField } from '../context/FieldContext'

const GREEN = '#7DC832'
const NAVY = '#1A1F3A'

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: '20px 24px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)', flex: 1, minWidth: 160 }}>
      <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: '#718096', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</p>
      <p style={{ margin: '8px 0 4px', fontSize: 28, fontWeight: 800, color: NAVY }}>{value}</p>
      {sub && <p style={{ margin: 0, fontSize: 12, color: '#a0aec0' }}>{sub}</p>}
    </div>
  )
}

export default function OverviewPage() {
  const { role } = useAuth()
  const { fieldId } = useField()
  const isSuper = role === 'SUPER_ADMIN'

  // Fetch admin analytics or field analytics depending on role
  const { data: adminData, isLoading: adminLoading } = useQuery(
    'adminAnalytics', 
    () => adminApi.getAnalytics().then(r => r.data), 
    { enabled: isSuper, staleTime: 300_000 }
  )

  const { data: fieldData, isLoading: fieldLoading } = useQuery(
    ['fieldAnalytics', fieldId], 
    () => fieldId ? fieldsApi.getAnalytics(fieldId).then(r => r.data) : Promise.reject('No field'), 
    { enabled: !isSuper && !!fieldId, staleTime: 300_000 }
  )

  const isLoading = isSuper ? adminLoading : fieldLoading
  const data = isSuper ? adminData : fieldData

  if (isLoading) return <div style={{ padding: 32, color: '#718096' }}>Loading analytics…</div>
  
  if (!isSuper && !fieldId) return <div style={{ padding: 32, color: '#718096' }}>No field selected</div>

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: NAVY, marginBottom: 24 }}>
        {isSuper ? 'Platform Overview' : 'Field Analytics'}
      </h1>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 32 }}>
        {isSuper && <StatCard label="Active Fields" value={(data as any)?.total_active_fields ?? 0} />}
        <StatCard label="Bookings (30d)" value={data?.total_bookings_30d ?? 0} />
        {!isSuper && <StatCard label="Revenue (30d)" value={`ETB ${Number((data as any)?.total_revenue_30d ?? 0).toLocaleString()}`} />}
      </div>

      <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <h3 style={{ margin: '0 0 20px', fontSize: 15, color: NAVY }}>Daily Bookings — Last 30 Days</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data?.daily_bookings ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            <Tooltip formatter={(v: number) => [v, 'Bookings']} labelFormatter={l => `Date: ${l}`} />
            <Line type="monotone" dataKey="count" stroke={GREEN} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
