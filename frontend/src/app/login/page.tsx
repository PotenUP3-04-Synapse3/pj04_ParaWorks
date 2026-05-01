"use client";

import { CheckCircle2, LogIn, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import {
  DEMO_USER_STORAGE_KEY,
  apiGet,
  apiPost,
  getStoredDemoUserId,
  setStoredDemoUserId,
} from "@/lib/api/client";
import type { AuthUserResponse, AuthUsersResponse, DemoUser } from "@/lib/api/types";

const text = {
  title: "\uB85C\uADF8\uC778",
  description:
    "MVP \uB2E8\uACC4\uC5D0\uC11C\uB294 \uBE44\uBC00\uBC88\uD638 \uC5C6\uC774 \uB370\uBAA8 \uACC4\uC815\uC744 \uC804\uD658\uD569\uB2C8\uB2E4. \uBAA8\uB4E0 API \uC694\uCCAD\uC740 \uC120\uD0DD\uB41C \uACC4\uC815\uC758 \uAD8C\uD55C \uD5E4\uB354\uB97C \uC0AC\uC6A9\uD569\uB2C8\uB2E4.",
  loadError: "\uB370\uBAA8 \uACC4\uC815 \uBAA9\uB85D\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
  loginError:
    "\uB85C\uADF8\uC778\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4. \uACC4\uC815 \uC774\uBA54\uC77C\uC744 \uD655\uC778\uD574\uC8FC\uC138\uC694.",
  switched: "\uACC4\uC815\uC73C\uB85C \uC804\uD658\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
  current: "\uD604\uC7AC",
  role: "\uC5ED\uD560",
  loginAs: "\uC774 \uACC4\uC815\uC73C\uB85C \uB85C\uADF8\uC778",
};

export default function LoginPage() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [currentUserId, setCurrentUserId] = useState("admin");
  const [status, setStatus] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    setCurrentUserId(getStoredDemoUserId());
    apiGet<AuthUsersResponse>("/api/v1/auth/login-options")
      .then((result) => setUsers(result.users))
      .catch(() => setError(text.loadError));
  }, []);

  async function login(user: DemoUser) {
    setError(undefined);
    setStatus(undefined);

    try {
      const result = await apiPost<AuthUserResponse>("/api/v1/auth/login", { email: user.email });
      setStoredDemoUserId(result.user.id);
      setCurrentUserId(result.user.id);
      window.dispatchEvent(new StorageEvent("storage", { key: DEMO_USER_STORAGE_KEY, newValue: result.user.id }));
      setStatus(`${result.user.name} ${text.switched}`);
    } catch {
      setError(text.loginError);
    }
  }

  const adminUser = users.find((user) => user.role === "admin");
  const employeeUsers = users.filter((user) => user.role !== "admin");

  return (
    <div className="space-y-5">
      <section className="liquid-surface rounded-[32px] p-5 md:p-7">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Demo Access</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">{text.title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">{text.description}</p>
          </div>
          <div className="liquid-control inline-flex w-fit items-center gap-2 rounded-[24px] px-4 py-3 text-sm font-semibold text-[var(--ink-muted)]">
            <LogIn className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            {currentUserId}
          </div>
        </div>
      </section>

      {status ? (
        <div className="liquid-control flex items-center gap-2 rounded-[22px] px-4 py-3 text-sm text-[var(--ink-strong)]">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
          {status}
        </div>
      ) : null}
      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div> : null}

      {adminUser ? (
        <AccountCard user={adminUser} currentUserId={currentUserId} onLogin={() => void login(adminUser)} featured />
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        {employeeUsers.map((user) => (
          <AccountCard key={user.id} user={user} currentUserId={currentUserId} onLogin={() => void login(user)} />
        ))}
      </section>
    </div>
  );
}

function AccountCard({
  user,
  currentUserId,
  onLogin,
  featured = false,
}: {
  user: DemoUser;
  currentUserId: string;
  onLogin: () => void;
  featured?: boolean;
}) {
  const active = currentUserId === user.id || currentUserId === user.email;
  const Icon = user.role === "admin" ? ShieldCheck : UserRound;

  return (
    <article className={`liquid-surface rounded-[30px] p-5 ${featured ? "border-[var(--workspace-accent)]" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="liquid-primary grid h-11 w-11 place-items-center rounded-[22px]">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold">{user.name}</h2>
            <p className="text-sm text-[var(--ink-muted)]">{user.email}</p>
          </div>
        </div>
        {active ? (
          <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-500">
            {text.current}
          </span>
        ) : null}
      </div>
      <div className="mt-4 grid gap-2 text-sm text-[var(--ink-muted)]">
        <p>
          <span className="font-semibold text-[var(--ink-strong)]">{user.department}</span> · {user.title}
        </p>
        <p>
          {text.role}: {user.role}
        </p>
        <div className="flex flex-wrap gap-2">
          {user.permission_levels.map((level) => (
            <span key={level} className="liquid-control rounded-full px-3 py-1 text-xs font-semibold">
              {level}
            </span>
          ))}
        </div>
      </div>
      <button
        type="button"
        onClick={onLogin}
        className="liquid-primary mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-[24px] text-sm font-semibold"
      >
        <LogIn className="h-4 w-4" aria-hidden="true" />
        {text.loginAs}
      </button>
    </article>
  );
}
