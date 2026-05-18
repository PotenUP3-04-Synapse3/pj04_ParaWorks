"use client";

import { AlertTriangle, LockKeyhole, ScrollText, ShieldCheck, UserCog, UsersRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch } from "@/lib/api/client";
import type { AuditLog, AuditLogsResponse, AuthUserResponse, AuthUsersResponse, DemoUser } from "@/lib/api/types";

const text = {
  loading: "\uAD00\uB9AC\uC790 \uCF58\uC194\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\uC785\uB2C8\uB2E4.",
  permissionRequired: "\uAD00\uB9AC\uC790 \uAD8C\uD55C \uD544\uC694",
  permissionDescription:
    "\uC774 \uD654\uBA74\uC740 \uC6CC\uD06C\uC2A4\uD398\uC774\uC2A4 \uAD00\uB9AC\uC790\uB9CC \uC811\uADFC\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uB370\uBAA8\uC5D0\uC11C\uB294 \uAD00\uB9AC\uC790 \uACC4\uC815\uC73C\uB85C \uC804\uD658\uD558\uBA74 \uC0AC\uC6A9\uC790\uC640 \uAD8C\uD55C \uBC94\uC704\uB97C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.",
  loginAsAdmin: "\uAD00\uB9AC\uC790 \uACC4\uC815\uC73C\uB85C \uB85C\uADF8\uC778",
  title: "\uAD00\uB9AC\uC790 \uCF58\uC194",
  description:
    "ParaWorks\uC758 \uB370\uBAA8 \uC0AC\uC6A9\uC790, \uC5ED\uD560, \uBB38\uC11C \uC811\uADFC \uB808\uBCA8\uC744 \uD55C \uACF3\uC5D0\uC11C \uD655\uC778\uD569\uB2C8\uB2E4. \uC774\uD6C4 \uC2E4\uC81C \uC870\uC9C1 \uACC4\uC815, OAuth, \uAC10\uC0AC \uB85C\uADF8 \uAD8C\uD55C \uBAA8\uB378\uB85C \uD655\uC7A5\uD558\uAE30 \uC704\uD55C \uAE30\uBC18\uC785\uB2C8\uB2E4.",
  total: "\uC804\uCCB4 \uACC4\uC815",
  admins: "\uAD00\uB9AC\uC790",
  employees: "\uC0AC\uC6D0 \uACC4\uC815",
  restrictedAccess: "Restricted \uC811\uADFC",
  usersAndPermissions: "\uC0AC\uC6A9\uC790\uC640 \uAD8C\uD55C",
  permissionNote:
    "\uAC80\uC0C9, RAG \uB2F5\uBCC0, \uAD00\uB9AC\uC790 API\uAC00 \uAC19\uC740 \uAD8C\uD55C \uB808\uBCA8\uC744 \uC0AC\uC6A9\uD569\uB2C8\uB2E4.",
  auditLogs: "\uAC10\uC0AC \uB85C\uADF8",
  auditNote:
    "\uB3D9\uAE30\uD654, AI \uC2E4\uD589, \uB9AC\uBDF0 \uC2B9\uC778, RAG \uC7AC\uC0C9\uC778 \uAC19\uC740 \uC8FC\uC694 \uC6B4\uC601 \uD589\uC704\uB97C \uB0A8\uAE41\uB2C8\uB2E4.",
  noAuditLogs: "\uC544\uC9C1 \uAE30\uB85D\uB41C \uAC10\uC0AC \uB85C\uADF8\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
  account: "\uACC4\uC815",
  role: "\uC5ED\uD560",
  department: "\uBD80\uC11C",
  scope: "\uAD8C\uD55C \uBC94\uC704",
  saveError: "사용자 권한을 변경하지 못했습니다.",
  action: "\uD589\uC704",
  target: "\uB300\uC0C1",
  actor: "\uC0AC\uC6A9\uC790",
  status: "\uC0C1\uD0DC",
  time: "\uC2DC\uAC01",
};

const ROLE_OPTIONS = ["employee", "reviewer", "manager", "admin"] as const;
const STATUS_OPTIONS = ["active", "suspended"] as const;
const PERMISSION_OPTIONS = ["public", "internal", "restricted"] as const;

export default function AdminPage() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [savingUserId, setSavingUserId] = useState<string>();

  async function loadAdminData(active = true) {
    try {
      const currentUser = await apiGet<AuthUserResponse>("/api/v1/auth/me");
      if (currentUser.user.role !== "admin") {
        if (active) {
          setError(text.permissionRequired);
          setLoading(false);
        }
        return;
      }

      const [usersResult, auditResult] = await Promise.all([
        apiGet<AuthUsersResponse>("/api/v1/admin/users"),
        apiGet<AuditLogsResponse>("/api/v1/admin/audit-logs?limit=8"),
      ]);
      if (active) {
        setUsers(usersResult.users);
        setAuditLogs(auditResult.logs);
        setError(undefined);
      }
    } catch {
      if (active) {
        setError(text.permissionRequired);
      }
    } finally {
      if (active) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    let active = true;

    void loadAdminData(active);

    return () => {
      active = false;
    };
  }, []);

  async function updateUser(user: DemoUser, update: Partial<Pick<DemoUser, "role" | "status" | "permission_levels">>) {
    setSavingUserId(user.id);
    setError(undefined);
    try {
      const result = await apiPatch<{ user: DemoUser }>(`/api/v1/admin/users/${encodeURIComponent(user.id)}`, update);
      setUsers((current) => current.map((row) => (row.id === user.id ? result.user : row)));
      const auditResult = await apiGet<AuditLogsResponse>("/api/v1/admin/audit-logs?limit=8");
      setAuditLogs(auditResult.logs);
    } catch {
      setError(text.saveError);
    } finally {
      setSavingUserId(undefined);
    }
  }

  const metrics = useMemo(() => {
    const adminCount = users.filter((user) => user.role === "admin").length;
    const restrictedCount = users.filter((user) => user.permission_levels.includes("restricted")).length;
    return {
      total: users.length,
      adminCount,
      employeeCount: users.length - adminCount,
      restrictedCount,
    };
  }, [users]);

  if (loading) {
    return <div className="panel reference-panel utility-workspace text-sm text-muted">{text.loading}</div>;
  }

  if (error) {
    return (
      <div className="reference-dashboard utility-workspace space-y-5">
        <section className="panel reference-panel">
          <div className="flex items-start gap-3">
            <span className="source-icon calendar">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            </span>
            <div>
              <p className="text-[13px] font-bold text-[var(--primary-dark)]">Workspace Admin</p>
              <h1 className="mt-1 text-2xl font-extrabold tracking-normal text-ink">{error}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{text.permissionDescription}</p>
            </div>
          </div>
        </section>
        <Link
          href="/login"
          className="primary-action w-fit px-5"
        >
          {text.loginAsAdmin}
        </Link>
      </div>
    );
  }

  return (
    <div className="reference-dashboard utility-workspace space-y-5">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Workspace Admin</p>
          <h1>{text.title}</h1>
          <p>{text.description}</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold text-[var(--ink-subtle)]">
          <ShieldCheck className="h-4 w-4 text-[var(--success)]" aria-hidden="true" />
          Admin verified
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <MetricCard label={text.total} value={metrics.total} icon={UsersRound} detail="registered users" />
        <MetricCard label={text.admins} value={metrics.adminCount} icon={ShieldCheck} detail="workspace admins" />
        <MetricCard label={text.employees} value={metrics.employeeCount} icon={UserCog} detail="non-admin accounts" />
        <MetricCard label={text.restrictedAccess} value={metrics.restrictedCount} icon={LockKeyhole} detail="restricted scope" />
      </section>

      <section className="panel reference-panel overflow-hidden p-0">
        <div className="activity-toolbar px-5 py-4">
          <div>
            <div className="reference-panel-title">
              <h2>{text.usersAndPermissions}</h2>
              <span>{users.length.toLocaleString("ko-KR")}</span>
            </div>
            <p className="mt-1 text-[13px] leading-5 text-muted">{text.permissionNote}</p>
          </div>
          <div className="toolbar-actions">
            <button type="button" aria-disabled="true">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              RBAC active
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="admin-table w-full min-w-[900px] text-left text-sm">
            <thead>
              <tr>
                <th>{text.account}</th>
                <th>{text.role}</th>
                <th>{text.status}</th>
                <th>{text.department}</th>
                <th>{text.scope}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>
                    <p className="font-extrabold text-ink">{user.name}</p>
                    <p className="mt-1 text-xs text-muted">{user.email}</p>
                  </td>
                  <td>
                    <select
                      value={user.role}
                      disabled={savingUserId === user.id}
                      onChange={(event) => void updateUser(user, { role: event.target.value })}
                      className="admin-select"
                      aria-label={`${user.email} role`}
                    >
                      {ROLE_OPTIONS.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      value={user.status ?? "active"}
                      disabled={savingUserId === user.id}
                      onChange={(event) => void updateUser(user, { status: event.target.value })}
                      className="admin-select"
                      aria-label={`${user.email} status`}
                    >
                      {STATUS_OPTIONS.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <p className="font-bold text-ink">{user.department}</p>
                    <p className="mt-1 text-xs text-muted">{user.title}</p>
                  </td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      {PERMISSION_OPTIONS.map((level) => {
                        const enabled = user.permission_levels.includes(level);
                        const nextLevels = enabled
                          ? user.permission_levels.filter((item) => item !== level)
                          : [...user.permission_levels, level];
                        return (
                        <button
                          type="button"
                          key={level}
                          disabled={savingUserId === user.id}
                          onClick={() => void updateUser(user, { permission_levels: nextLevels })}
                          className={`admin-permission-pill ${
                            enabled
                              ? "active"
                              : ""
                          }`}
                        >
                          {level}
                        </button>
                        );
                      })}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel reference-panel overflow-hidden p-0">
        <div className="activity-toolbar px-5 py-4">
          <div>
            <div className="reference-panel-title">
              <h2>{text.auditLogs}</h2>
              <span>{auditLogs.length.toLocaleString("ko-KR")}</span>
            </div>
            <p className="mt-1 text-[13px] leading-5 text-muted">{text.auditNote}</p>
          </div>
          <div className="hidden items-center gap-2 rounded-lg border border-line bg-surface-soft px-3 py-2 text-xs font-bold text-[var(--ink-subtle)] md:inline-flex">
            <ScrollText className="h-4 w-4" aria-hidden="true" />
            {auditLogs.length.toLocaleString()}
          </div>
        </div>
        {auditLogs.length ? (
          <div className="overflow-x-auto">
            <table className="admin-table w-full min-w-[860px] text-left text-sm">
              <thead>
                <tr>
                  <th>{text.action}</th>
                  <th>{text.target}</th>
                  <th>{text.actor}</th>
                  <th>{text.status}</th>
                  <th>{text.time}</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>
                      <p className="font-extrabold text-ink">{formatAction(log.action)}</p>
                      <p className="mt-1 text-xs text-muted">{metadataSummary(log.metadata)}</p>
                    </td>
                    <td>
                      <p className="font-bold text-ink">{log.target_type}</p>
                      <p className="mt-1 text-xs text-muted">{log.target_id ?? "-"}</p>
                    </td>
                    <td>
                      <p className="font-bold text-ink">{log.actor_email}</p>
                      <p className="mt-1 text-xs text-muted">{log.actor_role}</p>
                    </td>
                    <td>
                      <span className="admin-status-pill">{log.status}</span>
                    </td>
                    <td className="text-xs text-muted">{formatDate(log.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="px-5 py-6 text-sm text-muted">{text.noAuditLogs}</p>
        )}
      </section>
    </div>
  );
}

type MetricIcon = typeof ShieldCheck;

function MetricCard({ label, value, icon: Icon, detail }: { label: string; value: number; icon: MetricIcon; detail: string }) {
  return (
    <article className="source-metric-card min-h-[7rem]">
      <div>
        <p>{label}</p>
        <span className="source-logo blue">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </div>
      <b>{value.toLocaleString("ko-KR")}</b>
      <p>{detail}</p>
    </article>
  );
}

function formatAction(action: string) {
  return action.replaceAll(".", " / ");
}

function metadataSummary(metadata: Record<string, unknown>) {
  const entries = Object.entries(metadata).slice(0, 2);
  if (!entries.length) {
    return "-";
  }
  return entries.map(([key, value]) => `${key}=${String(value)}`).join(" · ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
