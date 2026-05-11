"use client";

import { AlertTriangle, BadgeCheck, Building2, IdCard, LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { AuthUserResponse, DemoUser } from "@/lib/api/types";

const roleLabels: Record<string, string> = {
  admin: "\uad00\ub9ac\uc790",
  manager: "\ub9e4\ub2c8\uc800",
  reviewer: "\ub9ac\ubdf0\uc5b4",
  employee: "\uba64\ubc84",
};

const permissionLabels: Record<string, string> = {
  public: "\uacf5\uac1c",
  internal: "\ub0b4\ubd80",
  restricted: "\uc81c\ud55c",
};

const copy = {
  loading: "\uacc4\uc815 \uc815\ubcf4\ub97c \ubd88\ub7ec\uc624\ub294 \uc911\uc785\ub2c8\ub2e4.",
  loginRequired: "\ub85c\uadf8\uc778 \ud544\uc694",
  loginAction: "\ub85c\uadf8\uc778\ud558\uae30",
  accountLabel: "Account",
  accountTitle: "\ub0b4 \uacc4\uc815",
  accountDescription: "\ud604\uc7ac \ub85c\uadf8\uc778\ub41c \uacc4\uc815\uc758 \uc5ed\ud560, \ubd80\uc11c, \uc811\uadfc \uad8c\ud55c\uc744 \ud655\uc778\ud569\ub2c8\ub2e4.",
  permissionScope: "\uad8c\ud55c \ubc94\uc704",
};

export default function AccountPage() {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiGet<AuthUserResponse>("/api/v1/auth/me")
      .then((result) => {
        if (active) {
          setUser(result.user);
          setError(undefined);
        }
      })
      .catch(() => {
        if (active) {
          setError("\uacc4\uc815 \uc815\ubcf4\ub97c \ud655\uc778\ud558\ub824\uba74 \ub85c\uadf8\uc778\uc774 \ud544\uc694\ud569\ub2c8\ub2e4.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const accountDisplay = useMemo(() => {
    const name = user?.name ?? "";
    const localPart = user?.email.split("@", 1)[0]?.trim().toLowerCase();
    const fallbackAvatarUrl = localPart ? `/profile/${localPart}.png` : null;
    const avatarUrl = user?.role === "admin" ? null : (user?.avatar_url ?? fallbackAvatarUrl);
    const initial = name.trim().charAt(0).toUpperCase() || "?";
    return {
      avatarUrl,
      initial,
      role: user ? (roleLabels[user.role] ?? user.role) : "",
      status: user?.status === "suspended" ? "\uc815\uc9c0" : "\ud65c\uc131",
    };
  }, [user]);

  if (loading) {
    return <div className="rounded-lg border border-line bg-[var(--glass-elevated)] p-5 text-sm text-muted shadow-sm">{copy.loading}</div>;
  }

  if (error || !user) {
    return (
      <div className="space-y-4">
        <section className="rounded-lg border border-line bg-[var(--glass-elevated)] p-6 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-500" aria-hidden="true" />
            <div>
              <h1 className="text-xl font-bold text-ink">{copy.loginRequired}</h1>
              <p className="mt-2 text-sm leading-6 text-muted">{error}</p>
            </div>
          </div>
        </section>
        <Link href="/login" className="inline-flex h-10 items-center justify-center rounded-lg bg-[var(--primary)] px-4 text-sm font-bold text-white">
          {copy.loginAction}
        </Link>
      </div>
    );
  }

  const details = [
    { label: "\uc774\uba54\uc77c", value: user.email, icon: Mail },
    { label: "\uc5ed\ud560", value: accountDisplay.role, icon: ShieldCheck },
    { label: "\uc9c1\ucc45", value: user.title, icon: IdCard },
    { label: "\ubd80\uc11c", value: user.department, icon: Building2 },
    { label: "\uc0c1\ud0dc", value: accountDisplay.status, icon: BadgeCheck },
    { label: "\uacc4\uc815 ID", value: user.id, icon: UserRound },
  ];

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-lg border border-line bg-[var(--glass-elevated)] shadow-panel">
        <div className="border-b border-line px-5 py-4">
          <p className="text-xs font-bold uppercase text-[var(--primary-dark)]">{copy.accountLabel}</p>
          <h1 className="mt-1 text-2xl font-bold text-ink">{user.name}</h1>
          <p className="mt-2 text-sm text-muted">{copy.accountDescription}</p>
        </div>

        <div className="grid gap-5 p-5 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="rounded-lg border border-line bg-[var(--glass-strong)] p-5">
            <div className="flex flex-col items-center text-center">
              <span className="grid h-36 w-36 place-items-center overflow-hidden rounded-full bg-gradient-to-br from-[#7c2d12] to-[#f0c0a5] text-4xl font-extrabold text-white">
                {accountDisplay.avatarUrl ? (
                  <Image src={accountDisplay.avatarUrl} alt="" width={144} height={144} className="h-full w-full object-cover" />
                ) : (
                  accountDisplay.initial
                )}
              </span>
              <h2 className="mt-4 text-xl font-bold text-ink">{user.name}</h2>
              <p className="mt-1 text-sm text-muted">{accountDisplay.role}</p>
              <div className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-line bg-[var(--glass-elevated)] px-3 py-1 text-xs font-bold text-[var(--primary-dark)]">
                <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
                {accountDisplay.status}
              </div>
            </div>
          </aside>

          <section className="grid gap-3 md:grid-cols-2">
            {details.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4 shadow-sm">
                  <div className="flex items-center gap-2 text-xs font-bold text-muted">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </div>
                  <p className="mt-2 break-words text-sm font-bold text-ink">{item.value}</p>
                </div>
              );
            })}
            <div className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4 shadow-sm md:col-span-2">
              <div className="flex items-center gap-2 text-xs font-bold text-muted">
                <LockKeyhole className="h-4 w-4" aria-hidden="true" />
                {copy.permissionScope}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {user.permission_levels.map((permission) => (
                  <span key={permission} className="rounded-full border border-line bg-[var(--glass-strong)] px-3 py-1 text-xs font-bold text-[var(--primary-dark)]">
                    {permissionLabels[permission] ?? permission}
                  </span>
                ))}
              </div>
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}
