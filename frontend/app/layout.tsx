import type { Metadata } from "next";

import { Providers } from "@/components/providers";

import "@fontsource-variable/geist-mono";
import "@fontsource-variable/inter";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Upcode Sprint", template: "%s · Upcode Sprint" },
  description: "Self-hosted agile project management for your organization",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
