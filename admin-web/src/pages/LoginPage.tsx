import { useState, FormEvent } from 'react'
import { useAuth } from '../hooks/useAuth'

const GREEN = '#7DC832'
const NAVY = '#1A1F3A'

export default function LoginPage() {
  const { login, loading } = useAuth()
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [obscure, setObscure] = useState(true)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(phone, password)
    } catch (err: any) {
      setError(err.message || 'Login failed')
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: NAVY }}>
      <div style={{ background: '#fff', borderRadius: 16, padding: 40, width: 360, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>

        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <img src="/logo_dark.png" alt="MedaZone" style={{ height: 56, objectFit: 'contain', marginBottom: 8 }} />
          <p style={{ margin: 0, color: '#718096', fontSize: 14 }}>Admin Dashboard</p>
        </div>

        {error && (
          <div style={{ background: '#fff5f5', border: '1px solid #fed7d7', borderRadius: 8, padding: '10px 14px', marginBottom: 16, color: '#c53030', fontSize: 13 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Phone Number</label>
          <input
            style={styles.input}
            type="tel"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="+251 9XX XXX XXX"
            required
          />

          <label style={{ ...styles.label, marginTop: 12 }}>Password</label>
          <div style={{ position: 'relative' }}>
            <input
              style={{ ...styles.input, paddingRight: 40 }}
              type={obscure ? 'password' : 'text'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
            <button
              type="button"
              onClick={() => setObscure(v => !v)}
              style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#718096', fontSize: 13 }}
            >
              {obscure ? 'Show' : 'Hide'}
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{ ...styles.btn, background: GREEN, marginTop: 24 }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p style={{ marginTop: 20, fontSize: 12, color: '#a0aec0', textAlign: 'center' }}>
          Admin access only. Players use the mobile app.
        </p>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#4a5568', marginBottom: 6 },
  input: {
    width: '100%', padding: '12px 14px', borderRadius: 10, border: '1.5px solid #e2e8f0',
    fontSize: 15, outline: 'none', boxSizing: 'border-box',
  },
  btn: {
    width: '100%', padding: 14, borderRadius: 10, border: 'none',
    color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
  },
}
