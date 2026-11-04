import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

const variants = cva('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium whitespace-nowrap [&_svg]:size-3.5', {
  variants: {
    tone: {
      neutral: 'bg-panel text-ink-2 ring-1 ring-inset ring-line',
      accent: 'bg-accent-soft text-accent',
      good: 'bg-good-soft text-good',
      warn: 'bg-warn-soft text-warn',
      bad: 'bg-bad-soft text-bad',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export type BadgeTone = NonNullable<VariantProps<typeof variants>['tone']>

export function Badge({ className, tone, ...props }: ComponentProps<'span'> & VariantProps<typeof variants>) {
  return <span className={cn(variants({ tone }), className)} {...props} />
}
