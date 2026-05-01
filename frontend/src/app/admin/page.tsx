"use client";

import { AlertTriangle, ShieldCheck, UserCog, UsersRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import type { AuthUsersResponse, DemoUser } from "@/lib/api/types";

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
  account: "\uACC4\uC815",
  role: "\uC5ED\uD560",
  department: "\uBD80\uC11C",
  scope: "\uAD8C\uD55C \uBC94\uC704",
};

export default function AdminPage() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    apiGet<AuthUsersResponse>("/api/v1/auth/users")
      .then((result) => {
        if (active) {
          setUsers(result.users);
          setError(undefined);
        }
      })
      .catch(() => {
        if (active) {
          setError(text.permissionRequired);
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
    return <div className="liquid-surface rounded-[30px] p-6 text-sm text-[var(--ink-muted)]">{text.loading}</div>;
  }

  if (error) {
    return (
      <div className="space-y-5">
        <section className="liquid-surface rounded-[32px] p-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-1 h-5 w-5 text-amber-500" aria-hidden="true" />
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">{error}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">{text.permissionDescription}</p>
            </div>
          </div>
        </section>
        <Link
          href="/login"
          className="liquid-primary inline-flex h-11 items-center justify-center rounded-[24px] px-5 text-sm font-semibold"
        >
          {text.loginAsAdmin}
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="liquid-surface rounded-[32px] p-5 md:p-7">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">Workspace Admin</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">{text.title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">{text.description}</p>
          </div>
          <div className="liquid-primary inline-flex w-fit items-center gap-2 rounded-[24px] px-4 py-3 text-sm font-semibold">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Admin verified
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard label={text.total} value={metrics.total} icon={UsersRound} />
        <MetricCard label={text.admins} value={metrics.adminCount} icon={ShieldCheck} />
        <MetricCard label={text.employees} value={metrics.employeeCount} icon={UserCog} />
        <MetricCard label={text.restrictedAccess} value={metrics.restrictedCount} icon={ShieldCheck} />
      </section>

      <section className="liquid-surface overflow-hidden rounded-[30px]">
        <div className="border-b border-[var(--line-soft)] px-5 py-4">
          <h2 className="text-base font-semibold">{text.usersAndPermissions}</h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">{text.permissionNote}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-xs uppercase text-[var(--ink-muted)]">
              <tr className="border-b border-[var(--line-soft)]">
                <th className="px-5 py-3 font-semibold">{text.account}</th>
                <th className="px-5 py-3 font-semibold">{text.role}</th>
                <th className="px-5 py-3 font-semibold">{text.department}</th>
                <th className="px-5 py-3 font-semibold">{text.scope}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-[var(--line-soft)] last:border-0">
                  <td className="px-5 py-4">
                    <p className="font-semibold text-[var(--ink-strong)]">{user.name}</p>
                    <p className="text-xs text-[var(--ink-muted)]">{user.email}</p>
                  </td>
                  <td className="px-5 py-4">
                    <span className="liquid-control rounded-full px-3 py-1 text-xs font-semibold">{user.role}</span>
                  </td>
                  <td className="px-5 py-4 text-[var(--ink-muted)]">
                    <p className="font-medium text-[var(--ink-strong)]">{user.department}</p>
                    <p className="text-xs">{user.title}</p>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex flex-wrap gap-2">
                      {user.permission_levels.map((level) => (
                        <span
                          key={level}
                          className="rounded-full border border-[var(--line-soft)] px-3 py-1 text-xs font-semibold text-[var(--ink-muted)]"
                        >
                          {level}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

type MetricIcon = typeof ShieldCheck;

function MetricCard({ label, value, icon: Icon }: { label: string; value: number; icon: MetricIcon }) {
  return (
    <article className="liquid-surface rounded-[26px] p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-[var(--ink-muted)]">{label}</p>
        <Icon className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
      </div>
      <p className="mt-2 text-2xl font-semibold">{value.toLocaleString()}</p>
    </article>
  );
}
