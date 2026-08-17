import { AlertTriangle, Inbox, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="state" role="status" aria-live="polite"><LoaderCircle className="spin" aria-hidden /><span>{label}</span></div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="state empty-state"><Inbox aria-hidden /><strong>{title}</strong><span>{description}</span>{action}</div>;
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="state error-state" role="alert"><AlertTriangle aria-hidden /><strong>This content could not be loaded</strong><span>{message}</span>{retry ? <Button variant="outline" onClick={retry}>Try again</Button> : null}</div>;
}
