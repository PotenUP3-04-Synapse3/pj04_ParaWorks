"use client";

import { CheckCircle2, LogIn, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import {
  DEMO_USER_STORAGE_KEY,
  apiGet,
  apiPost,
  clearStoredDemoUserId,
  getStoredDemoUserId,
  setStoredDemoUserId,
} from "@/lib/api/client";
import type { AuthUserResponse, AuthUsersResponse, DemoUser, GoogleLoginUrlResponse } from "@/lib/api/types";

const text = {
  title: "Login",
  eyebrow: "ParaWorks Identity",
  description:
    "Sign in with an invited Google account. Gmail, Drive, and Calendar data access stays separate from identity login.",
  googleLogin: "Continue with Google",
  googleUnavailable: "Google login is not fully configured yet.",
  redirectUri: "Redirect URI",
  missingConfig: "Missing configuration",
  demoAccounts: "Demo accounts",
  demoDescription: "Use local demo accounts to compare role and permission behavior without paid API calls.",
  loadError: "Could not load account information.",
  loginError: "Login failed. Check whether the account is invited.",
  logoutError: "Logout failed.",
  switched: "is now active.",
  loggedOut: "Logged out. Choose the account to use next.",
  current: "Current",
  role: "Role",
  loginAs: "Use this account",
  logout: "Logout",
};

export default function LoginPage() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [googleLogin, setGoogleLogin] = useState<GoogleLoginUrlResponse>();
  const [currentUserId, setCurrentUserId] = useState("hanvv-employee");
  const [status, setStatus] = useState<string>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    setCurrentUserId(getStoredDemoUserId());
    Promise.all([
      apiGet<AuthUsersResponse>("/api/v1/auth/login-options"),
      apiGet<GoogleLoginUrlResponse>("/api/v1/auth/google/login-url"),
    ])
      .then(([optionsResult, googleResult]) => {
        setUsers(optionsResult.users);
        setGoogleLogin(googleResult);
      })
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

  async function logout() {
    setError(undefined);
    setStatus(undefined);

    try {
      await apiPost<{ status: string }>("/api/v1/auth/logout");
      clearStoredDemoUserId();
      setCurrentUserId(getStoredDemoUserId());
      window.dispatchEvent(new StorageEvent("storage", { key: DEMO_USER_STORAGE_KEY, newValue: null }));
      setStatus(text.loggedOut);
    } catch {
      setError(text.logoutError);
    }
  }

  function startGoogleLogin() {
    if (!googleLogin?.configured || !googleLogin.login_url) {
      setError(text.googleUnavailable);
      return;
    }

    window.location.assign(googleLogin.login_url);
  }

  const adminUsers = users.filter((user) => user.role === "admin");
  const nonAdminUsers = users.filter((user) => user.role !== "admin");

  return (
    <div className="space-y-5">
      <section className="liquid-surface rounded-[32px] p-5 md:p-7">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">{text.eyebrow}</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">{text.title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">{text.description}</p>
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            className="liquid-control inline-flex w-fit items-center gap-2 rounded-[24px] px-4 py-3 text-sm font-semibold text-[var(--ink-muted)]"
          >
            <LogOut className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
            {text.logout}
          </button>
        </div>
      </section>

      <section className="liquid-surface rounded-[30px] p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <h2 className="text-lg font-semibold">Google Identity</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--ink-muted)]">
              Only invited Google emails are mapped to ParaWorks users.
            </p>
          </div>
          <button
            type="button"
            onClick={startGoogleLogin}
            className="liquid-primary inline-flex h-11 items-center justify-center gap-2 rounded-[24px] px-5 text-sm font-semibold"
          >
            <LogIn className="h-4 w-4" aria-hidden="true" />
            {text.googleLogin}
          </button>
        </div>
        <GoogleIdentityReadiness googleLogin={googleLogin} />
      </section>

      {status ? (
        <div className="liquid-control flex items-center gap-2 rounded-[22px] px-4 py-3 text-sm text-[var(--ink-strong)]">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
          {status}
        </div>
      ) : null}
      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div> : null}

      {users.length ? (
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">{text.demoAccounts}</h2>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">{text.demoDescription}</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {adminUsers.map((user) => (
              <AccountCard key={user.id} user={user} currentUserId={currentUserId} onLogin={() => void login(user)} featured />
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {nonAdminUsers.map((user) => (
              <AccountCard key={user.id} user={user} currentUserId={currentUserId} onLogin={() => void login(user)} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function GoogleIdentityReadiness({ googleLogin }: { googleLogin?: GoogleLoginUrlResponse }) {
  if (!googleLogin) {
    return null;
  }

  return (
    <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
      <div className="liquid-control rounded-[22px] p-3">
        <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">{text.redirectUri}</p>
        <p className="mt-1 break-all font-mono text-xs text-[var(--ink-strong)]">
          {googleLogin.redirect_uri || "not configured"}
        </p>
      </div>
      <div className="liquid-control rounded-[22px] p-3">
        <p className="text-xs font-semibold uppercase text-[var(--ink-muted)]">{text.missingConfig}</p>
        {googleLogin.configured ? (
          <p className="mt-1 text-sm font-semibold text-emerald-500">Ready</p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            {(googleLogin.missing_config?.length ? googleLogin.missing_config : ["GOOGLE_IDENTITY_CONFIGURATION"]).map(
              (item) => (
                <span key={item} className="rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-500">
                  {item}
                </span>
              ),
            )}
          </div>
        )}
      </div>
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
        <div className="flex min-w-0 items-center gap-3">
          <div className="liquid-primary grid h-11 w-11 shrink-0 place-items-center rounded-[22px]">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold">{user.name}</h2>
            <p className="truncate text-sm text-[var(--ink-muted)]">{user.email}</p>
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
          <span className="font-semibold text-[var(--ink-strong)]">{user.department}</span> / {user.title}
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
