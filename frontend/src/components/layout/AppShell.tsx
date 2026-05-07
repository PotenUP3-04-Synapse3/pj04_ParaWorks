"use client";

import {
  Activity,
  Bell,
  Bot,
  CalendarClock,
  CircleHelp,
  Database,
  FileClock,
  GitBranch,
  Home,
  Inbox,
  Map,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, type ReactNode } from "react";
import { LanguageProvider } from "@/lib/i18n/LanguageProvider";

const navGroups = [
  {
    label: "",
    items: [
      { href: "/dashboard", label: "대시보드", icon: Home },
      { href: "/messages", label: "실시간 활동", icon: Activity },
      { href: "/review", label: "검토 사항", icon: Inbox, badge: 12 },
    ],
  },
  {
    label: "지식 라이브러리",
    items: [
      { href: "/decisions", label: "의사결정", icon: ShieldCheck },
      { href: "/timeline", label: "타임라인", icon: GitBranch },
      { href: "/history", label: "히스토리", icon: FileClock },
      { href: "/knowledge-map", label: "지식 맵", icon: Map },
    ],
  },
  {
    label: "",
    items: [
      { href: "/search", label: "Ask 워크스페이스", icon: Bot },
      { href: "/agent-runs", label: "에이전트 실행 기록", icon: CalendarClock },
      { href: "/integrations", label: "연동 관리", icon: Database },
      { href: "/notifications", label: "알림", icon: Bell, badge: 3 },
      { href: "/admin", label: "관리자 콘솔", icon: Settings },
    ],
  },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <LanguageProvider>
      <ShellContent>{children}</ShellContent>
    </LanguageProvider>
  );
}

function ShellContent({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const query = String(formData.get("q") ?? "").trim();
    router.push(query ? `/search?q=${encodeURIComponent(query)}` : "/search");
  }

  return (
    <div className="min-h-screen bg-app text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[216px] border-r border-line bg-sidebar px-4 py-6 lg:flex lg:flex-col">
        <Link href="/dashboard" className="flex items-center gap-3 px-1">
          <span className="brand-mark" aria-hidden="true">
            <Sparkles className="h-4 w-4" />
          </span>
          <span className="min-w-0">
            <span className="block text-[22px] font-extrabold leading-6 text-ink">ParaWorks</span>
            <span className="mt-2 block text-[11px] font-medium text-muted">회사 메모리 플랫폼</span>
          </span>
        </Link>

        <nav className="mt-6 flex-1 overflow-y-auto">
          {navGroups.map((group, groupIndex) => (
            <div key={`${group.label}-${groupIndex}`} className="border-t border-line py-4 first:border-t-0">
              {group.label ? <p className="mb-2 px-2 text-[13px] font-medium text-[#4b5a78]">{group.label}</p> : null}
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link key={item.href} href={item.href} className={`sidebar-link ${active ? "active" : ""}`}>
                      <Icon className="h-[17px] w-[17px]" aria-hidden="true" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      {"badge" in item ? <span className="nav-badge">{item.badge}</span> : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="mt-4 flex items-center justify-between rounded-lg bg-[#f3f6fb] p-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-[#d8b7a5] text-xs font-bold text-white">
              김
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-bold text-ink">김하나</span>
              <span className="block text-[11px] text-muted">리뷰어</span>
            </span>
          </div>
          <button type="button" className="icon-button small" aria-label="사용자 설정">
            <Settings className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </aside>

      <div className="lg:pl-[216px]">
        <header className="sticky top-0 z-20 bg-app/95 px-4 py-4 backdrop-blur md:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <Link href="/dashboard" className="flex items-center gap-2 lg:hidden">
              <span className="brand-mark small" aria-hidden="true">
                <Sparkles className="h-4 w-4" />
              </span>
              <span className="font-bold text-ink">ParaWorks</span>
            </Link>

            <form onSubmit={submitSearch} className="top-search ml-auto min-w-0 flex-1 md:max-w-[410px]">
              <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
              <input
                name="q"
                className="min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-[#8a96ad]"
                placeholder="검색 (의사결정, 프로젝트, 키워드)"
                aria-label="회사 메모리 검색"
              />
            </form>

            <div className="flex shrink-0 items-center gap-2">
              <button type="button" className="icon-button" aria-label="도움말">
                <CircleHelp className="h-[18px] w-[18px]" aria-hidden="true" />
              </button>
              <Link href="/notifications" className="icon-button notification-button" aria-label="알림">
                <Bell className="h-[18px] w-[18px]" aria-hidden="true" />
                <span>3</span>
              </Link>
              <div className="hidden items-center gap-2 sm:flex">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-[#d8b7a5] text-xs font-bold text-white">
                  김
                </span>
                <span className="text-[13px] font-bold text-ink">김하나</span>
              </div>
            </div>
          </div>
        </header>

        <main className="w-full px-4 pb-8 pt-1 md:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
