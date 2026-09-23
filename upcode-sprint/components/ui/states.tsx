import { AlertTriangle, Inbox, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="state"><LoaderCircle className="spin" /><span>{label}</span></div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="state empty-state"><Inbox /><strong>{title}</strong><span>{description}</span></div>;
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="state error-state"><AlertTriangle /><strong>Something went wrong</strong><span>{message}</span>{retry ? <Button variant="outline" onClick={retry}>Try again</Button> : null}</div>;
}

