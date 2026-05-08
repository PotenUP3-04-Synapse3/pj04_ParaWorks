"use client";

import { CheckCircle2, Eye, LockKeyhole, LogIn, Mail, ShieldCheck, UserRound } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  DEMO_USER_STORAGE_KEY,
  apiGet,
  apiPost,
  clearStoredDemoUserId,
  getStoredDemoUserId,
  setStoredDemoUserId,
} from "@/lib/api/client";
import type { AuthUserResponse, AuthUsersResponse, DemoUser, GoogleLoginUrlResponse } from "@/lib/api/types";

const LOCAL_DEMO_USERS: DemoUser[] = [
  {
    id: "demo-admin",
    email: "admin@paraworks.com",
    role: "admin",
    permission_levels: ["public", "internal", "restricted"],
    name: "ParaWorks Admin",
    title: "Workspace Administrator",
    department: "Platform",
  },
  {
    id: "google-hanvv-admin",
    email: "hanvv3@gmail.com",
    role: "admin",
    permission_levels: ["public", "internal", "restricted"],
    name: "Hanvv Admin",
    title: "Workspace Administrator",
    department: "Platform",
  },
  {
    id: "google-hanvv-employee",
    email: "hanvv3@koreacu.ac.kr",
    role: "employee",
    permission_levels: ["public", "internal"],
    name: "Hanvv Employee",
    title: "AI Agent Developer",
    department: "Engineering",
  },
  {
    id: "employee-mina",
    email: "mina@paraworks.com",
    role: "reviewer",
    permission_levels: ["public", "internal"],
    name: "Kim Mina",
    title: "Product Manager",
    department: "Product",
  },
  {
    id: "employee-jun",
    email: "jun@paraworks.com",
    role: "employee",
    permission_levels: ["public", "internal"],
    name: "Lee Jun",
    title: "Backend Engineer",
    department: "Engineering",
  },
  {
    id: "employee-soyeon",
    email: "soyeon@paraworks.com",
    role: "employee",
    permission_levels: ["public"],
    name: "Park Soyeon",
    title: "Operations Associate",
    department: "Operations",
  },
];

export default function LoginPage() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [googleLogin, setGoogleLogin] = useState<GoogleLoginUrlResponse>();
  const [currentUserId, setCurrentUserId] = useState("hanvv-employee");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<string>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setCurrentUserId(getStoredDemoUserId());
    Promise.all([
      apiGet<AuthUsersResponse>("/api/v1/auth/login-options"),
      apiGet<GoogleLoginUrlResponse>("/api/v1/auth/google/login-url"),
    ])
      .then(([optionsResult, googleResult]) => {
        setUsers(optionsResult.users.length ? optionsResult.users : LOCAL_DEMO_USERS);
        setGoogleLogin(googleResult);
        setEmail((optionsResult.users[0] ?? LOCAL_DEMO_USERS[0])?.email ?? "");
      })
      .catch(() => {
        setUsers(LOCAL_DEMO_USERS);
        setEmail(LOCAL_DEMO_USERS[0].email);
        setError("백엔드 API에 연결할 수 없어 로컬 데모 계정 목록을 사용합니다.");
      });
  }, []);

  const selectedUser = useMemo(
    () => users.find((user) => user.email.toLowerCase() === email.trim().toLowerCase()),
    [email, users],
  );

  async function loginWithEmail(nextEmail: string) {
    setLoading(true);
    setError(undefined);
    setStatus(undefined);

    try {
      const result = await apiPost<AuthUserResponse>("/api/v1/auth/login", { email: nextEmail });
      setStoredDemoUserId(result.user.id);
      setCurrentUserId(result.user.id);
      window.dispatchEvent(new StorageEvent("storage", { key: DEMO_USER_STORAGE_KEY, newValue: result.user.id }));
      setStatus(`${result.user.name} 계정으로 로그인했습니다.`);
      window.location.assign("/dashboard");
    } catch {
      const fallbackUser = users.find((user) => user.email.toLowerCase() === nextEmail.toLowerCase());
      if (!fallbackUser) {
        setError("로그인에 실패했습니다. 초대된 데모 계정 이메일인지 확인해 주세요.");
        return;
      }

      setStoredDemoUserId(fallbackUser.id);
      setCurrentUserId(fallbackUser.id);
      window.dispatchEvent(new StorageEvent("storage", { key: DEMO_USER_STORAGE_KEY, newValue: fallbackUser.id }));
      setStatus(`${fallbackUser.name} 계정으로 로그인했습니다. 백엔드 세션 쿠키는 생성되지 않았습니다.`);
      window.location.assign("/dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextEmail = email.trim();
    if (!nextEmail || loading) return;
    await loginWithEmail(nextEmail);
  }

  async function logout() {
    setError(undefined);
    setStatus(undefined);
    try {
      await apiPost<{ status: string }>("/api/v1/auth/logout");
      clearStoredDemoUserId();
      setCurrentUserId(getStoredDemoUserId());
      window.dispatchEvent(new StorageEvent("storage", { key: DEMO_USER_STORAGE_KEY, newValue: null }));
      setStatus("로그아웃했습니다. 사용할 계정을 선택해 주세요.");
    } catch {
      setError("로그아웃에 실패했습니다.");
    }
  }

  function startGoogleLogin() {
    if (!googleLogin?.configured || !googleLogin.login_url) {
      setError("Google 로그인이 아직 설정되지 않았습니다.");
      return;
    }
    window.location.assign(googleLogin.login_url);
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <aside className="login-brand-panel">
          <div className="login-brand-lockup">
            <img src="/assets/paraworks-logo-icon.png" alt="" />
            <span className="brand-wordmark">paraworks</span>
          </div>
          <div>
            <h1>회사 모든 기록을 연결해, 더 나은 일의 흐름을 만듭니다.</h1>
            <p>모든 팀과 데이터가 하나로 연결되는 스마트 협업 플랫폼</p>
          </div>
          <div className="login-cube-scene" aria-hidden="true">
            <span className="cube large" />
            <span className="cube medium" />
            <span className="cube small" />
            <span className="dot-grid" />
          </div>
        </aside>

        <section className="login-form-panel">
          <div className="login-form-inner">
            <div>
              <h2>로그인</h2>
              <p>ParaWorks 계정으로 로그인하세요.</p>
            </div>

            <form onSubmit={submit} className="login-form">
              <label htmlFor="login-email">이메일</label>
              <div className="login-input">
                <Mail className="h-5 w-5" aria-hidden="true" />
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="이메일 주소를 입력하세요"
                  autoComplete="email"
                />
              </div>

              <label htmlFor="login-password">비밀번호</label>
              <div className="login-input">
                <LockKeyhole className="h-5 w-5" aria-hidden="true" />
                <input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="데모 로그인에서는 확인하지 않습니다"
                  autoComplete="current-password"
                />
                <Eye className="h-5 w-5" aria-hidden="true" />
              </div>

              <div className="login-options-row">
                <label className="login-checkbox">
                  <input type="checkbox" />
                  로그인 상태 유지
                </label>
                <button type="button" onClick={() => void logout()}>
                  로그아웃
                </button>
              </div>

              <button type="submit" className="login-submit" disabled={loading || !email.trim()}>
                {loading ? "로그인 중" : "로그인"}
              </button>
            </form>

            <div className="login-divider">
              <span />
              <b>또는</b>
              <span />
            </div>

            <button type="button" className="google-login-button" onClick={startGoogleLogin}>
              <span>G</span>
              Google 계정으로 로그인
            </button>

            {selectedUser ? (
              <div className="selected-account">
                <div>
                  <strong>{selectedUser.name}</strong>
                  <span>{selectedUser.role} · {selectedUser.department}</span>
                </div>
                {currentUserId === selectedUser.id || currentUserId === selectedUser.email ? (
                  <span className="current-badge">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    현재
                  </span>
                ) : null}
              </div>
            ) : null}

            {users.length ? (
              <div className="demo-account-list">
                {users.map((user) => (
                  <button
                    key={user.id}
                    type="button"
                    onClick={() => {
                      setEmail(user.email);
                      setPassword("");
                    }}
                    className={email === user.email ? "active" : ""}
                  >
                    {user.role === "admin" ? <ShieldCheck className="h-4 w-4" /> : <UserRound className="h-4 w-4" />}
                    <span>{user.email}</span>
                  </button>
                ))}
              </div>
            ) : null}

            {status ? <div className="login-status success">{status}</div> : null}
            {error ? <div className="login-status error">{error}</div> : null}

            <p className="signup-line">
              계정이 없으신가요? <span>회원 가입</span>
            </p>
          </div>
        </section>
      </section>

      <footer className="login-footer">
        <p>© 2026 Synapse3 Inc. All rights reserved.</p>
        <p>개인정보처리방침 <span>|</span> 이용약관 <span>|</span> 고객센터</p>
      </footer>
    </main>
  );
}
