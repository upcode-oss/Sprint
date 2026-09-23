import { Suspense } from "react";

import { LoadingState } from "@/components/ui/states";
import { LoginForm } from "@/features/auth/login-form";

export default function LoginPage() {
  return <main className="centered-page"><Suspense fallback={<LoadingState />}><LoginForm /></Suspense></main>;
}

