import clsx from 'clsx'
import type { ReactNode } from 'react'

interface Props {
  title?: string
  children: ReactNode
  className?: string
}

export function PanelBox({ title, children, className }: Props) {
  return (
    <div className={clsx('bg-panel border border-border rounded flex flex-col', className)}>
      {title && (
        <div className="text-2xs font-bold uppercase tracking-widest text-neutral px-2 py-1 border-b border-border">
          {title}
        </div>
      )}
      <div className="flex-1 p-1">{children}</div>
    </div>
  )
}
