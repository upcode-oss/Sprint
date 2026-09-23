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
  const customLogo = branding?.logo_url;
  return (
    <div className={cn("organization-brand-mark", className)}>
      <Image
        src={customLogo ?? "/logo.png"}
        alt={customLogo ? `${branding.name} logo` : "Sprint logo"}
        width={192}
        height={128}
        unoptimized={Boolean(customLogo)}
        priority={!customLogo}
      />
    </div>
  );
}
