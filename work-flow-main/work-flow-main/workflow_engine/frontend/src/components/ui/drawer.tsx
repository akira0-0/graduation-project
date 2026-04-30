import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { cn } from "../../lib/utils";

export const Drawer = Dialog.Root;
export const DrawerTrigger = Dialog.Trigger;
export const DrawerClose = Dialog.Close;

export const DrawerContent = ({
  className,
  children,
  ...props
}: React.ComponentProps<typeof Dialog.Content>) => (
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
    <Dialog.Content
      className={cn(
        "fixed right-0 top-0 z-50 h-full w-[520px] max-w-[90vw] border-l border-border bg-card p-4 shadow-xl outline-none",
        className
      )}
      {...props}
    >
      {children}
    </Dialog.Content>
  </Dialog.Portal>
);

export const DrawerTitle = Dialog.Title;
export const DrawerDescription = Dialog.Description;