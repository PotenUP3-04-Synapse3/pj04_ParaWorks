"use client";

import {
  Bell,
  Bot,
  CalendarClock,
  CircleHelp,
  Database,
  FileClock,
  GitBranch,
  Grid2X2,
  Inbox,
  Map,
  Search,
  Settings,
  ShieldCheck,
} from "lucide-react";
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
      { href: "/review", label: "\uac80\ud1a0\uc0ac\ud56d", icon: Inbox, badge: 12 },
      { href: "/decisions", label: "\uc758\uc0ac\uacb0\uc815", icon: ShieldCheck },
      { href: "/timeline", label: "\ud0c0\uc784\ub77c\uc778", icon: GitBranch },
      { href: "/history", label: "\ud788\uc2a4\ud1a0\ub9ac", icon: FileClock },
      { href: "/knowledge-map", label: "\uc9c0\uc2dd \ub9f5", icon: Map },
    ],
  },
  {
    items: [
      { href: "/search", label: "Ask \uc6cc\ud06c\uc2a4\ud398\uc774\uc2a4", icon: Bot },
      { href: "/agent-runs", label: "\uc5d0\uc774\uc804\ud2b8 \uc2e4\ud589 \uae30\ub85d", icon: CalendarClock },
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
        }
      });

    return () => {
      active = false;
    };
  }, [pathname]);

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
    const name = currentUser?.name ?? "\ub85c\uadf8\uc778 \ud544\uc694";
    const roleLabels: Record<string, string> = {
      admin: "\uad00\ub9ac\uc790",
      manager: "\ub9e4\ub2c8\uc800",
      reviewer: "\ub9ac\ubdf0\uc5b4",
      employee: "\uba64\ubc84",
    };
    const role = currentUser ? (roleLabels[currentUser.role] ?? currentUser.role) : "\uacc4\uc815 \uc5c6\uc74c";
    const initial = name.trim().charAt(0).toUpperCase() || "?";
    const avatarFileName = currentUser?.email.split("@", 1)[0]?.trim().toLowerCase();
    const fallbackAvatarUrl = avatarFileName ? `/profile/${avatarFileName}.png` : null;
    const avatarUrl = currentUser?.role === "admin" ? null : (currentUser?.avatar_url ?? fallbackAvatarUrl);
    return { name, role, initial, avatarUrl };
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
            <img src="/assets/paraworks-logo-icon.png" alt="" />
          </span>
          <span className="min-w-0 pt-0.5">
            <span className="brand-wordmark block text-[19px] leading-6 text-[#173a96]">paraworks</span>
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

        <div className="relative mt-4 flex items-center justify-between rounded-lg bg-[#fafafa] p-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="avatar-photo" aria-hidden="true">
              {accountDisplay.avatarUrl ? <img src={accountDisplay.avatarUrl} alt="" /> : accountDisplay.initial}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-bold text-ink">{accountDisplay.name}</span>
              <span className="block text-[11px] text-muted">{accountDisplay.role}</span>
            </span>
          </div>
          <button
            type="button"
            className="icon-button small"
            aria-label={"\uacc4\uc815 \uba54\ub274"}
            aria-expanded={accountMenuOpen}
            onClick={() => setAccountMenuOpen((open) => !open)}
          >
            <Settings className="h-4 w-4" aria-hidden="true" />
          </button>

          {accountMenuOpen ? (
            <div className="absolute bottom-full right-0 z-40 mb-2 w-36 rounded-lg border border-line bg-white p-1 shadow-lg">
              <button
                type="button"
                className="w-full rounded-md px-3 py-2 text-left text-[13px] font-bold text-ink hover:bg-[#f3f7fd]"
                onClick={() => {
                  setAccountMenuOpen(false);
                  router.push("/account");
                }}
              >
                {"\ub0b4 \uacc4\uc815"}
              </button>
              <button
                type="button"
                className="w-full rounded-md px-3 py-2 text-left text-[13px] font-bold text-red-600 hover:bg-red-50"
                onClick={() => void logout()}
              >
                {"\ub85c\uadf8\uc544\uc6c3"}
              </button>
            </div>
          ) : null}
        </div>
      </aside>

      <div className="lg:pl-[216px]">
        <header className="sticky top-0 z-20 bg-app/95 px-4 py-4 backdrop-blur md:px-6 lg:px-6">
          <div className="flex items-center justify-between gap-4">
            <Link href="/dashboard" className="flex items-center gap-2 lg:hidden">
              <span className="brand-logo small" aria-hidden="true">
                <img src="/assets/paraworks-logo-icon.png" alt="" />
              </span>
              <span className="brand-wordmark text-[#173a96]">paraworks</span>
            </Link>

            <form onSubmit={submitSearch} className="top-search ml-auto min-w-0 flex-1 md:max-w-[470px]">
              <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
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
