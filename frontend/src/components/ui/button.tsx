import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

const variants = cva(
  'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md font-medium transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-on-accent hover:bg-accent-hover',
        secondary: 'border border-line-strong bg-raised text-ink hover:bg-panel',
        ghost: 'text-ink-2 hover:bg-panel hover:text-ink',
        danger: 'bg-bad text-raised hover:opacity-90',
      },
      size: {
        md: 'h-9 px-3.5 text-sm',
        sm: 'h-8 px-2.5 text-[13px]',
        icon: 'size-8',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export function Button({
  className, variant, size, asChild = false, ...props
}: ComponentProps<'button'> & VariantProps<typeof variants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : 'button'
  return <Component className={cn(variants({ variant, size }), className)} {...props} />
}
