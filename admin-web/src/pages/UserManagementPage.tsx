import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { adminApi, AdminUser } from '../api/admin'
import { fieldsApi } from '../api/fields'
import toast from 'react-hot-toast'

const GREEN = '#7DC832'
const NAVY = '#1A1F3A'

export default function UserManagementPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [newPhone, setNewPhone] = useState('')
  const [newName, setNewName] = useState('')
  const [generatedPassword, setGeneratedPassword] = useState('')
  const [sponsorFieldId, setSponsorFieldId] = useState('')
  const [sponsorStart, setSponsorStart] = useState('')
  const [sponsorEnd, setSponsorEnd] = useState('')

  const { data: users = [], isLoading } = useQuery('adminUsers',
    () => adminApi.listUsers().then(r => r.data))
  const { data: fields = [] } = useQuery('fields',
    () => fieldsApi.list().then(r => r.data))

  const createUser = useMutation(
    () => adminApi.createUser({ phone_number: newPhone, display_name: newName || undefined, role: 'FIELD_OWNER' }),
    {
      onSuccess: (res) => { 
        qc.invalidateQueries('adminUsers'); 
        toast.success('Field owner created'); 
        setShowForm(false); 
        setNewPhone(''); 
        setNewName('');
        if (res.data.temp_password) {
          setGeneratedPassword(res.data.temp_password);
        }
      },
      onError: (e: any) => { toast.error(e?.response?.data?.error?.message || 'Failed to create user') },
    }
  )

  const toggleActive = useMutation(
    ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminApi.updateUser(id, { is_active }),
    { onSuccess: () => { qc.invalidateQueries('adminUsers'); toast.success('Updated') } }
  )

  const setSponsor = useMutation(
    () => fieldsApi.setSponsor(sponsorFieldId, sponsorStart, sponsorEnd),
    { onSuccess: () => { qc.invalidateQueries('fields'); toast.success('Sponsorship set') } }
  )

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontWeight: 700, fontStyle: 'italic', color: NAVY }}>User Management</h1>
        <button onClick={() => { setShowForm(s => !s); setGeneratedPassword(''); }}
          style={{ padding: '10px 20px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>
          {showForm ? 'Cancel' : '+ Add Field Owner'}
        </button>
      </div>

      {/* Generated Password Alert */}
      {generatedPassword && (
        <div style={{ background: '#ebf8ff', border: '1px solid #90cdf4', borderRadius: 12, padding: 20, marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: '0 0 8px', fontSize: 16, color: '#2b6cb0' }}>Account Created Successfully</h3>
            <p style={{ margin: 0, fontSize: 14, color: '#2c5282' }}>Please share this temporary password securely with the field owner.</p>
            <div style={{ marginTop: 12, background: '#fff', padding: '12px 16px', borderRadius: 8, fontSize: 18, fontWeight: 'bold', letterSpacing: 2, border: '1px dashed #cbd5e0', display: 'inline-block' }}>
              {generatedPassword}
            </div>
          </div>
          <button onClick={() => setGeneratedPassword('')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 24, color: '#4a5568' }}>×</button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <h3 style={{ margin: '0 0 14px', fontSize: 14 }}>New Field Owner</h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={lbl}>Phone *</label>
              <input style={inp} value={newPhone} onChange={e => setNewPhone(e.target.value)} placeholder="+251..." />
            </div>
            <div>
              <label style={lbl}>Display Name</label>
              <input style={inp} value={newName} onChange={e => setNewName(e.target.value)} placeholder="Optional" />
            </div>
            <button
              style={{ padding: '10px 20px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}
              onClick={() => createUser.mutate()} disabled={!newPhone || createUser.isLoading}>
              {createUser.isLoading ? 'Creating…' : 'Create'}
            </button>
          </div>
        </div>
      )}

      {/* Sponsor field */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 14 }}>Set Field Sponsorship</h3>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={lbl}>Field</label>
            <select style={inp} value={sponsorFieldId} onChange={e => setSponsorFieldId(e.target.value)}>
              <option value="">Select field…</option>
              {(fields as any[]).map((f: any) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>
          <div><label style={lbl}>Start</label><input style={inp} type="date" value={sponsorStart} onChange={e => setSponsorStart(e.target.value)} /></div>
          <div><label style={lbl}>End</label><input style={inp} type="date" value={sponsorEnd} onChange={e => setSponsorEnd(e.target.value)} /></div>
          <button style={{ padding: '10px 20px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}
            onClick={() => setSponsor.mutate()} disabled={!sponsorFieldId || !sponsorStart || !sponsorEnd}>
            Apply Sponsorship
          </button>
        </div>
      </div>

      {/* Users table */}
      {isLoading ? <p style={{ color: '#718096' }}>Loading…</p> : (
        <div style={{ background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f7fafc' }}>
                {['Phone', 'Name', 'Role', 'Status', 'Actions'].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(users as AdminUser[]).map(u => (
                <tr key={u.id} style={{ borderTop: '1px solid #e2e8f0' }}>
                  <td style={td}>{u.phone_number}</td>
                  <td style={td}>{u.display_name ?? '—'}</td>
                  <td style={td}>
                    <span style={{ background: u.role === 'SUPER_ADMIN' ? '#e9d8fd' : '#bee3f8', color: u.role === 'SUPER_ADMIN' ? '#553c9a' : '#2b6cb0', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700 }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={td}>
                    <span style={{ background: u.is_active ? '#c6f6d5' : '#fed7d7', color: u.is_active ? '#276749' : '#9b2c2c', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700 }}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={td}>
                    <button style={{ background: 'none', border: '1px solid #e2e8f0', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12, color: u.is_active ? '#c53030' : GREEN }}
                      onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}>
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
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

const lbl: React.CSSProperties = { display: 'block', fontSize: 11, fontWeight: 600, color: '#4a5568', marginBottom: 3 }
const inp: React.CSSProperties = { padding: '9px 12px', borderRadius: 7, border: '1.5px solid #e2e8f0', fontSize: 13 }
const th: React.CSSProperties = { padding: '11px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#4a5568', textTransform: 'uppercase' }
const td: React.CSSProperties = { padding: '11px 16px', fontSize: 13, color: NAVY }
