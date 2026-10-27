import { useState, FormEvent } from 'react'
import { bookingsApi } from '../api/bookings'
import toast from 'react-hot-toast'

const GREEN = '#7DC832'
const DARK_BG = '#0f172a'

export default function CheckInPage() {
  const [reference, setReference] = useState('')
  const [booking, setBooking] = useState<any>(null)
  const [warning, setWarning] = useState('')
  const [loading, setLoading] = useState(false)

  const lookup = async (e: FormEvent) => {
    e.preventDefault()
    if (!reference.trim()) return
    setLoading(true)
    setBooking(null)
    setWarning('')
    try {
      const r = await bookingsApi.verify(reference.trim())
      setBooking(r.data)
    } catch {
      toast.error('Booking not found')
    } finally { setLoading(false) }
  }

  const checkIn = async () => {
    if (!booking) return
    setLoading(true)
    try {
      const r = await bookingsApi.checkIn(booking.booking_id)
      if (r.data.warning) setWarning(r.data.warning)
      setBooking({ ...booking, status: 'checked_in' })
      toast.success('Check-in recorded ✅')
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message || 'Check-in failed')
    } finally { setLoading(false) }
  }

  const statusColor = (s: string) => s === 'confirmed' ? '#c6f6d5' : s === 'checked_in' ? '#bee3f8' : '#fed7d7'
  const statusText = (s: string) => s === 'confirmed' ? '#276749' : s === 'checked_in' ? '#2b6cb0' : '#9b2c2c'

  return (
    <div style={{ padding: '40px 20px', minHeight: '100vh', backgroundColor: DARK_BG, color: '#f1f5f9', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <h1 style={{ fontWeight: 800, fontStyle: 'italic', fontSize: 32, marginBottom: 40, letterSpacing: 1 }}>Check-In Kiosk</h1>

      <form onSubmit={lookup} style={{ display: 'flex', flexDirection: 'column', gap: 16, width: '100%', maxWidth: 500, marginBottom: 32 }}>
        <input
          style={{ padding: '20px', borderRadius: 16, border: '2px solid #334155', backgroundColor: '#1e293b', color: '#fff', fontSize: 24, fontFamily: 'monospace', letterSpacing: 3, textAlign: 'center' }}
          placeholder="ENTER REF CODE"
          value={reference}
          onChange={e => setReference(e.target.value.toUpperCase())}
          autoFocus
        />
        <button type="submit" disabled={loading}
          style={{ padding: '20px', background: GREEN, color: '#000', border: 'none', borderRadius: 16, fontWeight: 800, fontSize: 20, cursor: 'pointer', textTransform: 'uppercase' }}>
          {loading ? 'Searching…' : 'Look Up Booking'}
        </button>
      </form>

      {booking && (
        <div style={{ background: '#1e293b', borderRadius: 20, padding: 32, width: '100%', maxWidth: 500, border: '1px solid #334155', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <span style={{ fontFamily: 'monospace', fontWeight: 800, fontSize: 24, color: '#e2e8f0' }}>{booking.reference}</span>
            <span style={{ background: statusColor(booking.status), color: statusText(booking.status), padding: '6px 16px', borderRadius: 20, fontSize: 14, fontWeight: 800, textTransform: 'uppercase' }}>
              {booking.status.replace('_', ' ')}
            </span>
          </div>
          
          <div style={{ backgroundColor: '#0f172a', padding: 20, borderRadius: 12, marginBottom: 24 }}>
            <p style={row}>Date <strong style={strong}>{booking.slot_date}</strong></p>
            <p style={row}>Time <strong style={strong}>{booking.start_time.slice(0,5)} – {booking.end_time.slice(0,5)}</strong></p>
          </div>

          {warning && (
            <div style={{ background: '#451a1a', border: '1px solid #991b1b', borderRadius: 12, padding: '16px', marginBottom: 24, fontSize: 16, color: '#fca5a5', fontWeight: 600 }}>
              ⚠️ {warning}
            </div>
          )}

          {booking.status === 'confirmed' && (
            <button onClick={checkIn} disabled={loading}
              style={{ width: '100%', padding: '24px', background: GREEN, color: '#000', border: 'none', borderRadius: 16, fontWeight: 900, fontSize: 22, cursor: 'pointer', textTransform: 'uppercase', letterSpacing: 1 }}>
              {loading ? 'Processing…' : 'CONFIRM ARRIVAL'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const row: React.CSSProperties = { margin: '0 0 12px 0', fontSize: 16, color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }
const strong: React.CSSProperties = { color: '#f8fafc', fontSize: 18 }
