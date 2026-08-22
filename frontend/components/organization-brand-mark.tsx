import { Anchor } from "lucide-react";
import Image from "next/image";

import { cn } from "@/lib/utils";
import type { OrganizationBranding } from "@/types/api";

export function OrganizationBrandMark({
  branding,
  className,
}: {
  branding?: OrganizationBranding;
  className?: string;
}) {
  return (
    <div className={cn(branding?.logo_url ? "organization-brand-mark" : "brand-mark", className)}>
      {branding?.logo_url ? (
        <Image
          src={branding.logo_url}
          alt={`${branding.name} logo`}
          width={80}
          height={80}
          unoptimized
        />
      ) : (
        <Anchor aria-hidden />
      )}
    </div>
  );
}
