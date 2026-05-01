"use client";

import {
  Activity,
  BarChart3,
  Bot,
  Database,
  Library,
  LayoutDashboard,
  MessageSquare,
  Search,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageProvider";

const navItems = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard, section: "workspace" },
  { href: "/messages", labelKey: "messages", icon: MessageSquare, section: "workspace" },
  { href: "/review", labelKey: "review", icon: Activity, section: "workspace" },
  { href: "/knowledge", labelKey: "knowledge", icon: Library, section: "workspace" },
  { href: "/search", labelKey: "search", icon: Search, section: "workspace" },
  { href: "/agent-runs", labelKey: "agentRuns", icon: BarChart3, section: "workspace" },
  { href: "/integrations", labelKey: "integrations", icon: Database, section: "tools" },
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
  const workspaceItems = navItems.filter((item) => item.section === "workspace");
  const toolItems = navItems.filter((item) => item.section === "tools");

  return (
    <div className="min-h-screen text-ink">
      <aside className="liquid-dark fixed inset-y-3 left-3 hidden w-[272px] rounded-[28px] text-white md:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-white/[0.12] px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="liquid-primary grid h-10 w-10 place-items-center rounded-2xl text-base font-black">
                P
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">ParaWorks</p>
                <p className="truncate text-xs text-white/58">{shell.subtitle}</p>
              </div>
            </div>
          </div>

          <div className="px-3 py-3">
            <div className="flex items-center gap-2 rounded-2xl border border-white/[0.16] bg-white/[0.12] px-3 py-2 text-sm text-white/76 shadow-[inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-xl">
              <Search className="h-4 w-4" aria-hidden="true" />
              <span className="truncate">검색, 에이전트 실행, 문서 찾기</span>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto px-2 pb-4">
            <div className="mb-5">
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wide text-white/42">
                Home
              </p>
              <div className="space-y-1">
                {workspaceItems.map((item) => (
                  <ShellLink key={item.href} item={item} active={pathname === item.href} shell={shell} />
                ))}
              </div>
            </div>

            <div className="mb-5">
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wide text-white/42">
                Tools
              </p>
              <div className="space-y-1">
                {toolItems.map((item) => (
                  <ShellLink key={item.href} item={item} active={pathname === item.href} shell={shell} />
                ))}
              </div>
            </div>

            <div className="mx-2 rounded-2xl border border-white/[0.14] bg-white/[0.1] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.16)] backdrop-blur-xl">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
                <span className="text-sm font-semibold">Agent Inbox</span>
              </div>
              <p className="mt-2 text-xs leading-5 text-white/58">
                Slack Agent, Review, RAG 연결을 위한 작업대가 준비 중입니다.
              </p>
            </div>
          </nav>

          <div className="border-t border-white/10 p-3">
            <div className="mb-3 rounded-2xl border border-white/[0.14] bg-white/[0.08] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.16)]" aria-label={shell.language}>
              <div className="grid grid-cols-2 gap-1">
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded-md text-xs font-semibold ${
                    locale === "ko" ? "bg-white/90 text-[#21132b] shadow-sm" : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded-md text-xs font-semibold ${
                    locale === "en" ? "bg-white/90 text-[#21132b] shadow-sm" : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  EN
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-2xl border border-white/[0.12] bg-black/[0.18] px-3 py-2 text-xs text-white/68 backdrop-blur-xl">
              <span className="h-2 w-2 rounded-full bg-[var(--workspace-accent)]" />
              MVP smoke workspace
            </div>
          </div>
        </div>
      </aside>
      <div className="md:pl-[296px]">
        <header className="sticky top-0 z-20 border-b border-[var(--line-soft)] bg-white/70 px-4 py-3 backdrop-blur-2xl md:hidden">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="liquid-primary grid h-8 w-8 place-items-center rounded-2xl text-xs font-black">
                P
              </span>
              <span className="text-sm font-semibold">ParaWorks</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="liquid-control flex rounded-2xl p-0.5" aria-label={shell.language}>
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded-md px-2 text-xs font-medium ${
                    locale === "ko" ? "bg-neutral-900 text-white shadow-sm" : "text-muted"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded-md px-2 text-xs font-medium ${
                    locale === "en" ? "bg-neutral-900 text-white shadow-sm" : "text-muted"
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
                      className={`grid h-9 w-9 place-items-center rounded-lg ${
                        active ? "bg-neutral-900 text-white shadow-sm" : "liquid-control text-muted"
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
        <header className="sticky top-0 z-10 hidden px-8 py-4 md:block">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div className="liquid-control flex min-w-0 flex-1 items-center gap-3 rounded-[24px] px-4 py-2 text-sm text-[var(--ink-muted)]">
              <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="truncate">메시지, 검토 항목, 사내 문서를 검색하거나 AI 에이전트에게 질문</span>
            </div>
            <button
              type="button"
              className="liquid-primary inline-flex h-10 items-center gap-2 rounded-[24px] px-4 text-sm font-semibold transition hover:scale-[1.01] active:scale-[0.99]"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Agent 준비 중
            </button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-5 md:px-8 md:py-6">{children}</main>
      </div>
    </div>
  );
}

type ShellItem = (typeof navItems)[number];

function ShellLink({
  item,
  active,
  shell,
}: {
  item: ShellItem;
  active: boolean;
  shell: Record<ShellItem["labelKey"], string> & Record<string, string>;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={`flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition ${
        active
          ? "bg-white/20 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.18),0_10px_24px_rgba(0,0,0,0.12)]"
          : "text-white/70 hover:bg-white/10 hover:text-white"
      }`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{shell[item.labelKey]}</span>
    </Link>
  );
}
