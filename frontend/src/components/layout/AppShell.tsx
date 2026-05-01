"use client";

import { Database, LayoutDashboard, MessageSquare, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageProvider";

const navItems = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/integrations", labelKey: "integrations", icon: Database },
  { href: "/messages", labelKey: "messages", icon: MessageSquare },
  { href: "/review", labelKey: "review", icon: ShieldCheck },
  { href: "/search", labelKey: "search", icon: Search },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <LanguageProvider>
      <LocalizedAppShell>{children}</LocalizedAppShell>
    </LanguageProvider>
  );
}

function LocalizedAppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { dictionary, locale, setLocale } = useLanguage();
  const shell = dictionary.shell;

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white px-4 py-5 md:block">
        <div className="mb-7 px-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">ParaWorks</p>
          <h1 className="mt-1 text-lg font-semibold">{shell.subtitle}</h1>
        </div>
        <div className="mb-5 rounded-md border border-line p-1" aria-label={shell.language}>
          <div className="grid grid-cols-2 gap-1">
            <button
              type="button"
              onClick={() => setLocale("ko")}
              className={`h-8 rounded text-xs font-medium ${
                locale === "ko" ? "bg-neutral-900 text-white" : "text-muted hover:bg-neutral-50"
              }`}
            >
              {shell.korean}
            </button>
            <button
              type="button"
              onClick={() => setLocale("en")}
              className={`h-8 rounded text-xs font-medium ${
                locale === "en" ? "bg-neutral-900 text-white" : "text-muted hover:bg-neutral-50"
              }`}
            >
              {shell.english}
            </button>
          </div>
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium ${
                  active
                    ? "border border-line bg-neutral-100 text-ink"
                    : "text-muted hover:bg-neutral-50 hover:text-ink"
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{shell[item.labelKey]}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="md:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-semibold">ParaWorks</span>
            <div className="flex items-center gap-2">
              <div className="flex rounded-md border border-line p-0.5" aria-label={shell.language}>
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded px-2 text-xs font-medium ${
                    locale === "ko" ? "bg-neutral-900 text-white" : "text-muted"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded px-2 text-xs font-medium ${
                    locale === "en" ? "bg-neutral-900 text-white" : "text-muted"
                  }`}
                >
                  EN
                </button>
              </div>
              <nav className="flex gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`grid h-9 w-9 place-items-center rounded-md ${
                      active ? "bg-neutral-100 text-ink" : "text-muted"
                    }`}
                    aria-label={shell[item.labelKey]}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </Link>
                );
              })}
              </nav>
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
