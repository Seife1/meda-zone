import { useState, FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { slotsApi, Slot } from '../api/slots'
import { useField } from '../context/FieldContext'
import toast from 'react-hot-toast'

const GREEN = '#7DC832'
const NAVY = '#1A1F3A'

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  available: { bg: '#c6f6d5', text: '#276749' },
  booked:    { bg: '#e2e8f0', text: '#4a5568' },
  closed:    { bg: '#fed7d7', text: '#9b2c2c' },
  pending:   { bg: '#fefcbf', text: '#975a16' },
}

export default function SlotsPage() {
  const { fieldId, currentField } = useField()
  const qc = useQueryClient()

  const [mode, setMode] = useState<'one-time'|'monthly'>('one-time')
  const [form, setForm] = useState({
    start_date: '', end_date: '', slot_duration_minutes: 60,
    open_time: '06:00', close_time: '22:00',
  })

  const { data: slots = [], isLoading } = useQuery(
    ['slots', fieldId], () => slotsApi.list(fieldId!).then(r => r.data),
    { enabled: !!fieldId }
  )

  const generate = useMutation(
    () => {
      const payload = {
        start_date: form.start_date,
        end_date: mode === 'one-time' ? form.start_date : form.end_date,
        open_time: form.open_time,
        close_time: form.close_time,
        slot_duration_minutes: Number(form.slot_duration_minutes) as 30 | 60 | 90
      }
      return slotsApi.generate(fieldId!, payload)
    },
    {
      onSuccess: (r) => {
        qc.invalidateQueries(['slots', fieldId])
        toast.success(`Created ${r.data.created_count} slots, skipped ${r.data.skipped_count}`)
      },
      onError: () => { toast.error('Failed to generate slots') },
    }
  )

  const closeSlot = useMutation(
    (slotId: string) => slotsApi.setStatus(slotId, 'closed'),
    { onSuccess: () => { qc.invalidateQueries(['slots', fieldId]); toast.success('Slot closed') } }
  )

  // Group by date
  const byDate: Record<string, Slot[]> = {}
  for (const s of slots) {
    if (!byDate[s.slot_date]) byDate[s.slot_date] = []
    byDate[s.slot_date].push(s)
  }

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: NAVY, marginBottom: 4 }}>Slot Management</h1>
      <p style={{ color: '#718096', marginBottom: 24 }}>{currentField?.name ?? 'No field selected'}</p>

      {/* Generate form */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <div style={{ display: 'flex', gap: 16, borderBottom: '1px solid #e2e8f0', paddingBottom: 12, marginBottom: 16 }}>
          <button 
            style={{ background: 'none', border: 'none', fontWeight: 700, fontSize: 15, cursor: 'pointer', color: mode === 'one-time' ? NAVY : '#a0aec0', borderBottom: mode === 'one-time' ? `2px solid ${GREEN}` : 'none', paddingBottom: 4 }}
            onClick={() => setMode('one-time')}>
            One-Time Game
          </button>
          <button 
            style={{ background: 'none', border: 'none', fontWeight: 700, fontSize: 15, cursor: 'pointer', color: mode === 'monthly' ? NAVY : '#a0aec0', borderBottom: mode === 'monthly' ? `2px solid ${GREEN}` : 'none', paddingBottom: 4 }}
            onClick={() => setMode('monthly')}>
            Monthly Schedule
          </button>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={lbl}>{mode === 'one-time' ? 'Date' : 'Start Date'}</label>
            <input style={inp} type="date" value={form.start_date} onChange={e => setForm(p => ({ ...p, start_date: e.target.value }))} />
          </div>
          {mode === 'monthly' && (
            <div>
              <label style={lbl}>End Date</label>
              <input style={inp} type="date" value={form.end_date} onChange={e => setForm(p => ({ ...p, end_date: e.target.value }))} />
            </div>
          )}
          <div>
            <label style={lbl}>Open Time</label>
            <input style={inp} type="time" value={form.open_time} onChange={e => setForm(p => ({ ...p, open_time: e.target.value }))} />
          </div>
          <div>
            <label style={lbl}>Close Time</label>
            <input style={inp} type="time" value={form.close_time} onChange={e => setForm(p => ({ ...p, close_time: e.target.value }))} />
          </div>
          <div>
            <label style={lbl}>Duration (min)</label>
            <select style={inp} value={form.slot_duration_minutes}
              onChange={e => setForm(p => ({ ...p, slot_duration_minutes: Number(e.target.value) }))}>
              {[30, 60, 90].map(m => <option key={m} value={m}>{m} min</option>)}
            </select>
          </div>
          <button
            style={{ padding: '10px 20px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}
            onClick={() => generate.mutate()} disabled={generate.isLoading}>
            {generate.isLoading ? 'Generating…' : 'Generate Slots'}
          </button>
        </div>
      </div>

      {/* Calendar */}
      {isLoading ? <div style={{ color: '#718096' }}>Loading slots…</div> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {Object.entries(byDate).map(([date, daySlots]) => (
            <div key={date} style={{ background: '#fff', borderRadius: 10, padding: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: NAVY, marginBottom: 10 }}>{date}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {daySlots.map(s => {
                  const c = STATUS_COLORS[s.status] ?? STATUS_COLORS.closed
                  return (
                    <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ background: c.bg, color: c.text, padding: '4px 10px', borderRadius: 16, fontSize: 12, fontWeight: 600 }}>
                        {s.start_time}–{s.end_time}
                      </span>
                      {s.status === 'available' && (
                        <button style={{ background: 'none', border: 'none', color: '#9b2c2c', cursor: 'pointer', fontSize: 11, padding: 0 }}
                          onClick={() => closeSlot.mutate(s.id)}>✕</button>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
          {Object.keys(byDate).length === 0 && (
            <div style={{ color: '#718096', textAlign: 'center', padding: 32 }}>No slots for this period. Generate some above.</div>
          )}
        </div>
      )}
    </div>
  )
}

const lbl: React.CSSProperties = { display: 'block', fontSize: 11, fontWeight: 600, color: '#4a5568', marginBottom: 3 }
const inp: React.CSSProperties = { padding: '8px 12px', borderRadius: 7, border: '1.5px solid #e2e8f0', fontSize: 13 }
