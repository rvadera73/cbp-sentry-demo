import { useRole } from '../../context/RoleContext'
import type { UserRole } from '../../context/RoleContext'

const ROLE_NAMES: Record<UserRole, string> = {
  'cbp_officer': 'CBP Officer',
  'analyst': 'AI Analyst',
  'admin': 'Admin',
}

export default function RoleSelector() {
  const { role, setRole } = useRole()
  const roles: UserRole[] = ['cbp_officer', 'analyst', 'admin']

  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', paddingRight: '1rem' }}>
      <label style={{ fontSize: '0.75rem', fontWeight: '600', margin: 0, color: '#666' }}>DEMO ROLE:</label>
      <select
        value={role}
        onChange={(e) => {
          setRole(e.target.value as UserRole)
          localStorage.setItem('user_role', e.target.value)
        }}
        style={{
          padding: '0.25rem 0.5rem',
          borderRadius: '3px',
          border: '1px solid #d0d0d0',
          fontSize: '0.875rem',
          backgroundColor: 'white',
          cursor: 'pointer',
        }}
      >
        {roles.map((r) => (
          <option key={r} value={r}>
            {ROLE_NAMES[r]}
          </option>
        ))}
      </select>
    </div>
  )
}
