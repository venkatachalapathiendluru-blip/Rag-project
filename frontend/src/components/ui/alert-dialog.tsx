import * as Dialog from '@radix-ui/react-alert-dialog'
import type { ReactNode } from 'react'
import { Button } from './button'

export function ConfirmDialog({
  trigger, title, description, confirmLabel, onConfirm,
}: {
  trigger: ReactNode
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => void
}) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(26rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-line bg-raised p-5 shadow-[0_12px_32px_rgb(0_0_0/0.18)]">
          <Dialog.Title className="text-base font-semibold">{title}</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-ink-2">{description}</Dialog.Description>
          <div className="mt-5 flex justify-end gap-2">
            <Dialog.Cancel asChild>
              <Button>Keep it</Button>
            </Dialog.Cancel>
            <Dialog.Action asChild>
              <Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button>
            </Dialog.Action>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
