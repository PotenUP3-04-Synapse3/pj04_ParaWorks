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
    <div className="min-h-screen bg-[#f6f3ef] text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-[272px] bg-[var(--workspace-rail)] text-white md:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-white/10 px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-lg bg-[var(--workspace-accent)] text-base font-black text-[#13231f]">
                P
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">ParaWorks</p>
                <p className="truncate text-xs text-white/58">{shell.subtitle}</p>
              </div>
            </div>
          </div>

          <div className="px-3 py-3">
            <div className="flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm text-white/72 ring-1 ring-white/10">
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

            <div className="mx-2 rounded-lg border border-white/10 bg-white/[0.06] p-3">
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
            <div className="mb-3 rounded-lg border border-white/10 p-1" aria-label={shell.language}>
              <div className="grid grid-cols-2 gap-1">
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded-md text-xs font-semibold ${
                    locale === "ko" ? "bg-white text-[#21132b]" : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded-md text-xs font-semibold ${
                    locale === "en" ? "bg-white text-[#21132b]" : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  EN
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-[#160d1d] px-3 py-2 text-xs text-white/62">
              <span className="h-2 w-2 rounded-full bg-[var(--workspace-accent)]" />
              MVP smoke workspace
            </div>
          </div>
        </div>
      </aside>
      <div className="md:pl-[272px]">
        <header className="sticky top-0 z-20 border-b border-[var(--line-soft)] bg-white/90 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-[var(--workspace-rail)] text-xs font-black text-white">
                P
              </span>
              <span className="text-sm font-semibold">ParaWorks</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-lg border border-[var(--line-soft)] bg-white p-0.5" aria-label={shell.language}>
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded-md px-2 text-xs font-medium ${
                    locale === "ko" ? "bg-neutral-900 text-white" : "text-muted"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded-md px-2 text-xs font-medium ${
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
                      className={`grid h-9 w-9 place-items-center rounded-lg ${
                        active ? "bg-neutral-900 text-white" : "text-muted"
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
        <header className="sticky top-0 z-10 hidden border-b border-[var(--line-soft)] bg-[#f6f3ef]/88 px-8 py-4 backdrop-blur md:block">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div className="flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-[var(--line-soft)] bg-white px-4 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
              <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="truncate">메시지, 검토 항목, 사내 문서를 검색하거나 AI 에이전트에게 질문</span>
            </div>
            <button
              type="button"
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-4 text-sm font-semibold text-white shadow-sm"
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
          ? "bg-[var(--workspace-rail-active)] text-white shadow-sm"
          : "text-white/70 hover:bg-white/10 hover:text-white"
      }`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{shell[item.labelKey]}</span>
    </Link>
  );
}
