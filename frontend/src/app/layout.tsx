import type { Metadata } from "next";
import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Paraworks Company Memory",
  description: "AI-powered enterprise company memory dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <script
          dangerouslySetInnerHTML={{
            __html: `
try {
  document.documentElement.dataset.theme = 'light';
  localStorage.setItem('paraworks-theme', 'light');
} catch (_) {
  document.documentElement.dataset.theme = 'light';
}
`,
          }}
        />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
