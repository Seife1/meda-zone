import { NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../context/ThemeContext'

const NAV = [
  { to: '/', label: '🎮 Command Center', fieldOnly: true },
  { to: '/overview', label: '📊 Overview', fieldOnly: true },
  { to: '/', label: '📊 Overview', superOnly: true },
  { to: '/fields', label: '⚽ Fields' },
  { to: '/slots', label: '🗓 Slots' },
  { to: '/bookings', label: '📋 Bookings' },
  { to: '/checkin', label: '✅ Check-In' },
  { to: '/subscriptions', label: '🔄 Subscriptions' },
  { to: '/analytics', label: '📈 Analytics', superOnly: true },
  { to: '/users', label: '👥 Users', superOnly: true },
]

export default function Sidebar() {
  const { role, displayName, logout } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const isSuper = role === 'SUPER_ADMIN'

  return (
    <aside style={styles.aside}>
      {/* Brand */}
      <div style={styles.brand}>
        <img
          src="/logo_light.png"
          alt="MedaZone"
          style={{ height: 36, objectFit: 'contain' }}
        />
      </div>

      {/* Nav */}
      <nav style={styles.nav}>
        {NAV.filter((n) => {
          if (n.superOnly && !isSuper) return false
          if (n.fieldOnly && isSuper) return false
          return true
        }).map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/'}
            style={({ isActive }) => ({
              ...styles.link,
              backgroundColor: isActive ? '#7DC832' : 'transparent',
              color: isActive ? '#fff' : '#cbd5e0',
            })}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.user}>
          <span style={styles.avatar}>{(displayName || 'A').slice(0, 1).toUpperCase()}</span>
          <span style={{ fontSize: 13, color: '#9DC4A8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {displayName || role}
          </span>
          <button onClick={toggleTheme} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 16 }}>
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
        <button onClick={logout} style={styles.logoutBtn}>Logout</button>
      </div>
    </aside>
  )
}

const styles: Record<string, React.CSSProperties> = {
  aside: {
    width: 220, minHeight: '100vh', backgroundColor: '#1A1F3A',
    display: 'flex', flexDirection: 'column', padding: '0 0 16px',
  },
  brand: {
    padding: '24px 20px 20px',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
    marginBottom: 8,
  },
  nav: { flex: 1, display: 'flex', flexDirection: 'column', gap: 2, padding: '8px 12px' },
  link: {
    display: 'block', padding: '10px 14px', borderRadius: 8,
    textDecoration: 'none', fontSize: 14, fontWeight: 500,
    transition: 'background 0.15s',
  },
  footer: { padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.08)' },
  user: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 },
  avatar: {
    width: 30, height: 30, borderRadius: '50%', backgroundColor: '#7DC832',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, fontWeight: 700, color: '#fff', flexShrink: 0,
    lineHeight: '30px', textAlign: 'center',
  },
  logoutBtn: {
    width: '100%', padding: '8px', borderRadius: 6, border: 'none',
    background: 'rgba(239,68,68,0.15)', color: '#f87171',
    cursor: 'pointer', fontSize: 13, fontWeight: 500,
  },
}
