export default function WeightTrendChart({ corridor, days }: { corridor?: string; days: number }) {
  return (
    <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '6px', textAlign: 'center' }}>
      <p style={{ color: '#666', margin: 0 }}>Weight trend chart for {corridor || 'all corridors'} — last {days} days</p>
    </div>
  );
}
