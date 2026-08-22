"use client";

import { Anchor } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/states";
import { api } from "@/services/api";

export default function HomePage() {
  const router = useRouter();
  const [error, setError] = useState<string>();
  useEffect(() => {
    api<{ completed: boolean }>("/setup/status")
      .then((status) => router.replace(status.completed ? "/dashboard" : "/setup"))
      .catch((reason: Error) => setError(reason.message));
  }, [router]);
  return (
    <main className="centered-page">
      <div className="brand-mark"><Anchor /></div>
      {error ? <ErrorState message={error} retry={() => window.location.reload()} /> : <LoadingState label="Opening Upcode Sprint" />}
    </main>
  );
}

