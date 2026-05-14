interface Props {
  value: number     // -100 to 100
  label: string
  size?: number
}

export function GaugeChart({ value, label, size = 80 }: Props) {
  const clampedValue = Math.max(-100, Math.min(100, value))
  const normalized = (clampedValue + 100) / 200  // 0 to 1
  const angle = normalized * 180 - 90             // -90° (left) to +90° (right)
  const rad   = (angle * Math.PI) / 180

  const cx = size / 2
  const cy = size * 0.6
  const r  = size * 0.38

  const needleLen = r * 0.9
  const nx = cx + needleLen * Math.cos(rad)
  const ny = cy + needleLen * Math.sin(rad)

  // Arc path: semicircle from left to right
  const startX = cx - r
  const startY = cy
  const endX   = cx + r
  const endY   = cy

  const positive = clampedValue >= 0
  const color    = positive ? '#00c853' : '#f44336'

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.7} viewBox={`0 0 ${size} ${size * 0.7}`}>
        {/* Background arc */}
        <path
          d={`M ${startX} ${cy} A ${r} ${r} 0 0 1 ${endX} ${cy}`}
          fill="none" stroke="#2a2a2a" strokeWidth="6"
        />
        {/* Value arc */}
        {clampedValue !== 0 && (
          <path
            d={`M ${cx} ${cy} A ${r} ${r} 0 0 ${positive ? 1 : 0} ${nx} ${ny}`}
            fill="none" stroke={color} strokeWidth="4"
          />
        )}
        {/* Needle */}
        <line x1={cx} y1={cy} x2={nx} y2={ny}
              stroke={color} strokeWidth="2" strokeLinecap="round" />
        {/* Center dot */}
        <circle cx={cx} cy={cy} r="3" fill={color} />
        {/* Value label */}
        <text x={cx} y={cy - r - 4} textAnchor="middle"
              fill={color} fontSize={size * 0.14} fontFamily="monospace" fontWeight="bold">
          {clampedValue.toFixed(2)}
        </text>
      </svg>
      <span className="text-2xs text-neutral uppercase tracking-wide">{label}</span>
    </div>
  )
}
