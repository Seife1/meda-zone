import { useState, useEffect, FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { fieldsApi, FieldCreate } from '../api/fields'
import toast from 'react-hot-toast'

// Fix Leaflet default icon
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function MapPicker({ lat, lng, onChange }: { lat: number; lng: number; onChange: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onChange(e.latlng.lat, e.latlng.lng) })
  return lat ? <Marker position={[lat, lng]} /> : null
}

const GREEN = '#7DC832'

export default function FieldCreatePage() {
  const nav = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const isEdit = !!id

  const [form, setForm] = useState<FieldCreate & { lat: number; lng: number }>({
    name: '', address: '', neighborhood: '', lat: 9.005401, lng: 38.763611,
    surface_type: 'grass', field_size: '', amenities: {}, price_per_hour: 0,
    operating_hours: {}, photo_urls: [],
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isEdit) {
      fieldsApi.get(id!).then(r => {
        const f = r.data
        setForm(prev => ({
          ...prev,
          name: f.name,
          address: f.address,
          neighborhood: f.neighborhood ?? undefined,
          lat: f.lat,
          lng: f.lng,
          surface_type: f.surface_type,
          field_size: f.field_size ?? undefined,
          amenities: f.amenities,
          price_per_hour: f.price_per_hour,
          operating_hours: f.operating_hours,
          photo_urls: f.photo_urls,
        }))
      }).catch(() => toast.error('Failed to load field'))
    }
  }, [id])

  const set = (k: string, v: unknown) => setForm(prev => ({ ...prev, [k]: v }))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (isEdit) { await fieldsApi.update(id!, form); toast.success('Field updated') }
      else { await fieldsApi.create(form); toast.success('Field created') }
      nav('/fields')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save field')
    } finally { setSaving(false) }
  }

  return (
    <div style={{ padding: 32, maxWidth: 720 }}>
      <h1 style={{ fontWeight: 700, fontStyle: 'italic', color: '#1A1F3A', marginBottom: 24 }}>
        {isEdit ? 'Edit Field' : 'Create Field'}
      </h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Field_ label="Field Name *" value={form.name} onChange={v => set('name', v)} required />
        <Field_ label="Address *" value={form.address} onChange={v => set('address', v)} required />
        <Field_ label="Neighborhood" value={form.neighborhood ?? ''} onChange={v => set('neighborhood', v)} />

        <div>
          <label style={lbl}>Surface Type *</label>
          <select style={inp} value={form.surface_type} onChange={e => set('surface_type', e.target.value)}>
            {['grass', 'artificial', 'futsal'].map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        <Field_ label="Price per Hour (ETB) *" type="number" value={String(form.price_per_hour)} onChange={v => set('price_per_hour', Number(v))} required />

        {/* Amenities */}
        <div>
          <label style={lbl}>Amenities</label>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {['lighting', 'changing_rooms', 'parking', 'water'].map(a => (
              <label key={a} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input type="checkbox" checked={!!(form.amenities as any)[a]}
                  onChange={e => set('amenities', { ...form.amenities, [a]: e.target.checked })} />
                {a.replace('_', ' ')}
              </label>
            ))}
          </div>
        </div>

        {/* Map picker */}
        <div>
          <label style={lbl}>Location (click map to pin) *</label>
          <p style={{ fontSize: 12, color: '#718096', margin: '4px 0 8px' }}>
            Lat: {form.lat.toFixed(6)} · Lng: {form.lng.toFixed(6)}
          </p>
          <div style={{ height: 300, borderRadius: 10, overflow: 'hidden', border: '1.5px solid #e2e8f0' }}>
            <MapContainer center={[form.lat, form.lng]} zoom={13} style={{ height: '100%', width: '100%' }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <MapPicker lat={form.lat} lng={form.lng} onChange={(lat, lng) => { set('lat', lat); set('lng', lng) }} />
            </MapContainer>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
          <button type="submit" disabled={saving}
            style={{ padding: '12px 28px', background: GREEN, color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, cursor: saving ? 'not-allowed' : 'pointer' }}>
            {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Field'}
          </button>
          <button type="button" onClick={() => nav('/fields')}
            style={{ padding: '12px 20px', background: 'transparent', border: '1.5px solid #e2e8f0', borderRadius: 8, cursor: 'pointer' }}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}

function Field_({ label, value, onChange, type = 'text', required = false }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean
}) {
  return (
    <div>
      <label style={lbl}>{label}</label>
      <input style={inp} type={type} value={value} required={required}
        onChange={e => onChange(e.target.value)} />
    </div>
  )
}

const lbl: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 600, color: '#4a5568', marginBottom: 4 }
const inp: React.CSSProperties = { width: '100%', padding: '10px 14px', borderRadius: 8, border: '1.5px solid #e2e8f0', fontSize: 14, boxSizing: 'border-box' }
