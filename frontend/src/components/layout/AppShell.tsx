"use client";

import {
  Bell,
  Bot,
  CalendarClock,
  CircleHelp,
  Database,
  FolderKanban,
  GitBranch,
  Grid2X2,
  Inbox,
  Search,
  Settings,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, clearStoredDemoUserId } from "@/lib/api/client";
import type { AuthUserResponse, DemoUser } from "@/lib/api/types";
import { LanguageProvider } from "@/lib/i18n/LanguageProvider";

type NavItem = {
  href: string;
  label: string;
  icon: typeof Grid2X2;
  badge?: number;
  requiredRole?: "admin";
};

const navGroups: { items: NavItem[] }[] = [
  {
    items: [
      { href: "/dashboard", label: "\ub300\uc2dc\ubcf4\ub4dc", icon: Grid2X2 },
      { href: "/projects", label: "\ud504\ub85c\uc81d\ud2b8", icon: FolderKanban },
      { href: "/review", label: "\uac80\ud1a0\uc0ac\ud56d", icon: Inbox, badge: 12 },
      { href: "/timeline", label: "\ud0c0\uc784\ub77c\uc778", icon: GitBranch },
    ],
  },
  {
    items: [
      { href: "/search", label: "AI \ube44\uc11c", icon: Bot },
      {
        href: "/agent-runs",
        label: "\uc5d0\uc774\uc804\ud2b8 \uc2e4\ud589 \uae30\ub85d",
        icon: CalendarClock,
        requiredRole: "admin",
      },
      { href: "/integrations", label: "\uc5f0\ub3d9 \uad00\ub9ac", icon: Database },
      { href: "/notifications", label: "\uc54c\ub9bc", icon: Bell, badge: 3 },
    ],
  },
  {
    items: [
      { href: "/admin", label: "\uad00\ub9ac\uc790 \ucf58\uc194", icon: Settings, requiredRole: "admin" },
    ],
  },
];

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
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<DemoUser | null>(null);

  useEffect(() => {
    if (pathname === "/login" || pathname.startsWith("/login/")) {
      return;
    }

    let active = true;
    apiGet<AuthUserResponse>("/api/v1/auth/me")
      .then((result) => {
        if (active) {
          setCurrentUser(result.user);
        }
      })
      .catch(() => {
        if (active) {
          setCurrentUser(null);
          router.push("/login");
        }
      });

    return () => {
      active = false;
    };
  }, [pathname, router]);

  const visibleNavGroups = useMemo(
    () =>
      navGroups
        .map((group) => ({
          items: group.items.filter((item) => !item.requiredRole || currentUser?.role === item.requiredRole),
        }))
        .filter((group) => group.items.length > 0),
    [currentUser?.role],
  );

  const accountDisplay = useMemo(() => {
    const isLoggedIn = !!currentUser;
    const name = currentUser?.name ?? "로그인이 필요합니다";
    const roleLabels: Record<string, string> = {
      admin: "관리자",
      manager: "매니저",
      reviewer: "리뷰어",
      employee: "멤버",
    };
    const role = currentUser ? (roleLabels[currentUser.role] ?? currentUser.role) : "여기를 클릭해 로그인하세요";
    const initial = isLoggedIn ? (currentUser?.name?.trim().charAt(0).toUpperCase() || "?") : "!";
    const avatarUrl = currentUser?.avatar_url ?? null;
    return { name, role, initial, avatarUrl, isLoggedIn };
  }, [currentUser]);

  if (pathname === "/login" || pathname.startsWith("/login/")) {
    return <>{children}</>;
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const query = String(formData.get("q") ?? "").trim();
    router.push(query ? `/search?q=${encodeURIComponent(query)}` : "/search");
  }

  async function logout() {
    setAccountMenuOpen(false);
    try {
      await apiPost<{ status: string }>("/api/v1/auth/logout");
    } finally {
      clearStoredDemoUserId();
      setCurrentUser(null);
      router.push("/login");
    }
  }

  return (
    <div className="min-h-screen bg-app text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[216px] border-r border-line bg-sidebar px-4 py-6 lg:flex lg:flex-col">
        <Link href="/dashboard" className="flex items-start gap-3">
          <span className="brand-logo" aria-hidden="true">
            <Image src="/assets/paraworks-logo-icon.png" alt="" width={37} height={37} />
          </span>
          <span className="min-w-0 pt-0.5">
            <span className="brand-wordmark block text-[19px] leading-6 text-[var(--primary-dark)]">paraworks</span>
          </span>
        </Link>

        <nav className="mt-6 flex-1 overflow-y-auto">
          {visibleNavGroups.map((group, groupIndex) => (
            <div key={groupIndex} className="border-t border-line py-4 first:border-t-0 first:pt-0">
              <div className="space-y-2">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link key={item.href} href={item.href} className={`sidebar-link ${active ? "active" : ""}`}>
                      <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="relative mt-4 flex items-center justify-between rounded-lg bg-white p-2 shadow-sm border border-line/50">
          <button
            type="button"
            className={`flex min-w-0 flex-1 items-center gap-2 p-1 text-left outline-none transition-opacity hover:opacity-80 ${
              !accountDisplay.isLoggedIn ? "animate-pulse" : ""
            }`}
            onClick={() => {
              if (!accountDisplay.isLoggedIn) {
                router.push("/login");
              } else {
                setAccountMenuOpen((open) => !open);
              }
            }}
          >
            <span className={`avatar-photo ${!accountDisplay.isLoggedIn ? "bg-[var(--primary-soft)]" : ""}`} aria-hidden="true">
              {accountDisplay.avatarUrl ? (
                <Image src={accountDisplay.avatarUrl} alt="" width={34} height={34} />
              ) : (
                <span className={!accountDisplay.isLoggedIn ? "text-[var(--primary-dark)]" : ""}>
                  {accountDisplay.initial}
                </span>
              )}
            </span>
            <span className="min-w-0 flex-1">
              <span className={`block truncate text-[13px] font-bold ${accountDisplay.isLoggedIn ? "text-ink" : "text-[var(--primary-dark)]"}`}>
                {accountDisplay.name}
              </span>
              <span className="block truncate text-[11px] text-muted">{accountDisplay.role}</span>
            </span>
          </button>
          
          <button
            type="button"
            className="icon-button small shrink-0"
            aria-label={"계정 메뉴"}
            aria-expanded={accountMenuOpen}
            onClick={() => setAccountMenuOpen((open) => !open)}
          >
            <Settings className="h-4 w-4" aria-hidden="true" />
          </button>

          {accountMenuOpen ? (
            <div className="absolute bottom-full right-0 z-40 mb-2 w-44 rounded-lg border border-line bg-[var(--glass-elevated)] p-1 shadow-lg">
              {accountDisplay.isLoggedIn ? (
                <>
                  <button
                    type="button"
                    className="w-full rounded-md px-3 py-2 text-left text-[13px] font-bold text-ink hover:bg-[#f3f7fd]"
                    onClick={() => {
                      setAccountMenuOpen(false);
                      router.push("/account");
                    }}
                  >
                    내 계정 정보
                  </button>
                  <div className="my-1 border-t border-line" />
                  <button
                    type="button"
                    className="w-full rounded-md px-3 py-2 text-left text-[13px] font-bold text-red-600 hover:bg-red-50"
                    onClick={() => void logout()}
                  >
                    로그아웃
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="w-full rounded-md px-3 py-2 text-left text-[13px] font-bold text-[var(--primary-dark)] hover:bg-[var(--primary-soft)]"
                  onClick={() => {
                    setAccountMenuOpen(false);
                    router.push("/login");
                  }}
                >
                  로그인하기
                </button>
              )}
            </div>
          ) : null}
        </div>
      </aside>

      <div className="lg:pl-[216px]">
        <header className="sticky top-0 z-20 bg-app/95 px-4 py-4 backdrop-blur md:px-6 lg:px-6">
          <div className="flex items-center justify-between gap-4">
            <Link href="/dashboard" className="flex items-center gap-2 lg:hidden">
              <span className="brand-logo small" aria-hidden="true">
                <Image src="/assets/paraworks-logo-icon.png" alt="" width={31} height={31} />
              </span>
              <span className="brand-wordmark text-[var(--primary-dark)]">paraworks</span>
            </Link>

            <form onSubmit={submitSearch} className="top-search ml-auto min-w-0 flex-1 md:max-w-[470px]">
              <button type="submit" className="top-search-icon-button" aria-label="AI 비서에게 질문">
                <Search className="h-4 w-4" aria-hidden="true" />
              </button>
              <input
                name="q"
                className="min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-[#667085]"
                placeholder={"\uac80\uc0c9\uc5b4\ub97c \uc785\ub825\ud558\uc138\uc694"}
                aria-label={"\ud68c\uc0ac \uba54\ubaa8\ub9ac \uac80\uc0c9"}
              />
            </form>

            <div className="flex shrink-0 items-center gap-3">
              <button type="button" className="icon-button" aria-label={"\ub3c4\uc6c0\ub9d0"}>
                <CircleHelp className="h-[18px] w-[18px]" aria-hidden="true" />
              </button>
              <Link href="/notifications" className="icon-button notification-button" aria-label={"\uc54c\ub9bc"}>
                <Bell className="h-[18px] w-[18px]" aria-hidden="true" />
                <span>3</span>
              </Link>
            </div>
          </div>
        </header>

        <main className="w-full px-4 pb-8 pt-1 md:px-6 lg:px-6">{children}</main>
      </div>
    </div>
  );
}
