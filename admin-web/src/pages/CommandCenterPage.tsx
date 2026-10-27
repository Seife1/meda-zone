import { useQuery } from 'react-query'
import { fieldsApi } from '../api/fields'
import { useField } from '../context/FieldContext'
import { Link } from 'react-router-dom'

const GREEN = '#7DC832'
const NAVY = '#1A1F3A'

export default function CommandCenterPage() {
  const { fieldId, currentField } = useField()

  const { data: slots, isLoading } = useQuery(
    ['todaySlots', fieldId],
    () => fieldId ? fieldsApi.getTodaySlots(fieldId).then(r => r.data) : Promise.reject('No field'),
    { enabled: !!fieldId, refetchInterval: 30000 } // Poll every 30s for live updates
  )

  if (!fieldId) return <div style={{ padding: 32, color: '#718096' }}>No field selected</div>
  if (isLoading) return <div style={{ padding: 32, color: '#718096' }}>Loading today's schedule...</div>

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: NAVY, marginBottom: 8 }}>
        Today's Command Center
      </h1>
      <p style={{ color: '#718096', marginBottom: 24, fontSize: 14 }}>
        Live view for {currentField?.name ?? 'your field'}. Auto-updates every 30 seconds.
      </p>

      {slots && slots.length === 0 ? (
        <div style={{ background: '#fff', padding: 32, borderRadius: 12, textAlign: 'center', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <p style={{ margin: 0, color: '#718096' }}>No slots configured for today.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {slots?.map(slot => {
            const isAvailable = slot.status === 'open'
            const isBooked = slot.status === 'booked' || !!slot.booking_id
            
            return (
              <div key={slot.id} style={{
                background: '#fff',
                borderRadius: 12,
                padding: 20,
                borderLeft: `4px solid ${isAvailable ? GREEN : (isBooked ? NAVY : '#cbd5e0')}`,
                boxShadow: '0 1px 4px rgba(0,0,0,0.06)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <span style={{ fontSize: 18, fontWeight: 700, color: NAVY }}>
                    {slot.start_time.slice(0, 5)} - {slot.end_time.slice(0, 5)}
                  </span>
                  <span style={{
                    fontSize: 12, fontWeight: 600, padding: '4px 10px', borderRadius: 20,
                    background: isAvailable ? '#f0fff4' : (isBooked ? '#ebf4ff' : '#edf2f7'),
                    color: isAvailable ? '#276749' : (isBooked ? '#2b6cb0' : '#4a5568')
                  }}>
                    {isAvailable ? 'Available' : (isBooked ? 'Booked' : slot.status)}
                  </span>
                </div>
                
                {isBooked ? (
                  <div style={{ marginTop: 12 }}>
                    <p style={{ margin: '0 0 4px', fontSize: 13, color: '#718096' }}>Player</p>
                    <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: NAVY }}>{slot.player_name || 'Unknown'}</p>
                    <div style={{ marginTop: 16 }}>
                      <Link to="/checkin" style={{ display: 'inline-block', width: '100%', textAlign: 'center', padding: '10px 0', background: GREEN, color: '#fff', textDecoration: 'none', borderRadius: 8, fontWeight: 600 }}>
                        Go to Check-In
                      </Link>
                    </div>
                  </div>
                ) : isAvailable ? (
                  <div style={{ marginTop: 12, textAlign: 'center' }}>
                    <p style={{ margin: '0 0 16px', fontSize: 13, color: '#718096' }}>Slot is open for booking</p>
                    <Link to="/slots" style={{ display: 'inline-block', width: '100%', textAlign: 'center', padding: '10px 0', background: '#f7fafc', color: NAVY, border: '1px solid #e2e8f0', textDecoration: 'none', borderRadius: 8, fontWeight: 600 }}>
                      Manage Slot
                    </Link>
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
