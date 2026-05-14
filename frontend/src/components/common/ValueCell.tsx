import clsx from 'clsx'

interface Props {
  value: number
  prefix?: string
  decimals?: number
  className?: string
  showSign?: boolean
}

export function ValueCell({ value, prefix = '', decimals = 2, className, showSign = false }: Props) {
  const positive = value >= 0
  return (
    <span className={clsx('font-mono tabular-nums', positive ? 'text-up' : 'text-down', className)}>
      {showSign && positive ? '+' : ''}
      {prefix}{value.toFixed(decimals)}
    </span>
  )
}
