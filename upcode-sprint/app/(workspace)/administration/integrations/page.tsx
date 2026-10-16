"use client";

import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/ui/states";
import { useAuth } from "@/features/auth/auth-context";
import { InstanceConnection } from "@/features/integrations/instance-connection";

export default function IntegrationsPage() {
  const { hasPermission } = useAuth();
  if (!hasPermission("settings.manage"))
    return <ErrorState message="Settings permission required" />;
  return (
    <>
      <PageHeader title="Integrations" description="Connect this Sprint instance with Forge." />
      <div className="content-grid">
        <InstanceConnection peerName="Forge" />
      </div>
    </>
  );
}
