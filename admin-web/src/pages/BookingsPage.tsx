import { useQuery } from 'react-query'
import { bookingsApi, Booking } from '../api/bookings'
import { useField } from '../context/FieldContext'
import { useNavigate } from 'react-router-dom'

const STATUS_COLOR: Record<string, string> = {
  confirmed: '#c6f6d5', checked_in: '#bee3f8', cancelled: '#fed7d7'
}
const STATUS_TEXT: Record<string, string> = {
  confirmed: '#276749', checked_in: '#2b6cb0', cancelled: '#9b2c2c'
}

export default function BookingsPage() {
  const { fieldId, currentField } = useField()
  const nav = useNavigate()

  const { data: bookings = [], isLoading } = useQuery(
    ['bookings', fieldId],
    () => bookingsApi.listForField(fieldId!).then(r => r.data),
    { enabled: !!fieldId, refetchInterval: 30_000 }
  )

  const today = new Date().toISOString().slice(0, 10)
  const todayBookings = bookings
    .filter((b: Booking) => b.slot_date === today)
    .sort((a: Booking, b: Booking) => a.slot_start_time.localeCompare(b.slot_start_time))

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: '#1A1F3A', margin: 0 }}>Today's Bookings</h1>
          <p style={{ color: '#718096', margin: '4px 0 0' }}>{currentField?.name ?? ''} · {today}</p>
        </div>
        <button onClick={() => nav('/checkin')}
          style={{ padding: '10px 20px', background: '#7DC832', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>
          Check-In Scanner →
        </button>
      </div>

      {isLoading ? (
        <div style={{ color: '#718096' }}>Loading…</div>
      ) : todayBookings.length === 0 ? (
        <div style={{ color: '#718096', textAlign: 'center', padding: 48 }}>No bookings for today.</div>
      ) : (
        <div style={{ background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f7fafc' }}>
                {['Time', 'Reference', 'Status'].map(h => (
                  <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 12, fontWeight: 700, color: '#4a5568', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {todayBookings.map((b: Booking) => (
                <tr key={b.id} style={{ borderTop: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '12px 16px', fontSize: 14, color: '#1A1F3A', fontWeight: 500 }}>
                    {b.slot_start_time} – {b.slot_end_time}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 13, fontFamily: 'monospace', color: '#4a5568' }}>
                    {b.reference}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ background: STATUS_COLOR[b.status] ?? '#e2e8f0', color: STATUS_TEXT[b.status] ?? '#4a5568', padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>
                      {b.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
