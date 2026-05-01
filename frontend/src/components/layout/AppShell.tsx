"use client";

import {
  Activity,
  BarChart3,
  Bot,
  Database,
  Library,
  LayoutDashboard,
  LogIn,
  MessageSquare,
  Moon,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState, type ReactNode } from "react";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageProvider";

const navItems = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard, section: "workspace" },
  { href: "/messages", labelKey: "messages", icon: MessageSquare, section: "workspace" },
  { href: "/review", labelKey: "review", icon: Activity, section: "workspace" },
  { href: "/knowledge", labelKey: "knowledge", icon: Library, section: "workspace" },
  { href: "/search", labelKey: "search", icon: Search, section: "workspace" },
  { href: "/agent-runs", labelKey: "agentRuns", icon: BarChart3, section: "workspace" },
  { href: "/integrations", labelKey: "integrations", icon: Database, section: "tools" },
  { href: "/admin", labelKey: "admin", icon: ShieldCheck, section: "tools" },
  { href: "/login", labelKey: "login", icon: LogIn, section: "tools" },
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
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const shell = dictionary.shell;
  const workspaceItems = navItems.filter((item) => item.section === "workspace");
  const toolItems = navItems.filter((item) => item.section === "tools");

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("paraworks-theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
      document.documentElement.dataset.theme = savedTheme;
      return;
    }
    document.documentElement.dataset.theme = "dark";
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("paraworks-theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  return (
    <div className="min-h-screen text-ink">
      <aside className="shell-rail fixed inset-y-4 left-4 hidden w-[276px] rounded-[34px] md:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-[var(--shell-border)] px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="liquid-primary grid h-11 w-11 place-items-center rounded-[22px] text-base font-black">
                P
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">ParaWorks</p>
                <p className="truncate text-xs text-[var(--shell-faint)]">{shell.subtitle}</p>
              </div>
            </div>
          </div>

          <div className="px-3 py-3">
            <GlobalSearchForm
              ariaLabel={shell.searchLabel}
              placeholder={shell.sidebarSearchPlaceholder}
              testId="sidebar-global-search-input"
              variant="sidebar"
            />
          </div>

          <nav className="flex-1 overflow-y-auto px-2 pb-4">
            <div className="mb-5">
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--shell-label)]">
                Home
              </p>
              <div className="space-y-1">
                {workspaceItems.map((item) => (
                  <ShellLink key={item.href} item={item} active={pathname === item.href} shell={shell} />
                ))}
              </div>
            </div>

            <div className="mb-5">
              <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--shell-label)]">
                Tools
              </p>
              <div className="space-y-1">
                {toolItems.map((item) => (
                  <ShellLink key={item.href} item={item} active={pathname === item.href} shell={shell} />
                ))}
              </div>
            </div>

            <div className="liquid-control mx-2 rounded-[24px] p-3 text-[var(--shell-ink)]">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
                <span className="text-sm font-semibold">Agent Inbox</span>
              </div>
              <p className="mt-2 text-xs leading-5 text-[var(--shell-faint)]">
                Slack Agent, Review, RAG 연결을 위한 작업대가 준비 중입니다.
              </p>
            </div>
          </nav>

          <div className="border-t border-[var(--shell-border)] p-3">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
            <div className="liquid-control mb-3 rounded-[24px] p-1" aria-label={shell.language}>
              <div className="grid grid-cols-2 gap-1">
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded-md text-xs font-semibold ${
                    locale === "ko" ? "liquid-segment-active" : "text-[var(--shell-muted)] hover:bg-[var(--shell-hover)]"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded-md text-xs font-semibold ${
                    locale === "en" ? "liquid-segment-active" : "text-[var(--shell-muted)] hover:bg-[var(--shell-hover)]"
                  }`}
                >
                  EN
                </button>
              </div>
            </div>
            <div className="liquid-control flex items-center gap-2 rounded-[22px] px-3 py-2 text-xs text-[var(--shell-muted)]">
              <span className="h-2 w-2 rounded-full bg-[var(--workspace-accent)]" />
              MVP smoke workspace
            </div>
          </div>
        </div>
      </aside>
      <div className="md:pl-[312px]">
        <header className="sticky top-0 z-20 px-3 py-3 md:hidden">
          <div className="liquid-surface rounded-[28px] px-3 py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="liquid-primary grid h-9 w-9 place-items-center rounded-[20px] text-xs font-black">
                P
              </span>
              <span className="text-sm font-semibold">ParaWorks</span>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle theme={theme} onToggle={toggleTheme} compact />
              <div className="liquid-control flex rounded-2xl p-0.5" aria-label={shell.language}>
                <button
                  type="button"
                  onClick={() => setLocale("ko")}
                  className={`h-8 rounded-md px-2 text-xs font-medium ${
                    locale === "ko" ? "liquid-segment-active" : "text-muted hover:bg-[var(--glass-control-strong)]"
                  }`}
                >
                  KO
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`h-8 rounded-md px-2 text-xs font-medium ${
                    locale === "en" ? "liquid-segment-active" : "text-muted hover:bg-[var(--glass-control-strong)]"
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
                        active ? "liquid-segment-active" : "liquid-control text-muted"
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
          </div>
        </header>
        <header className="sticky top-0 z-10 hidden px-8 py-4 md:block">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <GlobalSearchForm
              ariaLabel={shell.searchLabel}
              placeholder={shell.topSearchPlaceholder}
              testId="top-global-search-input"
              variant="top"
            />
            <button
              type="button"
              className="liquid-primary inline-flex h-12 items-center gap-2 rounded-[28px] px-5 text-sm font-semibold transition hover:scale-[1.01] active:scale-[0.99]"
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

function GlobalSearchForm({
  ariaLabel,
  placeholder,
  testId,
  variant,
}: {
  ariaLabel: string;
  placeholder: string;
  testId: string;
  variant: "sidebar" | "top";
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const isTop = variant === "top";

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      router.push("/search");
      return;
    }

    const params = new URLSearchParams({ q: trimmedQuery });
    router.push(`/search?${params.toString()}`);
  }

  return (
    <form
      role="search"
      onSubmit={submitSearch}
      className={
        isTop
          ? "liquid-surface flex min-w-0 flex-1 items-center gap-3 rounded-[30px] px-5 py-3 text-sm text-[var(--ink-muted)]"
          : "liquid-control flex items-center gap-2 rounded-[22px] px-3 py-2 text-sm text-[var(--shell-muted)]"
      }
      aria-label={ariaLabel}
    >
      <Search className={`${isTop ? "h-4 w-4 shrink-0" : "h-4 w-4"} text-current`} aria-hidden="true" />
      <input
        data-testid={testId}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        className="min-w-0 flex-1 bg-transparent text-current outline-none placeholder:text-current/70"
        placeholder={placeholder}
        aria-label={placeholder}
      />
      <button type="submit" className="sr-only">
        {ariaLabel}
      </button>
    </form>
  );
}

function ThemeToggle({
  theme,
  onToggle,
  compact = false,
}: {
  theme: "dark" | "light";
  onToggle: () => void;
  compact?: boolean;
}) {
  const Icon = theme === "dark" ? Moon : Sun;
  const nextLabel = theme === "dark" ? "라이트 모드" : "다크 모드";

  if (compact) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="liquid-control grid h-9 w-9 place-items-center rounded-2xl text-[var(--ink-muted)]"
        aria-label={nextLabel}
        title={nextLabel}
      >
        <Icon className="h-4 w-4" aria-hidden="true" />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      className="liquid-control mb-3 flex h-10 w-full items-center justify-between rounded-[24px] px-3 text-xs font-semibold text-[var(--shell-muted)]"
      aria-label={nextLabel}
      title={nextLabel}
    >
      <span>{theme === "dark" ? "Dark Glass" : "Light Glass"}</span>
      <Icon className="h-4 w-4" aria-hidden="true" />
    </button>
  );
}

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
      className={`flex h-10 items-center gap-3 rounded-[20px] px-3 text-sm font-medium transition ${
        active
          ? "liquid-segment-active"
          : "text-[var(--shell-muted)] hover:bg-[var(--shell-hover)] hover:text-[var(--shell-ink)]"
      }`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{shell[item.labelKey]}</span>
    </Link>
  );
}
