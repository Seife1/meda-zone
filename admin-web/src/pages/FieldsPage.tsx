import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { fieldsApi, Field } from '../api/fields'
import toast from 'react-hot-toast'

const GREEN = '#7DC832'

export default function FieldsPage() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const { data: fields = [], isLoading } = useQuery('fields', () => fieldsApi.list().then(r => r.data))

  const toggleStatus = useMutation(
    ({ id, is_active }: { id: string; is_active: boolean }) =>
      fieldsApi.setStatus(id, is_active),
    { onSuccess: () => { qc.invalidateQueries('fields'); toast.success('Status updated') } }
  )

  if (isLoading) return <Loader />

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>Fields</h1>
        <button onClick={() => nav('/fields/new')} style={styles.btn}>+ Add Field</button>
      </div>
      {fields.length === 0 ? (
        <Empty msg="No fields yet. Create your first field." />
      ) : (
        <div style={styles.grid}>
          {fields.map((f: Field) => (
            <div key={f.id} style={styles.card}>
              <div style={styles.cardTop}>
                <span style={styles.name}>{f.name}</span>
                <span style={{ ...styles.badge, background: f.is_active ? '#c6f6d5' : '#fed7d7', color: f.is_active ? '#276749' : '#9b2c2c' }}>
                  {f.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <p style={styles.sub}>{f.address}</p>
              <p style={styles.sub}>{f.surface_type} · ETB {f.price_per_hour}/hr · ⭐ {f.average_rating}</p>
              <div style={styles.actions}>
                <button style={styles.actionBtn} onClick={() => nav(`/fields/${f.id}/edit`)}>Edit</button>
                <button style={{ ...styles.actionBtn, color: f.is_active ? '#c53030' : GREEN }}
                  onClick={() => toggleStatus.mutate({ id: f.id, is_active: !f.is_active })}>
                  {f.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { padding: 32 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  title: { margin: 0, fontSize: 24, fontWeight: 700, color: '#1A1F3A', fontStyle: 'italic' },
  btn: { padding: '10px 20px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 },
  card: { background: '#fff', borderRadius: 12, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  cardTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  name: { fontWeight: 700, fontSize: 16, color: '#1A1F3A' },
  badge: { padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 },
  sub: { margin: '4px 0', color: '#718096', fontSize: 13 },
  actions: { display: 'flex', gap: 8, marginTop: 12 },
  actionBtn: { padding: '6px 14px', border: '1px solid #e2e8f0', borderRadius: 6, background: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500, color: '#4a5568' },
}

function Loader() { return <div style={{ padding: 32, color: '#718096' }}>Loading…</div> }
function Empty({ msg }: { msg: string }) { return <div style={{ padding: 32, color: '#718096', textAlign: 'center' }}>{msg}</div> }
