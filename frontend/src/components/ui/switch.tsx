import * as SwitchPrimitive from '@radix-ui/react-switch'
import type { ComponentProps } from 'react'

export function Switch(props: ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      className="relative inline-flex h-5 w-9 shrink-0 rounded-full bg-line-strong transition-colors duration-150 data-[state=checked]:bg-accent disabled:opacity-50"
      {...props}
    >
      <SwitchPrimitive.Thumb className="block size-4 translate-x-0.5 translate-y-0.5 rounded-full bg-raised transition-transform duration-150 data-[state=checked]:translate-x-[18px]" />
    </SwitchPrimitive.Root>
  )
}
