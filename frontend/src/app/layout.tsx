import type { Metadata } from "next";
import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "ParaWorks Harness",
  description: "Minimal frontend harness for ParaWorks demos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `
try {
  var theme = localStorage.getItem('paraworks-theme') || 'dark';
  document.documentElement.dataset.theme = theme === 'light' ? 'light' : 'dark';
} catch (_) {
  document.documentElement.dataset.theme = 'dark';
}
`,
          }}
        />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
