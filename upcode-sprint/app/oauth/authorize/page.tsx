import { Suspense } from "react";

import { LoadingState } from "@/components/ui/states";
import { OAuthConsent } from "@/features/auth/oauth-consent";

export default function OAuthAuthorizePage() {
  return (
    <main className="centered-page">
      <Suspense fallback={<LoadingState />}>
        <OAuthConsent />
      </Suspense>
    </main>
  );
}
