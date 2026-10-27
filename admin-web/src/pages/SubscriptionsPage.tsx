import { useState, FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { subscriptionsApi, SubscriptionCreate } from '../api/subscriptions'
import { useField } from '../context/FieldContext'
import toast from 'react-hot-toast'

const GREEN = '#7DC832'
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const TIERS = ['1_month', '2_months', '3_months'] as const

export default function SubscriptionsPage() {
  const { fieldId, currentField } = useField()
  const qc = useQueryClient()
  const [form, setForm] = useState<SubscriptionCreate>({
    player_id: '', field_id: fieldId ?? '',
    recurring_days: [], session_start_time: '16:00',
    session_duration_hours: 2, tier: '1_month',
  })

  const { data: subs = [], isLoading } = useQuery(
    ['subscriptions', fieldId],
    () => subscriptionsApi.listForField(fieldId!).then(r => r.data),
    { enabled: !!fieldId }
  )

  const propose = useMutation(
    (data: SubscriptionCreate) => subscriptionsApi.propose({ ...data, field_id: fieldId! }),
    {
      onSuccess: () => {
        qc.invalidateQueries(['subscriptions', fieldId])
        toast.success('Subscription proposed — player will be notified')
        setForm(f => ({ ...f, player_id: '', recurring_days: [] }))
      },
      onError: (err: any) => { toast.error(err?.response?.data?.error?.message || 'Failed to propose') },
    }
  )

  const toggleDay = (day: string) =>
    setForm(f => ({
      ...f,
      recurring_days: f.recurring_days.includes(day)
        ? f.recurring_days.filter(d => d !== day)
        : [...f.recurring_days, day],
    }))

  // Price preview
  const tierMonths: Record<string, number> = { '1_month': 1, '2_months': 2, '3_months': 3 }
  const totalSessions = Math.round(form.recurring_days.length * 4.33 * (tierMonths[form.tier] ?? 1))
  const totalPrice = currentField
    ? (currentField.price_per_hour * form.session_duration_hours * totalSessions).toFixed(2)
    : '—'

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: '#1A1F3A', marginBottom: 4 }}>Subscriptions</h1>
      <p style={{ color: '#718096', marginBottom: 24 }}>{currentField?.name ?? 'No field selected'}</p>

      {/* Propose form */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 24, marginBottom: 28, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15 }}>Propose New Subscription</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={lbl}>Player ID *</label>
            <input style={inp} value={form.player_id} onChange={e => setForm(f => ({ ...f, player_id: e.target.value }))} placeholder="Player UUID" />
          </div>
          <div>
            <label style={lbl}>Recurring Days</label>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {DAYS.map(d => (
                <button key={d} type="button"
                  style={{ padding: '5px 12px', borderRadius: 20, border: '1.5px solid', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                    background: form.recurring_days.includes(d) ? GREEN : 'transparent',
                    color: form.recurring_days.includes(d) ? '#fff' : '#4a5568',
                    borderColor: form.recurring_days.includes(d) ? GREEN : '#e2e8f0' }}
                  onClick={() => toggleDay(d)}>{d.slice(0, 3)}</button>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={lbl}>Session Start Time</label>
              <input style={inp} type="time" value={form.session_start_time}
                onChange={e => setForm(f => ({ ...f, session_start_time: e.target.value }))} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={lbl}>Duration (hours)</label>
              <input style={inp} type="number" min={0.5} max={4} step={0.5} value={form.session_duration_hours}
                onChange={e => setForm(f => ({ ...f, session_duration_hours: Number(e.target.value) }))} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={lbl}>Tier</label>
              <select style={inp} value={form.tier} onChange={e => setForm(f => ({ ...f, tier: e.target.value as typeof form.tier }))}>
                {TIERS.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </select>
            </div>
          </div>
          {/* Price preview */}
          <div style={{ background: '#f0fff4', borderRadius: 8, padding: '10px 16px', fontSize: 13 }}>
            <strong>{totalSessions} sessions</strong> · Total: <strong style={{ color: GREEN }}>ETB {totalPrice}</strong>
          </div>
          <button
            style={{ padding: '11px 24px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, cursor: propose.isLoading ? 'not-allowed' : 'pointer', alignSelf: 'flex-start' }}
            disabled={propose.isLoading || !form.player_id || form.recurring_days.length === 0}
            onClick={() => propose.mutate(form)}>
            {propose.isLoading ? 'Sending…' : 'Propose Subscription'}
          </button>
        </div>
      </div>

      {/* Active subscriptions list */}
      <h3 style={{ fontSize: 15, margin: '0 0 12px' }}>Active Subscriptions</h3>
      {isLoading ? <p style={{ color: '#718096' }}>Loading…</p> : subs.length === 0 ? (
        <p style={{ color: '#718096' }}>No active subscriptions for this field.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {subs.map((s: any) => (
            <div key={s.id} style={{ background: '#fff', borderRadius: 10, padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{s.tier.replace('_', ' ')} — {s.recurring_days.join(', ')}</div>
                <div style={{ fontSize: 12, color: '#718096' }}>{s.session_start_time} · {s.total_sessions} sessions · ETB {s.total_price}</div>
              </div>
              <span style={{ background: s.status === 'active' ? '#c6f6d5' : '#e2e8f0', color: s.status === 'active' ? '#276749' : '#4a5568', padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>
                {s.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const lbl: React.CSSProperties = { display: 'block', fontSize: 11, fontWeight: 600, color: '#4a5568', marginBottom: 3 }
const inp: React.CSSProperties = { width: '100%', padding: '9px 12px', borderRadius: 7, border: '1.5px solid #e2e8f0', fontSize: 13, boxSizing: 'border-box' }
